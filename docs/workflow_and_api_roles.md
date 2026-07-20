# 工作流与 API 职责

`references/工作流.png` 描述的是逻辑职责，不代表每个方框必须使用一个不同的 LLM。第一版的最小实现只需要两类模型能力：

1. 一个支持图像输入的多模态 LLM/VLM：重复用于规划和验证。
2. 一个实际支持图像生成或图像编辑的模型/API：用于产出候选编辑图。

## 已验证的 OpenAI 兼容 API

已配置服务的 `base_url` 为 `https://api.nuwaapi.com/v1`。探测调用确认该服务既提供 Chat Completions，也提供标准的图像生成与编辑 endpoint。密钥只保存在本地 `.env`，本文不记录其值。

```text
输入图 + 编辑指令 -> Planner 的结构化 JSON
原图 + 候选图 + 计划 -> Verifier 的结构化 JSON
```

实测能力如下：

| 角色 | 模型与 endpoint | 已验证行为 |
| --- | --- | --- |
| Planner / Verifier | `gpt-4o`，`POST /v1/chat/completions` | 接收标准 RGB PNG 的 data URL，并正确识别图像内容；服务响应的解析快照为 `gpt-4o-2024-11-20`。 |
| 文生图 Executor | `gpt-image-2`，`POST /v1/images/generations` | 成功生成候选图。 |
| 图像编辑 Executor | `gpt-image-2`，`POST /v1/images/edits` | 成功接收标准 RGB PNG 并按编辑指令返回候选图。 |
| 图像返回 | `gpt-image-2` | 生成和编辑均返回 `data[0].b64_json`，客户端必须 Base64 解码后保存为图像文件。 |

一次 1x1 测试 PNG 被编辑 endpoint 拒绝为无效图像文件；64x64、24-bit RGB PNG 成功。因此客户端在首版应统一把输入规范化为 RGB PNG，并在调用前校验文件有效性和最小尺寸。模型列表中还存在其他 GPT 与 Gemini 别名，但未逐项探测，不能据名称推断其视觉或图像编辑能力。

`/v1/models` 不提供计费、RPM/TPM、并发数、最大上传尺寸或支持格式的完整信息。这些仍需从服务商控制台或文档确认，并在运行时按 `429`、超时和图片参数错误处理。

## 推荐 MVP 映射

```text
User image + instruction
  -> Planner call: gpt-4o (同一 API，调用 1)
  -> Tool selection: Python 规则，不调用 LLM
  -> Tool retrieval: MVP 跳过
  -> Tool executor: gpt-image-2（`/images/edits`，调用 2）
  -> Verification call: gpt-4o（同一 API，调用 3）
       -> pass: 返回候选图
       -> fail: Planner 再调用，生成带失败原因的修复指令；最多重试 2 次
```

规划器输出必须受 JSON schema 约束，至少包括 `target`、`operation`、`preserve`、`physics_dependencies`、`route`、`edit_prompt`。验证器也输出 JSON，包括 `instruction_score`、`preservation_score`、各物理检查项、`pass`、`repair_instruction`。这使重试由程序根据字段触发，而不是由自由文本聊天决定。

## 各方框的实现边界

| 图中模块 | 首版实现 | 是否使用文档 API |
| --- | --- | --- |
| MLLM Analyzer / Planning | `gpt-4o` 的图文理解与 JSON 计划 | 是，已验证视觉输入 |
| Tool Selection | 基于计划 JSON 的 Python router | 否 |
| Tool retrieval | 暂停；后续可检索工具能力说明或历史成功案例 | 否 |
| Tool Executor | `gpt-image-2`；调用 `/images/edits` 并解码 `b64_json`；必要时配合检测、分割、裁剪、回贴 | 是，已验证 image-edit 能力 |
| Verification Agent | `gpt-4o`，但使用独立评审 prompt；辅以确定性检查 | 是，已验证视觉输入 |
| Refine / Retry | Python 状态机拼接 `repair_instruction` 后重新执行 | 仅在生成新的修复计划时使用 |

检测、分割、阴影/反射几何检查不是 LLM。它们可在第二阶段作为本地 CV 工具接入。物理一致性的核心贡献是把它们的输出转为验证约束和修复指令，而非增加 LLM 数量。

## 设计约束

- 重试应回到 `Planner` 的当前状态，而不是回到最初的用户输入；状态包含原图、当前候选图、历史计划、失败原因与调用次数。
- 每个用例限制候选数和最大重试次数，防止成本失控。
- API key 只从 `.env` 读取；不写入本文件、代码、日志或提交记录。
- 输入图在进入 API 前转换为 RGB PNG；将 `b64_json` 解码后的候选图与每轮 JSON 评审结果写入 `outputs/`。

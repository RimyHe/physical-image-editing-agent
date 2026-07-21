# 物理一致性图像编辑 Agent：任务总览

## 1. 项目背景

本项目面向“图像生成/编辑模型在修改主体内容后，是否同时保持场景物理规律”的问题。常见图像编辑模型可完成“添加、删除、移动、改属性”等指令，却容易留下与编辑对象不一致的阴影、反射、遮挡关系、接触关系或物体状态。

项目不训练新的图像生成模型，而是以**闭源模型 API** 为底座，通过 agent 在推理时进行任务规划、工具路由、编辑结果验证和定向重试，提高物理真实感与编辑可靠性。

## 2. 原始任务拆解

### Task 1：搭建 Agent Pipeline

1. 调研开源图像生成/图像编辑 agent pipeline，重点关注它们如何做任务分解、工具调用、评估与自我修正。
2. 使用闭源模型 API 实现 pipeline；如复用开源框架，需要改造其模型调用层。
3. 展示 agent 的编辑过程与结果，而不只是给出一张最终图。
4. 选取 PICABench 的部分测试案例验证效果。

### Task 2：设计物理规律保持模块

在 Task 1 的 pipeline 上加入可解释的物理一致性机制，使 agent 在编辑时识别并处理：

- 光学：阴影、反射、光照与材质一致性；
- 几何/空间：遮挡、透视、相对位置与边界连续性；
- 交互/力学：接触、支撑、悬浮及物体间互动；
- 状态变化：编辑后的物体状态与周边环境是否同步变化。

该模块必须影响编辑决策或重试，而不只是生成后的审美打分。

## 3. 总体目标与成功标准

### 总体目标

实现一个可运行、可追踪、可评测的闭环系统：输入用户图片和自然语言编辑指令，输出编辑结果，并在需要时通过物理约束验证和有限重试修复结果。

### 最小成功标准（MVP）

1. 可通过配置切换闭源模型 API，不在代码中硬编码密钥。
2. 对至少一个支持图像编辑的模型，跑通 `plan -> edit -> verify -> retry/accept`。
3. 每次运行保存输入、计划、候选图、验证结果、重试原因、耗时和调用次数。
4. 在一小组 PICABench 代表性样例上，对比“单次直接编辑”与“agent 闭环编辑”。
5. 展示至少一个物理错误被验证器发现并在后续编辑中修复的完整案例。

## 4. 工作流

参考图：[`references/工作流.png`](../references/工作流.png)

```text
User Image + Instruction
  -> MLLM Analyzer / Planning
  -> Tool Selection
  -> (optional) Tool Retrieval
  -> Tool Executor (generation/edit)
  -> Verification Agent
       -> pass: final image
       -> fail: refine / retry -> 返回当前状态的规划步骤
```

这里的方框表示**功能角色**，不是一格对应一个模型。MVP 的推荐实现是：

```text
Planner/VLM：`gpt-4o`，读取图像并输出受 schema 约束的 JSON
Router：Python 规则，根据目标尺度、编辑类型和物理依赖选执行路线
Executor：`gpt-image-2`，调用 `/images/edits` 并将 `b64_json` 解码为候选图
Verifier/VLM：复用 `gpt-4o`，以独立评审 prompt 检查结果
State machine：Python 控制重试次数、候选记录、停止与回退
```

`Tool Retrieval` 在首版不实现。后续可用于检索工具说明、历史成功轨迹或特定物理规则。

## 5. 已有资源

### 已验证的 API 能力

- 服务为 OpenAI-compatible 格式，`base_url` 为 `https://api.nuwaapi.com/v1`；密钥只从本地 `.env` 或环境变量读取。旧的已暴露密钥必须撤销，不得复用。
- `gpt-4o` 已通过 `POST /v1/chat/completions` 的标准 RGB PNG data URL 测试，可读取图像并适合作为 Planner/Verifier。请求别名为 `gpt-4o`，服务返回的实际快照为 `gpt-4o-2024-11-20`。
- `gpt-image-2` 已通过 `POST /v1/images/generations` 和 `POST /v1/images/edits` 测试，既可生成图片，也可编辑上传图片，作为 MVP 的 Executor。
- `gpt-image-2` 的结果为 `data[0].b64_json`，而非 URL；`editor_client` 负责 Base64 解码、保存候选图并将其路径写入运行状态。
- 编辑 endpoint 拒绝过 1x1 测试图，但接受 64x64、24-bit RGB PNG。首版统一将输入规范化为 RGB PNG，并在调用前校验文件有效性和最小尺寸。
- 计费、RPM/TPM、并发、最大上传尺寸及完整格式列表仍未由 API 返回；实现中要为 `429`、超时和图片参数错误设置退避重试，并在服务商控制台补充限额记录。

推荐 `.env` 配置为：

```dotenv
OPENAI_COMPAT_BASE_URL=https://api.nuwaapi.com/v1
OPENAI_COMPAT_API_KEY=<local-secret>
PLANNER_MODEL=gpt-4o
VERIFIER_MODEL=gpt-4o
IMAGE_EDIT_MODEL=gpt-image-2
```

### 功能角色与 API 职责

`references/工作流.png` 中的方框是逻辑职责，不要求每个方框对应一个独立模型。第一版最小实现只需要两类能力：

1. 一个支持图像输入的多模态 LLM/VLM，用于规划和验证。
2. 一个支持图像编辑的生成模型/API，用于产出候选图。

当前推荐映射如下：

| 角色 | 模型与 endpoint | 当前职责 |
| --- | --- | --- |
| Planner / Verifier | `gpt-4o`，`POST /v1/chat/completions` | 读取图像并输出结构化计划或验证结果 |
| Image Executor | `gpt-image-2`，`POST /v1/images/edits` | 根据原图和编辑 prompt 生成候选图 |
| Tool Selection / Retry Control | Python 状态机 | 路由、重试、保存中间产物、控制停止条件 |

推荐的 MVP 调用链：

```text
User image + instruction
  -> Planner call: gpt-4o
  -> Tool selection: Python router
  -> Tool executor: gpt-image-2 /images/edits
  -> Verification call: gpt-4o
       -> pass: 返回候选图
       -> fail: 生成 repair instruction 后重试
```

设计边界：

- `Tool Retrieval` 在首版仍跳过，后续可用于检索历史成功轨迹或工具说明。
- 检测、分割、mask、阴影/反射几何检查属于第二阶段本地 CV 工具，不由 LLM 直接承担。
- `/v1/models` 不能提供完整计费、并发和上传限制信息，运行时仍需处理 `429`、超时和图片参数错误。
- 输入图在进入 API 前统一规范化为 RGB PNG；候选图通过 `b64_json` 解码后写入 `outputs/`。

### 基准

- PICABench：评估编辑后物理真实感，覆盖光学、力学和状态变化等维度；用于挑选测试样例和定义评价问题。

### 已下载论文

| 文件 | 对项目的直接价值 |
| --- | --- |
| `references/papers/GenArtist_2407.05600.pdf` | 任务分解、工具库、位置辅助工具、逐步验证 |
| `references/papers/IMAGAgent_2603.29602.pdf` | 约束感知规划、工具编排、多专家反思与重试 |
| `references/papers/PICABench_2510.17681.pdf` | 物理一致性问题定义、测试案例和评估维度 |
| `references/papers/ImAgent_2511.11483.pdf` | 将推理时增强设计为动作空间与停止决策 |
| `references/papers/ATR_2604.15917.pdf` | 查询画像、任务重构路由、局部编辑/结构解耦与反馈执行 |

### 已下载参考项目

| 位置 | 可借鉴内容 | 不应直接承担的职责 |
| --- | --- | --- |
| `references/projects/nanobot` | OpenAI-compatible provider 配置、工具注册、运行日志、WebUI | 物理一致性判断与图像编辑状态机 |
| `references/projects/autoresearch` | 固定预算、指标驱动实验、保留改进与丢弃退化的流程 | 图像编辑运行时或模型训练 |

### 当前目录

```text
src/        后续自行实现的 pipeline 与物理模块
data/       PICABench 子集、输入图和案例元数据
outputs/    中间图、日志、评测表和展示材料
docs/       任务、设计、阅读与实验文档
references/ 论文、参考代码、工作流图
```

## 6. 建议的实现范围

### 第一阶段：可运行闭环

实现下列最少模块：

1. `planner`：读取原图和指令，抽取目标、操作、保持内容、物理依赖、编辑 prompt。
2. `router`：先仅支持 `direct_edit` 与 `local_edit` 两条路线。
3. `editor_client`：封装确认可用的闭源图像编辑 API。
4. `verifier`：比较原图、候选图与计划，输出结构化检查结果。
5. `orchestrator`：限制最多 2 次重试，保存每一步状态。
6. `demo`：显示原图、计划、每轮候选图、验证项和最终结果。

### 第二阶段：物理保持模块

将编辑操作映射为物理依赖。例如删除物体时，不只验证“物体是否消失”，还检查“对应阴影、反射、遮挡区域是否同步更新”。建议优先覆盖删除、添加、移动三类操作，并逐步加入局部检测/分割、裁剪与回贴。

## 7. 预期交付物

- 可运行源码与 `.env.example`；
- 架构图、模块职责和 API 调用说明；
- 一组 PICABench 案例的输入、运行轨迹和结果；
- baseline（单次编辑）与 agent（闭环）的对比表；
- 至少一个失败检测与定向修复的可视化案例；
- 调用成本、延迟、失败模式与局限性说明。

## 8. 当前待确认事项

1. API 服务的计费、RPM/TPM、并发、最大上传尺寸和完整格式列表。
2. 是否允许使用第三方或本地检测、分割模型；若不允许，物理模块只能依赖 VLM 验证与编辑 prompt 重构。
3. PICABench 的样例数据获取方式、可用数量及评测脚本。
4. 展示形式要求：命令行日志、Gradio/FastAPI 页面，或两者都要。
5. Task 2 对“物理规律保持”的评价口径：仅定性展示、VLM 指标，还是 PICAEval/人工标注的定量比较。

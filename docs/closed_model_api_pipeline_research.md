# 闭源模型 API Pipeline 调研

## 调研范围

本文调研编排层可检查、可扩展，而推理、路由或评审等一个或多个步骤调用托管闭源模型 API 的项目。Pipeline 代码开源不等于模型权重开源。

## 稳定结论

- 将工作流语义保留在模型服务之外：使用类型化工具契约、结构化输出、持久化状态、提供商适配层和确定性验证器。这样替换 Planner 或 Verifier 时不必重写整个流程。
- 每次运行记录提供商、模型 ID、请求参数、模板版本、工具输入输出、重试决策、延迟、成本和验证证据。闭源模型可能在未发布权重的情况下变更行为，因此模型更新后必须重新评测。
- 对确定性、隐私敏感或高吞吐任务优先采用本地实现。将付费多模态 API 留给歧义规划、语义路由、开放式评审和结果合成；同时实施脱敏、超时、限流、预算上限、回退和高风险操作的人类审批。

## 代表性项目

| 项目 | 闭源 API 的职责 | Pipeline 机制 | 最适用场景 |
| --- | --- | --- | --- |
| OpenAI Agents SDK | 通过 Responses 或 Chat Completions API 作为主 Agent 模型 | 工具、handoff、会话、护栏和 trace | 基于 OpenAI 模型的生产级工作流 |
| AutoGen | GPT / Azure OpenAI 客户端 | 消息驱动 Agent、Agent 作为工具、代码执行 | 已有多 Agent 原型；主仓库已进入维护模式 |
| LangGraph | 任意支持工具调用的托管模型，包括 OpenAI、Anthropic、Google 等 | 有状态图、checkpoint、条件路由和人工审核 | 需要持久状态及确定性流程控制的长任务 |
| CrewAI | 为各 Agent 配置托管 LLM | 角色化 Crew 和事件驱动 Flow | 团队式业务自动化 |
| HuggingGPT / JARVIS | ChatGPT 规划并汇总 | 任务规划、模型选择、执行与结果生成，底层使用 HF 专家模型 | “闭源控制器 + 专用模型工具库”的经典范式 |
| Visual ChatGPT、GenArtist | GPT 类多模态模型解析、规划、选工具与验证 | 围绕图像生成、编辑和空间辅助工具的工具链或规划树 | 统一图像生成/编辑研究 |
| IMAGAgent | 托管 VLM/LLM 负责规划、编排与多专家反思 | 带历史反馈的约束感知 `plan-execute-reflect` 闭环 | 稳定的长程多轮图像编辑 |

## 通用架构

```text
用户输入
  -> 策略 / schema 校验
  -> 托管模型 Planner 或 Router
  -> 类型化工具调用与本地状态更新
  -> 确定性检查 + 可选模型评审
  -> 重试、回退、人工审批或最终响应
  -> trace、成本、评测与审计记录
```

## 对物理一致性图像编辑项目的适配性

| 选项 | 对 OpenAI-compatible API 的适配 | 可提供的能力 | 建议 |
| --- | --- | --- | --- |
| PydanticAI | `OpenAIChatModel` 与 `OpenAIProvider(base_url, api_key)` 支持 Chat Completions-compatible endpoint | 强类型 Planner/Verifier 输出、校验与重试 hook、工具、图原语和评测支持 | 首选实现框架 |
| OpenAI Agents SDK | `OpenAIChatCompletionsModel` 可接受带 `base_url` 与 `api_key` 的自定义 `AsyncOpenAI` 客户端 | Agent/工具运行时、handoff、护栏、会话和 tracing | 当动态工具选择成为主要复杂度时采用 |
| LangGraph | `ChatOpenAI` 支持标准 Chat Completions endpoint 的自定义 `base_url` | 显式状态图、checkpoint、人工审核、持久执行和条件重试路径 | 需要断点恢复或人工审批时加入 |
| AutoGen | `OpenAIChatCompletionClient` 暴露 `base_url`，但非 OpenAI 模型不保证兼容 | 从 Agent、工具、反思团队、终止条件到状态的逐步教程 | 很好的学习参考，不作为 MVP 默认选择 |
| CrewAI | `LLM` 接受 `base_url` 和带提供商前缀的模型名 | 角色化 Agent 和事件驱动 Flow | 适合业务自动化，不是确定性图像编辑控制的首选 |
| LiteLLM Proxy | 支持 OpenAI-compatible endpoint 和大量上游服务 | 路由、凭据、预算和提供商标准化 | 模型网关层，不是 Agent pipeline 框架 |

## 推荐实施顺序

1. 使用既有 Chat Completions endpoint 上的 `gpt-5.4-mini` 与 PydanticAI 起步。将 `EditPlan` 和 `VerificationReport` 定义为 Pydantic 输出模型；对格式错误或字段缺失的输出拒绝并重试。
2. 将 `gpt-image-2` 保持在聊天 Agent 抽象之外。实现一个小型 `editor_client`：把输入规范化为 RGB PNG，调用 `/images/edits`，解码 `data[0].b64_json`，并保存候选图产物。
3. 实现显式 Python 状态机：`plan -> edit -> verify -> accept | repair -> retry`。每轮持久化输入、计划、候选图、验证报告、耗时和请求标识，最多重试两次。
4. 请求 VLM Verifier 前先运行确定性的物理检查。将失败证据写入 `repair_instruction`，而不是依赖无约束的多 Agent 对话辩论。
5. 只有当任务需要跨进程恢复、暂停等待人工批准，或在多个编辑工具间分支时才引入 LangGraph。只有当多个专用角色的动态路由不能被状态机清晰表达时，才采用 Agents SDK 或 AutoGen 的多 Agent 模式。

## 框架接入前的兼容性检查

- 当前固定模型为 `gpt-5.4-mini`；需要持续验证其图片输入、JSON schema 输出和函数调用兼容性。
- 不要因为代理兼容 Chat Completions 就假设它支持 Responses API 特性、托管工具、服务端会话或 tracing。除非该服务另行证明兼容 Responses API，否则框架应配置为 Chat Completions。
- 将成本和限流信息作为独立配置记录；`/models` endpoint 不提供这些信息。

## Codex 认证边界

当前项目的 `https://api.nuwaapi.com/v1` key 是第三方 OpenAI-compatible 模型网关凭据，本项目固定使用 `gpt-5.4-mini` 和 `gpt-image-2`；它不是 OpenAI Platform API key，也不是 ChatGPT 账号凭据。因此它不能用于登录 Codex，也不应写入全局 `~/.codex/.env` 或作为 Codex 的 `OPENAI_API_KEY`。

Codex 的官方登录路径是 ChatGPT 账号授权或 OpenAI Platform API key；官方还单独支持 Amazon Bedrock 凭据和其 Responses API 实现。第三方 Chat Completions-compatible endpoint 的模型列表与 Codex 可登录、可使用的模型是两个独立的授权与兼容性边界。

## 来源

- OpenAI Agents SDK: https://github.com/openai/openai-agents-python
- AutoGen: https://github.com/microsoft/autogen
- LangGraph: https://langchain-ai.github.io/langgraph/
- CrewAI: https://docs.crewai.com/
- HuggingGPT / JARVIS: https://github.com/microsoft/JARVIS
- GenArtist: https://github.com/zhenyuw16/GenArtist
- IMAGAgent: https://arxiv.org/html/2603.29602
- PydanticAI OpenAI-compatible models: https://pydantic.dev/docs/ai/models/openai/
- OpenAI Agents SDK custom providers: https://openai.github.io/openai-agents-python/models/
- LangGraph workflow and agent patterns: https://langchain-ai.github.io/langgraph/agents/tools/
- AutoGen AgentChat tutorial: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/
- CrewAI LLM configuration: https://docs.crewai.com/en/concepts/llms
- LiteLLM Proxy quick start: https://docs.litellm.ai/docs/proxy/quick_start

# Physical Image Editing Agent

本目录用于完成“基于闭源图像编辑 API 的物理一致性图像编辑 Agent”任务。

## 目录

```text
src/                    自行实现的 agent pipeline 与物理约束模块
data/                   PICABench 子集与本地测试输入
outputs/                运行结果、候选图与评测报告
docs/                   设计说明、实验记录与阅读笔记
references/papers/      任务直接相关论文 PDF
references/projects/    只读参考项目
```

## 参考论文

- `GenArtist_2407.05600.pdf` - GenArtist: Multimodal LLM as an Agent for Unified Image Generation and Editing
- `IMAGAgent_2603.29602.pdf` - IMAGAgent: Orchestrating Multi-Turn Image Editing via Constraint-Aware Planning and Reflection
- `PICABench_2510.17681.pdf` - PICABench: How Far Are We from Physically Realistic Image Editing?
- `ImAgent_2511.11483.pdf` - ImAgent: A Unified Multimodal Agent Framework for Test-Time Scalable Image Generation
- `ATR_2604.15917.pdf` - Making Image Editing Easier via Adaptive Task Reformulation with Agentic Executions

## 参考项目

- `projects/nanobot` - OpenAI-compatible provider、工具注册、WebUI 与运行时设计参考。
- `projects/autoresearch` - 固定预算、指标驱动的自动实验与消融流程参考。

参考项目不作为本项目的运行时依赖。核心流程将独立实现为可审计的状态机：`profile -> route -> reformulate -> edit -> verify -> retry/accept`。

## 当前可运行 MVP

已实现一个最小闭环 agent：

```text
input PNG + instruction
  -> Planner: gpt-4o, 输出结构化计划
  -> Router: Python 规则，首版走 direct_edit
  -> Executor: gpt-image-2 /images/edits, 输出 candidate.png
  -> Verifier: gpt-4o, 输出结构化验收结果
  -> pass: 接受；fail: 带 repair_instruction 重试
```

运行前在本目录创建 `.env`，格式可参考 `.env.example`。密钥只在本地 `.env` 中读取，不写入源码、文档或日志。

```powershell
python physical_image_editing_agent\run_agent.py
```

如果不传 `--image`，脚本会生成一个合成样本 `data/samples/red_ball_shadow.png`，默认任务是移除红球及其阴影。也可以指定自己的 PNG：

```powershell
python physical_image_editing_agent\run_agent.py --image physical_image_editing_agent\data\samples\red_ball_shadow.png --instruction "Remove the red ball and its shadow."
```

每次运行会在 `outputs/run_YYYYMMDD_HHMMSS/` 下保存：

- `run_state.json`：总状态、调用次数、是否接受、最终图路径。
- `step_XX/plan.json`：Planner 计划和 Router 结果。
- `step_XX/candidate.png`：Executor 生成的候选图。
- `step_XX/verify.json`：Verifier 评分、问题列表和修复指令。

当前版本只做整图编辑，不做 mask、检测、分割或局部回贴；这些属于下一阶段的物理保持模块。

# Docs Guide

本目录按“任务定义、进展汇报、开发计划、技术调研、评测结果、协作约定”组织。

## 1. 任务与基线

- [`task_brief.md`](task_brief.md)
  - 项目背景、任务目标、成功标准、工作流、API 能力和功能角色映射。

## 2. 进展汇报

- [`physical_dataset_progress_report.md`](physical_dataset_progress_report.md)
  - 当前阶段进展、数据集选择、评测结论、遇到的问题、走过的弯路和修正方案。

## 3. 开发计划

- [`development_plan.md`](development_plan.md)
  - 当前阶段目标、路线图、router/tooling 演进和下一步任务拆解。

## 4. 技术调研

- [`closed_model_api_pipeline_research.md`](closed_model_api_pipeline_research.md)
  - 闭源模型 API pipeline、框架适配和架构选择调研。
- [`tool_router_physics_tool_research.md`](tool_router_physics_tool_research.md)
  - tool router、物理编辑工具链和 route 设计调研。

## 5. PICABench 数据与结果

- [`picabench_examples.md`](picabench_examples.md)
  - 本地 PICABench 子集说明、评分字段、运行方式和结果入口。
- [`picabench_full_run_results.md`](picabench_full_run_results.md)
  - 50 个 case 的逐类分组结果表和汇总评分。

## 6. 协作约定

- [`codex_role_and_doc_maintenance.md`](codex_role_and_doc_maintenance.md)
  - Codex 在本目录下工作的角色、文档维护职责和更新规则。

## 7. 当前整理说明

本次整理将原先单独存在的 `workflow_and_api_roles.md` 合并进 [`task_brief.md`](task_brief.md)，因为两者都描述 MVP 工作流、API 能力和角色边界，长期并存会导致重复维护。

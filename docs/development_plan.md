# Physical Agent 开发计划

本文档只维护后续开发路线、模块职责、优先级和验收标准。已经完成的实验记录、阶段性问题和人工观察放在 [`physical_dataset_progress_report.md`](physical_dataset_progress_report.md)；完整运行结果放在 [`picabench_full_run_results.md`](picabench_full_run_results.md)；PICABench 数据说明放在 [`picabench_examples.md`](picabench_examples.md)。

## 当前重点

P0 `PhysicalIntentExpander` 已达到当前阶段的收尾标准：能够从短 `superficial_prompt` 和图像证据中生成结构化 `TaskProfile`，补全关键最终稳定状态，输出 diagnostics，并将详细任务画像压缩成更适合 image executor 的 prompt。下一阶段第一优先级转向 P2/P3：把 `TaskProfile` 真正接入 route/toolchain，尤其是 `causal_settle_route` 和局部 executor 控制。

2026-07-24 的 5-case 人工检查表明，早期瓶颈不是 prompt 不够长，而是 `PhysicalIntentExpander` 经常没有预测下一个稳定状态。例如移除支撑牌后没有预测玻璃桌面倾斜，移除摩托车脚撑后没有预测摩托车倒伏。当前 P0 已通过 `StableStatePredictor` 和 `PromptCompressor` 修复这一类核心缺口。后续学习 `explicit_prompt` 时，只抽取终态约束结构，不直接模仿长文本。

```text
explicit_prompt
  -> intervention target
  -> affected objects
  -> final stable state
  -> contact/support/shadow/reflection changes
  -> preserve scope
  -> must-pass checks
```

## 目标架构

```text
User image + instruction
  -> PhysicalIntentExpander: 结构化物理任务画像
  -> Planner: 生成执行 prompt 和 verifier focus
  -> Router: 根据 law / operation / risk 选择 route 或 toolchain
  -> Executor: direct edit / mask edit / two-pass / best-of-N
  -> Verifier: law-specific checklist + PICABench QA + preservation checks
       -> pass: accept
       -> fail: structured failure -> retry / reroute / reject
```

当前 MVP 已经跑通 Planner、direct-edit Router、Image Edit API、Verifier、retry 和 PICABench 离线评测，但 Router 仍基本回退到 `direct_edit`，尚未真正接入 detection、segmentation、mask edit、local repaint 或 best-of-N。

## P0：PhysicalIntentExpander

状态：当前阶段收尾。后续只保留小修和回归测试；新的主要开发应进入 P2 Router、P3 Executor 和 P4 route-aware Verifier。

目标：输出可验证、可路由、可追踪的 `TaskProfile`，而不是生成更长的自然语言 prompt。

运行时输入应保持为：

```text
image + superficial/user instruction + optional inferred labels + previous verifier failure
```

PICABench 的 `explicit_prompt` 只用于 schema 设计参考、upper-bound 对照、失败归因诊断和弱监督字段抽取，不作为真实推理输入。

### TaskProfile

`TaskProfile` 至少包含：

```text
schema_version
labels
target_objects
physical_operation
current_state
intervention
final_state
affected_objects
physical_dependencies
dependent_regions
preserve_scope
reference_cues
uncertainties
must_pass_checks
route_hints
diagnostics
```

### 内部职责

第一阶段可以仍用一次 VLM 调用，但代码边界按以下职责组织：

```text
IntentNormalizer
  -> LabelPolicyCompiler
  -> SceneEvidenceExtractor
  -> InterventionGraphBuilder
  -> StableStatePredictor
  -> VisualEvidencePlanner
  -> PreserveScopePlanner
  -> TaskProfileValidator
  -> PromptRenderer
```

### Causality 专项

`Causality + remove` 是最高优先级专项，必须从“删除目标”升级为“移除支撑/约束并进入稳定态”：

```text
remove support/constraint
  -> identify affected object
  -> predict no-longer-supported state
  -> choose final stable pose
  -> add new contact points/contact shadows
  -> remove old support traces
```

### P0 验收样例

| Case | 验收重点 |
|---|---|
| `picabench_0000_causality` | 删除 5 of spades 后，`final_state` 包含玻璃桌面倾斜、前左区域空缺、相关纸牌倒落和新接触阴影 |
| `picabench_0294_causality` | 删除脚撑后，`final_state` 包含摩托车倒伏、左侧接触地面、旧脚撑痕迹消失和连续接触阴影 |
| `picabench_0358_causality` | 杯子侧倒后，液体静态铺展、连接杯口且边界自然，避免错误反射/倒影关系 |
| `picabench_0148_light_propagation` | 删除自行车时同步删除完整车影和接触阴影，并恢复路面/路缘连续性 |
| `picabench_0816_light_propagation` | 移动郁金香时保持主体完整、位置正确，并重投影与场景一致的阴影 |

### P0 待办

- [~] 实现 `explicit_prompt -> TaskProfile` 字段抽取，用作弱监督候选标签。该项移动为后续数据构建/训练准备，不阻塞 P0 收尾。
- [x] 强化 `LabelPolicyCompiler` 的短 prompt 推断：`kickstand`、`card structure`、`knock over/spill` 可以进入 causality/topple 路径。
- [x] 实现规则版 `StableStatePredictor`，优先覆盖 `Causality + remove`，并补充 `Causality + topple` 与 `Light_Propagation + move/remove` 的基础终态约束。
- [x] 强化 `TaskProfileValidator` 的归一化流程，在最终校验前调用 `StableStatePredictor`，避免 `final_state` 和关键 law-specific dependency 只停留为空值。
- [x] 实现 law-specific `PromptRenderer`，覆盖 reflection、light propagation、refraction、causality、deformation、global/local state，并加入 `PromptCompressor` 输出压缩 executor prompt。
- [x] 输出 diagnostics：记录 stable-state predictor 的 `auto_filled_fields`、`validation_warnings`、`prompt_length`、`detailed_prompt_length` 和 `prompt_compression_ratio`。后续细化 `wrong_stable_pose`、`shadow_not_removed`、`subject_broken_after_move` 放入 P4 Verifier。
- [x] 在五个 P0 验收样例上比较 superficial baseline、explicit upper bound 和 expander，并记录人工检查结论。`0000` 额外完成 latest intent long prompt 和单次生图验证。

### P0 收尾结论

P0 的目标不是让所有图片编辑结果都达到最终质量，而是让 intent 组件产出足够明确、可验证、可路由的物理任务画像。当前已经满足：

- `TaskProfile` schema 稳定，包含 labels、target objects、intervention、final state、dependencies、dependent regions、preserve scope、checks、route hints 和 diagnostics。
- `Causality + remove` 能从局部删除升级为支撑/约束移除后的稳定态预测。
- `0000` 的短 prompt 能生成包含玻璃倾斜、支撑 gap、倒落纸牌、新接触阴影和 old-state failure 禁止项的压缩 executor prompt，并且单次生图已经产生结构重排。
- `0294` 的脚撑删除能表达摩托车倒伏和新接触关系。
- `0358` 的碰倒杯子能表达杯子侧倒、咖啡铺展、杯口到液体连接和自然液体边界。
- `0148`、`0816` 的 light propagation 路径能表达旧影删除、新影重投影和主体完整性约束。

P0 残余风险：

- intent 仍可能依赖规则补全，不能证明 VLM 自身稳定掌握所有物理后果。
- 压缩 prompt 的最佳预算仍需通过更多样例统计确定。
- 图片结果中的身份保持、局部区域控制和候选选择不属于 P0，应交给 Router/Executor/Verifier。

## P1：评测协议与坐标协议

状态：已完成当前阶段所需的最小稳定版本。

已实现能力：

- canonical input：原图 contain 到 `1024x1024`，保存 `coordinate_transform.json`。
- 显式坐标映射：`source box -> canonical box -> output box`。
- 输出去 padding：同时保留 padded candidate 和 unpadded final image。
- QA 视图分流：`global_position` 使用完整图，`local_appearance` 使用 mapped crop，`mixed` 同时使用两者。
- 结果记录：`pica_eval.json` 记录 evaluation view、source box、mapped box、output size 和 context risk。

后续增强不阻塞 P0：

- 增加坐标映射单元测试。
- 用少量人工标注校正 QA question type。
- 对 Global 任务单独解释 non-edit PSNR。
- 将 PICAEval 结果进一步接入 Verifier gate。

## P2：Router 与 RouteSpec

目标：把 `TaskProfile` 转成可审计的 route/toolchain，而不是让所有任务都退化成 whole-image direct edit。

待办：

- [ ] 定义 `RouteDecision`：`route`、`confidence`、`required_tools`、`optional_tools`、`requires_mask`、`fallback_route`、`verification_focus`。
- [ ] 定义 `RouteSpec`：适用 law/operation、工具链、失败模式、fallback、retry hints。
- [ ] 定义 `ToolSpec`：输入、输出、成本、风险、适用标签、失败模式。
- [ ] 实现 rule-based routes：`reflection_route`、`shadow_projection_route`、`causal_settle_route`、`direct_global_edit`、`localized_inpaint`、`qa_eval_only`。

高风险 route：

| Route | 风险原因 |
|---|---|
| `causal_settle_route` | 需要预测稳定态和新接触关系 |
| `shadow_projection_route` | 需要旧影删除、新影位置、方向、软硬一致 |
| `reflection_route` | 主体、反射面、倒影必须成对更新 |

## P3：Executor 路线化执行

目标：让执行层体现 route 差异，逐步从单次 whole-image edit 扩展到局部、两阶段和候选选择。

待办：

- [ ] 为每条 route 准备 route-specific prompt template。
- [ ] 保留低风险任务的 `one_pass_direct_edit`。
- [ ] 为 Reflection 和 Light_Propagation 支持 two-pass：先完成主体变化，再补齐反射/阴影/光照。
- [ ] 为 Causality 支持 `one_pass_with_strong_final_state` 或 `best_of_n=3`。
- [ ] 记录 `execution_trace`：实际 route、工具调用、输入输出路径、fallback、候选数和失败原因。

## P4：Route-aware Verifier

目标：Verifier 不再只给通用分数，而是按 route 检查必须满足的物理条件。

待办：

- [ ] Verifier 输入 `TaskProfile`、route、metadata 和 PICABench QA。
- [ ] 根据 `physics_law + edit_operation + route` 生成 law-specific checklist。
- [ ] 区分 `must_pass` 和 `soft_score`，must-pass 失败时不能 accept。
- [ ] 输出 `check_results`、`blocking_failures`、`route_hints`、`repair_instruction`。
- [ ] 对 accepted 但 PICAEval 低分的 case 建立回归记录。

## P5：Retry Loop 与实验闭环

目标：让失败信息结构化回流到 Planner、Router 和 Executor，而不是只拼成自然语言 repair prompt。

待办：

- [ ] 将 blocking failures 转成 route hints，例如 `missing_reflection`、`shadow_not_reprojected`、`support_removed_without_settle`。
- [ ] Retry 时允许 Router 根据失败类型切换 route 或提高候选预算。
- [ ] 高风险任务在 verifier 稳定后启用 best-of-N。
- [ ] 实验汇总按 `physics_category`、`physics_law`、`edit_operation`、`route`、`question_type`、`context_risk` 分组。

## P6：真实视觉工具接入

目标：在评测协议、TaskProfile、Router 和 Verifier 稳定后，再接入 detector、segmenter、mask editor、inpainting 等重工具。

接入顺序：

1. 轻量工具：coordinate mapper、law-specific verifier、mask generator stub、dependency region expander。
2. 真实视觉工具：object detector、segmenter、local mask editor、inpainting。
3. 每个工具补齐 `ToolSpec`、文件约定、失败模式和 fallback。
4. 每个工具必须用固定 regression cases 验证收益，不能只看单例视觉效果。

## 短期执行顺序

1. 定义 `RouteDecision` 和 `RouteSpec` 的最小 schema，把 `TaskProfile.route_hints` 转成可审计路由决策。
2. 先实现 `causal_settle_route` 的最小版本：使用压缩 executor prompt、记录 route、dependent regions、preserve scope 和 failure modes。
3. 用 `0000`、`0294`、`0358` 做 route-level 回归：比较 direct edit、compressed PhysicalIntent 和 causal route。
4. 为 `causal_settle_route` 增加局部控制：限制可改区域、保护非目标身份、记录候选输出和失败原因。
5. 实现 route-aware verifier 的最小版本，把 `must_pass_checks` 转成结构化 `check_results` 和 `blocking_failures`。
6. 将 `explicit_prompt -> TaskProfile` 字段抽取移动到后续弱监督数据构建，不阻塞当前 router/executor 开发。
7. 在 route 和 verifier 稳定后，再接入 mask、detection、segmentation 等重工具。

## 开发原则

- PICABench 样例优先作为 regression cases。
- `explicit_prompt` 是弱监督和 upper bound，不是真实推理输入。
- 每个 route 必须说明适用物理类型、输入要求、失败模式和 fallback。
- 每个新工具必须有 `ToolSpec`。
- VLM 判断要拆成可解释分项，重要失败不能只藏在 rationale。
- 不在任务画像和评测协议未稳定前优化重工具。
- API key 只从本地 `.env` 或环境变量读取，不写入源码、文档或日志。

## 待确认

- 是否允许安装或运行 GroundingDINO、SAM/SAM2、LaMa 等本地模型。
- 是否优先使用闭源 API 的 mask edit 能力，还是先实现本地 mask/inpaint 接口。
- PICABench 评测是否只做定性展示，还是继续维护批量表格和可量化分数。
- 当前图像编辑 API 默认输出 `1024x1024`，后续是否请求原图比例输出，还是继续使用 canonical + unpadding 协议。

## 参考工作

| 工作 | 对本项目的作用 |
|---|---|
| PICABench / PICAEval | 定义物理一致性编辑任务、taxonomy 和 region-grounded QA |
| PHYRE | 用动作干预、目标状态和稳定结果定义物理任务 |
| CLEVRER | 将因果任务拆成 descriptive、explanatory、predictive、counterfactual |
| Physion / IntPhys | 提供物理后果预测和直觉物理评测思想 |
| ReAct / HuggingGPT / Visual ChatGPT | 提供 planner、router、tool-use agent 的工程参考 |

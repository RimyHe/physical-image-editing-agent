# Physical Agent 开发计划

## 当前开发重点

下一阶段重点是扩充 tool router 和物理一致性评分机制，使系统从当前的 `direct_edit` MVP 发展为物理类别感知的工具编排系统。

参考调研笔记：[`tool_router_physics_tool_research.md`](tool_router_physics_tool_research.md)

## 目标架构

```text
User image + instruction
  -> Planner: 生成 task profile 和初始 edit prompt
  -> Router: 根据编辑动作、物理依赖、空间范围选择 route/toolchain
  -> Tool Executor: direct edit / mask edit / detection / segmentation / inpainting / QA
  -> Verifier: VLM 分项评分 + PICABench QA + deterministic guardrails
       -> pass: accept
       -> fail: 生成 repair instruction，并带历史反馈重新 route/edit
```

## 阶段 1：Router 与 ToolSpec 骨架

目标：先建立可扩展的工具抽象，不急于接入所有外部模型。

任务：

1. 定义 `ToolSpec`：
   - `name`
   - `route`
   - `required_inputs`
   - `provided_outputs`
   - `cost`
   - `risk`
   - `physics_tags`
   - `failure_modes`
2. 定义 `RouteSpec`：
   - `route`
   - `applicable_operations`
   - `applicable_physics_laws`
   - `toolchain`
   - `verification_focus`
   - `fallback_route`
3. 将现有 `select_route(plan)` 改成基于 task profile 的规则路由。
4. 保留 `direct_edit` 作为默认 fallback，避免路由失败导致流程不可运行。

优先 routes：

| route | 适用任务 | 初始实现 |
| --- | --- | --- |
| `direct_global_edit` | 天气、季节、整体光照、全局状态变化 | 调用现有 image edit API |
| `localized_inpaint` | 小目标删除/替换，背景需保持 | 先用 whole-image fallback，预留 mask 输入 |
| `remove_with_physics` | 删除支撑物、光源、反射物、遮挡物 | 先生成依赖区域说明，后续接 detector/segmenter |
| `add_with_effects` | 添加物体、开灯、加火/水源 | 先强化 prompt 和 verifier focus |
| `move_or_deform` | 移动、拉伸、倾斜、倒塌 | 先规则识别，后续接 keypoint/drag 工具 |
| `qa_eval_only` | PICABench 评测和 debug | 不编辑，只运行 QA verifier |

## 阶段 2：Task Profile

目标：Planner 不只输出自由的 `edit_prompt`，还要输出 router 可用的结构化任务画像。

建议字段：

```json
{
  "operation": "remove | add | move | replace | deform | weather | lighting | state_change",
  "physics_law": "Light_Propagation | Light_Source_Effects | Reflection | Refraction | Deformation | Causality | Global | Local",
  "target_objects": [],
  "dependent_effects": [],
  "edit_scope": "global | local | object | region",
  "preserve_scope": [],
  "requires_mask": false,
  "requires_detection": false,
  "requires_reference": false,
  "expected_stable_outcome": ""
}
```

Router 应主要使用这些字段，而不是完全相信 Planner 输出的 `route`。

## 阶段 3：评分机制升级

目标：从单一 VLM 自评分升级为混合评分 gate。

评分组成：

| 组件 | 作用 |
| --- | --- |
| `instruction_score` | 是否完成用户显式指令 |
| `preservation_score` | 非目标内容、身份、构图是否保留 |
| `physics_score` | 阴影、反射、接触、状态、力学结果是否合理 |
| `physics_qa_score` | PICABench annotated QA 的 yes/no 通过率 |
| `guardrail_pass` | 尺寸、格式、画幅、输出存在、非编辑区一致性等确定性检查 |

初始 accept 规则建议：

```text
accept = guardrail_pass
  and instruction_score >= 8
  and preservation_score >= 7
  and physics_score >= 7
  and physics_qa_score >= configured_threshold when QA is available
```

必须尽快加入的 guardrails：

1. 输出图存在且是有效 PNG。
2. 输出尺寸与输入尺寸一致，或经过明确允许的 resize/crop 策略。
3. 对 PICABench 样例，记录 annotated QA 的逐项判断。
4. 非编辑区不应发生大范围漂移；首版可先记录风险，后续用 mask + PSNR/SSIM。

## 阶段 4：物理依赖区域工具

目标：让工具不只定位目标物体，还能定位物理依赖区域。

优先支持：

| 物理类型 | 需要定位的区域 |
| --- | --- |
| 光照/阴影 | 光源、受光面、投影方向、阴影宿主表面 |
| 反射 | 反射物、镜面/水面/金属面、反射区域 |
| 折射 | 透明介质、背景穿透区域、边界 |
| 因果/支撑 | 被删/移动对象、支撑点、接触区、受影响对象 |
| 形变 | 目标物、锚点、受力方向、连续纹理区域 |
| 全局状态 | 天空、道路/地面、植被、材质表面、空气/能见度 |
| 局部状态 | 材料变化区域、热/湿/冻/烧/破裂影响范围 |

实现顺序：

1. 先让 Planner/Router 显式列出 dependent regions。
2. 再接入 detector/segmenter 生成候选 mask。
3. 最后让 verifier 检查 dependent regions 是否同步更新。

## 阶段 5：候选生成与重试策略

目标：降低单次图像编辑随机性。

计划：

1. 为高风险 route 支持 `best_of_n`。
2. 每个候选都运行相同 verifier。
3. 选择综合分最高的候选，而不是第一个 pass 的候选。
4. 成本预算写入 settings，防止候选数量失控。
5. 重试时将失败项转化为新的 route hints，而不只是拼接自然语言 repair prompt。

## 开发原则

- 每个新工具必须有 `ToolSpec`，不能只在代码里硬编码调用。
- 每个 route 必须说明适用物理类型、输入要求、失败模式和 fallback。
- VLM 判断必须尽量拆成可解释分项；重要失败不能只藏在 `rationale`。
- PICABench 样例优先作为 regression cases。
- API key 仍只从本地 `.env` 或环境变量读取，不写入源码、文档或日志。

## 待确认

- 是否允许安装或运行 GroundingDINO、SAM/SAM2、LaMa 等本地模型。
- 是否优先使用闭源 API 的 mask edit 能力，还是先实现本地 mask/inpaint 接口。
- PICABench 评测是否只做定性展示，还是需要批量表格和可量化分数。
- 当前 `gpt-image-2` 输出尺寸默认 `1024x1024`，需要决定是请求原图比例、后处理回原尺寸，还是在 verifier 中判失败。

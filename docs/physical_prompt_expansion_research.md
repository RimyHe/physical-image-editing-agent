# PhysicalIntentExpander 调研报告

## 结论摘要

本报告面向 P0 组件 `PhysicalIntentExpander`，目标是研究：如何把 PICABench 的短 `superficial_prompt` 扩展成更适合图像编辑模型执行的物理一致性指令。

核心结论：

1. 扩写器不应只是把一句话改写得更长，而应先生成结构化的物理任务画像，再渲染成最终编辑 prompt。
2. `explicit_prompt` 可以作为教师信号和弱监督来源，但不能直接视为绝对真值。它可能包含过度具体、不可从图像确认或与真实物理后果不一致的描述。
3. 物理扩写必须显式表示“当前状态、干预动作、受影响对象、最终稳定状态、视觉证据和保持区域”。
4. 对阴影、反射、折射和因果任务，应该使用不同的物理模板，而不是统一追加“保持物理一致性”。
5. 第一阶段不建议直接使用强化学习。应先用规则骨架、VLM 结构化输出和人工/自动校验建立可解释 baseline，再考虑监督微调、偏好优化或 RL。
6. PICABench 的 50-case 集合应继续作为固定 regression/test set，不应直接用于训练扩写器。

## 1. 研究问题

当前 agent 的 Planner 接收图像和编辑指令，直接输出自由结构 JSON 与 `edit_prompt`：

```text
image + instruction
  -> Planner
  -> edit_prompt
  -> image editor
```

当前 Planner 的系统提示只要求在相关时提到 shadows、reflections、occlusion、contact、lighting 和 perspective，但没有规定：

- 哪些对象是编辑目标；
- 哪些对象会被物理干预影响；
- 编辑后系统应达到什么最终稳定状态；
- 哪些区域必须保持不变；
- 物理后果如何被图像观察和验证；
- 哪些细节来自图像证据，哪些只是模型推断。

因此，P0 的问题不是“如何让 prompt 更详细”，而是：

> 如何将短编辑意图转化为有物理结构、可验证、不过度臆造的编辑任务表示。

## 2. 相关工作

### 2.1 PICABench：扩写 prompt 但不把语言当作物理本身

PICABench 将物理一致性分为 Optics、Mechanics 和 State Transition，并用区域级、人类标注的 yes/no 问题评估阴影、反射、接触、变形和状态变化。其项目页面说明，数据构建流程会把人类编辑指令扩展为三个复杂度等级，并在主模型比较中默认使用 `superficial prompts`。这说明三种 prompt 是一种控制变量，而不是三个不同任务。[PICABench project](https://picabench.github.io/)

PICABench 还引入 PICA-100K，通过视频生成物理过程和编辑监督，改善模型的物理一致性。项目页面报告，视频驱动数据微调比单纯依赖文本指令更能补充动态和物理后果信息。[PICABench project](https://picabench.github.io/)

对本项目的启示：

- `superficial_prompt` 适合作为 agent 的真实输入；
- `explicit_prompt` 适合作为扩写目标的候选教师信号；
- 物理扩写不能代替物理监督；
- 扩写结果必须回到 PICAEval 的局部问题和非编辑区指标上验证。

### 2.2 InstructPix2Pix、MagicBrush：指令质量和数据质量会直接影响编辑结果

InstructPix2Pix 将图像编辑建模为“输入图像 + 自然语言编辑指令 -> 编辑图像”。MagicBrush 进一步使用人工标注的真实图像编辑三元组，覆盖单轮、多轮、有 mask 和无 mask 的编辑，并指出自动合成指令数据含有较多噪声，人工标注有助于提高编辑质量。[InstructPix2Pix](https://arxiv.org/abs/2211.09800)；[MagicBrush](https://arxiv.org/abs/2306.10012)

对本项目的启示：

- explicit prompt 不是天然高质量标签；
- 需要区分“语言覆盖了更多要求”和“语言描述了正确要求”；
- 扩写器训练数据应保留图像、短指令、扩写指令和最终图像/评分的对应关系；
- 关键物理任务应加入人工复核，而不能完全依赖另一个 VLM 生成标签。

### 2.3 Complex-Edit：复杂度增加会伤害保持区域，不能无限扩写

Complex-Edit 使用 Chain-of-Edit 先生成原子编辑，再组合成复杂指令。其分析指出，指令复杂度增加会明显损害输入图像中关键内容的保持；将复杂指令拆成多个顺序编辑步骤也可能降低结果质量，而 Best-of-N 能部分缓解这一问题。[Complex-Edit](https://arxiv.org/abs/2504.13143)

对本项目的启示：

- 扩写 prompt 必须有信息预算；
- 结构化分解可以用于内部推理，但不应机械地变成多次图像编辑调用；
- 应优先生成一条连贯的最终状态 prompt；
- 每次扩写都必须有 `preserve_scope`，避免物理细节扩散到无关区域；
- prompt 长度和物理收益应作为实验变量记录。

### 2.4 Prompt-to-Prompt：文本变化会改变空间布局和内容保持

Prompt-to-Prompt 研究表明，扩展或替换文字不仅改变语义，也会通过文本-图像交互影响空间布局。其方法通过保留源 prompt 的部分注意力关系来提升编辑区域控制和原图保持。[Prompt-to-Prompt](https://arxiv.org/abs/2208.01626)

当前项目使用的是闭源图像编辑 API，无法直接控制 cross-attention。因此只能在 prompt 层模拟这一原则：

- 明确目标对象和原位置；
- 明确新位置或最终姿态；
- 明确保持对象和背景；
- 将新增物理后果限制在必要依赖区域；
- 避免在 prompt 中加入与任务无关的风格、质量或环境变化词。

### 2.5 CLEVRER：物理任务应拆成描述、解释、预测和反事实

CLEVRER 将视觉因果问题分为 descriptive、explanatory、predictive 和 counterfactual 四种类型，并发现模型在感知型问题上较强，但在解释、预测和反事实任务上明显更弱。[CLEVRER](https://openreview.net/forum?id=HkxYzANYDB)

这与 PICABench 的物理编辑非常接近：

| CLEVRER 类型 | 对应图像编辑问题 |
|---|---|
| Descriptive | 当前有哪些对象、支撑、接触、阴影和反射 |
| Explanatory | 为什么该物体当前稳定，谁提供支撑或约束 |
| Predictive | 执行编辑后会出现什么最终状态 |
| Counterfactual | 如果移除/移动某个因素，哪些对象和视觉效果必须改变 |

对 `Causality` 任务，扩写器应显式经过这四步，而不是直接把 `remove` 改成更长的句子。

### 2.6 PHYRE：用目标状态和约束表达物理后果

PHYRE 将物理推理任务表示为初始状态、动作和目标状态：智能体需要选择一个干预，使模拟后的场景满足目标。其关键思想不是生成一段漂亮的解释，而是判断干预后是否达到可检验的 goal state。[PHYRE](https://arxiv.org/abs/1908.05656)

对本项目的启示：

- `final_state` 应是必填字段；
- `must_pass_checks` 应从最终状态直接派生；
- prompt 中的物理描述应尽量转化为可观察约束；
- “看起来合理”不应替代“哪些关系必须成立”。

### 2.7 InPhyRe：视觉物理推理存在语言偏置和归纳不足

InPhyRe 研究发现，大型多模态模型在未见过的物理环境中进行归纳式物理推理时表现较弱，并可能受语言偏置影响而忽略图像证据。[InPhyRe](https://arxiv.org/abs/2509.12263)

对本项目的启示：

- 扩写器不能只读取 `superficial_prompt` 和 `explicit_prompt`；
- 必须读取原图中的参考阴影、支撑关系、光源方向、反射面和材质边界；
- 对无法确认的物理关系输出 `uncertainties`；
- 不能把数据集提供的详细文字当作图像事实；
- verifier 需要检查 prompt 是否与图像证据冲突。

## 3. 物理 prompt 扩写的核心表示

### 3.1 推荐的 TaskProfile

```json
{
  "target_objects": [],
  "operation": "",
  "physical_operation": "",
  "current_state": {
    "pose": "",
    "support_relations": [],
    "contact_points": [],
    "relevant_effects": []
  },
  "intervention": {
    "changed_factor": "",
    "removed_or_added_object": "",
    "spatial_change": ""
  },
  "final_state": {
    "pose": "",
    "support_relations": [],
    "contact_points": [],
    "secondary_object_changes": []
  },
  "physical_dependencies": [],
  "dependent_regions": [],
  "reference_cues": [],
  "preserve_scope": [],
  "must_pass_checks": [],
  "uncertainties": [],
  "edit_prompt": ""
}
```

其中最重要的字段不是 `edit_prompt`，而是：

1. `physical_operation`：把普通动作改写成物理干预，例如 `remove_support_and_settle`。
2. `final_state`：明确最终稳定姿态、接触关系和受影响对象。
3. `physical_dependencies`：记录阴影、反射、折射、接触、遮挡、光照和材料状态。
4. `preserve_scope`：保护不应随编辑改变的对象和区域。
5. `must_pass_checks`：将物理后果变成可验证条件。

### 3.2 扩写器的输入边界

#### 训练阶段可以使用

- 原图；
- `superficial_prompt`；
- `explicit_prompt`；
- `intermediate_prompt`；
- PICABench 的 `physics_category`、`physics_law`、`edit_operation`；
- `edit_area` 和 annotated QA；
- 编辑结果和评分。

#### 真实推理阶段应使用

- 原图；
- 用户的短 prompt；
- 由模型或规则推断的任务类别；
- 原图中的视觉参考证据；
- 上一轮 verifier 反馈。

PICABench 的金标准 `physics_law`、QA 答案和 `explicit_prompt` 不应直接作为真实推理时的输入，否则会把评测标注泄漏给 agent。

## 4. 物理类别的扩写规则

### 4.1 Light Propagation：阴影不是物体轮廓的复制品

扩写器应提取：

- 主光源方向；
- 目标物与承接面的关系；
- cast shadow 与 contact shadow；
- 阴影起点、方向、长度和大致区域；
- 距离造成的软化和衰减；
- 周围物体已有阴影作为参考；
- 旧位置阴影是否需要移除。

推荐写法：

```text
Move the tulip to the requested position while preserving its appearance.
Remove the old contact/cast shadow at the original position.
Create a new soft shadow on the receiving surface in the same light direction
as nearby reference shadows. The shadow should become softer and lighter with
distance and should not be a sharp copy of the tulip silhouette.
```

应避免：

```text
Create a sharp, complete shadow identical to the tulip outline.
```

0816 暴露的正是这种问题：如果扩写器把“有影子”错误地扩成“轮廓清晰、完整、锐利的影子”，语言更详细反而会降低结果质量。

### 4.2 Reflection：主体、反射面和倒影必须成对表示

扩写器应提取：

- 主体对象；
- 反射面或水面；
- 主体与反射面的接触关系；
- 反射轴/水线；
- 倒影的相对位置、方向和尺度；
- 倒影的亮度、饱和度、模糊程度；
- 主体和倒影共同遮挡的背景区域。

推荐依赖表示：

```text
subject -> reflective_surface -> reflected_subject
```

不能只在 prompt 末尾追加“add a realistic reflection”，因为这没有说明反射应出现在哪里、关于哪条轴对称、与主体如何对应。

### 4.3 Refraction：描述介质变化和背景重建

折射任务需要区分：

- 透明介质本体；
- 介质内部的液体或空气；
- 被折射/扭曲的背景；
- 水线、caustic、高光和边界；
- 移除介质后背景应恢复的连续性。

例如移除玻璃中的水，不应只写“remove the water”，还要表达：

```text
Remove water-dependent refraction, waterline, caustics, and internal highlights.
Restore the background and object appearance as seen through empty glass and air.
Keep the glass geometry and dry-glass reflections.
```

### 4.4 Causality：用干预链表示最终稳定态

推荐的内部分解：

```text
descriptive
  -> 当前对象、支撑、接触和稳定原因
explanatory
  -> 哪个因素维持当前状态
counterfactual
  -> 执行 remove/move/add 后哪些关系消失
predictive
  -> 最终姿态、接触点、阴影和受影响对象
visual realization
  -> 将这些结果写成编辑 prompt 和 must-pass checks
```

例如删除摩托车脚撑：

```text
physical_operation: remove_support_and_settle
intervention: remove the kickstand and its ground contact
final_state: motorcycle rests on its left side
secondary_effects:
  - left-side body/engine contacts the road
  - wheels and pose change consistently
  - old kickstand shadow disappears
  - broad contact shadow appears along the left side
must_pass_checks:
  - kickstand absent
  - motorcycle no longer upright
  - left-side contact visible
  - contact shadow consistent with the new pose
```

### 4.5 Deformation：区分刚体位姿变化和材料形变

扩写器应先判断：

- 是刚体移动/旋转；
- 还是柔性物体拉伸、弯曲、压缩；
- 哪些端点或接触点保持不变；
- 形变是否连续；
- 纹理、褶皱和高光是否应随材料变化。

避免只写“bend the object realistically”。应明确形变的受力方向、固定端、材料连续性和邻接结构。

### 4.6 Global / Local State：先确定传播范围

对于天气、季节、昼夜等全局状态：

- 规定全局传播范围；
- 统一天空、光照、色温、阴影、材质和能见度；
- 不强行使用小目标 mask。

对于局部湿润、结冰、融化、烧焦等局部状态：

- 规定状态变化边界；
- 描述材料响应和邻近影响；
- 明确周围区域保持不变；
- 防止局部效果扩散成全局风格变化。

## 5. 推荐组件架构

### 5.1 处理流程

```text
superficial_prompt + image
  -> IntentNormalizer
  -> LabelPolicyCompiler
  -> SceneEvidenceExtractor
  -> InterventionGraphBuilder
  -> StableStatePredictor
  -> VisualEvidencePlanner
  -> PreserveScopePlanner
  -> TaskProfileValidator
  -> PromptRenderer
  -> existing Planner / Router / Executor / Verifier
```

### 5.2 各模块职责

| 模块 | 作用 | 第一阶段实现 |
|---|---|---|
| `IntentNormalizer` | 识别目标对象和基础动作 | VLM JSON |
| `LabelPolicyCompiler` | 根据 law/operation 注入不可漏的物理字段 | 规则表 |
| `SceneEvidenceExtractor` | 找参考阴影、反射面、支撑、接触和材质边界 | VLM 描述，暂不依赖重 CV 工具 |
| `InterventionGraphBuilder` | 将动作表示为被改变的因果因素 | 规则 + VLM |
| `StableStatePredictor` | 预测最终姿态、接触和 secondary effects | VLM constrained JSON |
| `VisualEvidencePlanner` | 把物理状态转成可观察视觉条件 | 模板 + VLM |
| `PreserveScopePlanner` | 明确不应变化的区域 | 原图元数据 + VLM |
| `TaskProfileValidator` | 检查字段完整性和物理逻辑 | 规则校验 |
| `PromptRenderer` | 生成最终编辑 prompt | route-specific 模板 |

### 5.3 规则优先，VLM 填充

建议采用：

```text
规则决定：
  - 哪些字段必须存在
  - 某类 physics law 必须检查什么
  - 普通 operation 如何改写为 physical_operation
  - 哪些依赖不能被省略

VLM 决定：
  - 图像中具体对象是谁
  - 参考证据位于哪里
  - 受影响对象和区域是什么
  - 最终稳定状态的具体视觉表现

Validator 决定：
  - 输出是否完整
  - 是否与图像证据矛盾
  - 是否过度具体
  - 是否遗漏 preserve scope
```

这比让 Planner 一次性自由生成长 prompt 更容易调试和归因。

## 6. 训练和数据策略

### 6.1 第一阶段：不训练，先建立可解释 baseline

先用现有 VLM 做结构化输出：

```text
superficial_prompt + image + policy scaffold
  -> TaskProfile JSON
```

使用 few-shot 示例和规则校验，先确定：

- 哪些字段经常缺失；
- 哪些 physics law 容易误判；
- 哪些 explicit prompt 细节会造成错误；
- 结构化输出是否比直接长 prompt 更稳定。

### 6.2 第二阶段：弱监督抽取

将 `explicit_prompt` 解析为候选字段：

| explicit 文本片段 | 结构化字段 |
|---|---|
| “rests on its left side” | `final_state.pose` |
| “remove its shadow” | `physical_dependencies.shadow` |
| “keep the background unchanged” | `preserve_scope.background` |
| “contact with the ground” | `final_state.contact_points` |

然后用原图、QA、edit area 和人工抽查进行校正。

注意：不要把“从 explicit 文本抽取字段”误认为“验证了物理真值”。它只是产生候选标签。

### 6.3 第三阶段：监督微调

只有在结构化数据质量稳定后，才考虑 SFT：

```text
input:
  image + superficial_prompt + policy scaffold

target:
  validated TaskProfile
```

建议训练目标优先级：

1. 必填字段完整；
2. `physical_operation` 正确；
3. `final_state` 与 QA 参考答案一致；
4. `preserve_scope` 不扩大；
5. `edit_prompt` 语言质量。

### 6.4 第四阶段：偏好优化或强化学习

强化学习应放在最后。候选 reward 可以是：

```text
reward =
  w1 * PICAEval QA accuracy
  + w2 * non-edit-region preservation
  + w3 * verifier must-pass rate
  + w4 * prompt evidence coverage
  - w5 * hallucinated dependency penalty
  - w6 * unnecessary edit scope penalty
```

必须避免：

- 只优化 VLM-as-judge；
- 用同一批 50 个测试样本训练和选择 prompt；
- 把更长 prompt 当作更高质量 prompt；
- 用 explicit 文本直接泄漏 QA 答案或物理标签。

## 7. P0 实验设计

### 7.1 三条主要对照线

| 实验 | 输入 | 目的 |
|---|---|---|
| A: superficial baseline | `superficial_prompt` | 真实官方口径 baseline |
| B: explicit upper bound | `explicit_prompt` | 估计详细人工指令的上限 |
| C: PhysicalIntentExpander | `superficial_prompt + image` | 测试新增组件的实际收益 |

三组实验必须固定：

- 同一 executor；
- 同一模型；
- 同一 canonical/crop 协议；
- 同一 PICAEval；
- 同一重试预算；
- 同一 50-case regression set。

### 7.2 扩写器本身的指标

不能只看最终图片分数，还应记录：

| 指标 | 含义 |
|---|---|
| Schema completeness | 必填结构化字段的填充率 |
| Physical operation accuracy | 普通动作是否被正确改写为物理动作 |
| Final-state coverage | 是否覆盖 QA 涉及的最终状态 |
| Dependency coverage | 是否覆盖阴影、反射、接触等必要依赖 |
| Evidence grounding | 描述是否能在原图中找到依据 |
| Hallucination rate | 是否添加图像中不存在或无法确认的细节 |
| Preserve completeness | 是否明确关键保持区域 |
| Prompt length | 扩写后的 token 数和复杂度 |

### 7.3 最终图像指标

继续使用当前项目的：

- QA answer accuracy；
- non-edit-region PSNR；
- agent accepted；
- verifier pass rate。

并增加按以下维度统计：

- `physics_law`；
- `edit_operation`；
- `question_type`；
- `context_risk`；
- prompt level；
- expansion failure type。

### 7.4 最小实验集

优先使用已有重点 case：

| Case | 重点 |
|---|---|
| `0816` | 阴影软硬、阴影位置、阴影是否被错误写成物体轮廓 |
| `0387` | 添加主体位置、反射、反射区域和水面关系 |
| `0294` | 支撑移除、最终倒伏、接触和接触阴影 |

然后扩展到每个 physics law 至少 3 个 case，避免只针对单个失败样本过拟合。

## 8. 风险与控制

### 风险 1：扩写器把错误的 explicit prompt 学得更稳定

控制：

- explicit 只作为弱监督；
- 保留 `uncertainties`；
- 用 QA 和原图人工复核；
- 对 0816 等争议样本建立“标注风险”字段。

### 风险 2：prompt 变长导致非编辑区域变差

控制：

- 强制 `preserve_scope`；
- 记录 prompt length；
- 比较 direct long prompt 与 structured renderer；
- 使用 non-edit PSNR 作为硬指标之一。

### 风险 3：物理描述与图像证据不一致

控制：

- 先生成 `reference_cues`；
- 每个物理结论要求对应图像证据；
- 对无法确认的字段输出 uncertainty；
- Verifier 检查 prompt 和原图是否冲突。

### 风险 4：训练或推理泄漏 PICABench 标签

控制：

- 训练阶段可以使用标签；
- 真实推理阶段不直接输入金标准 law、QA 或 explicit prompt；
- 50-case 只做测试；
- 记录每次实验的 `prompt_level` 和 `metadata_visibility`。

### 风险 5：把扩写器误认为物理模拟器

控制：

- 明确扩写器只产生假设和可观察约束；
- 不声称它进行了真实动力学仿真；
- 后续通过视频监督、几何工具或专门 verifier 补充物理依据。

## 9. 对当前项目的具体建议

### 建议一：先改 Planner 接口，不先改 Executor

当前 `planner.py` 已有 `physics_dependencies` 和 `verifier_focus` 字段，但它们是自由文本。第一步应把 Planner 输出改成兼容 TaskProfile 的结构化 JSON。

建议保留现有字段以兼容旧运行：

```json
{
  "target": "...",
  "operation": "...",
  "preserve": [],
  "physics_dependencies": [],
  "route": "direct_edit",
  "edit_prompt": "...",
  "verifier_focus": [],
  "task_profile": {}
}
```

### 建议二：先做 rule scaffold + VLM，而不是单独训练扩写模型

现有 PICABench 标签和 8 个 physics law 足以先构建规则表。规则表负责防遗漏，VLM 负责看图补充对象、区域和视觉细节。

### 建议三：Prompt renderer 要按 physics law 分模板

至少先实现：

- `shadow_projection_template`；
- `reflection_template`；
- `refraction_template`；
- `causal_settle_template`；
- `deformation_template`；
- `global_state_template`；
- `local_state_template`。

### 建议四：将 prompt 扩写失败单独记录

扩写器失败与图像编辑失败要分开：

```text
expansion_failure:
  missing_final_state
  missing_dependency
  unsupported_detail
  evidence_conflict
  preserve_scope_missing
  wrong_physical_operation
```

否则最终 QA 下降时无法知道是 prompt 生成错误还是 executor 执行错误。

## 10. 最终决策

P0 推荐采用以下方案：

```text
superficial_prompt + image
  -> rule-based policy scaffold
  -> VLM structured physical intent expansion
  -> validator
  -> physics-law-specific prompt renderer
  -> existing Planner / Executor
```

暂不实施：

- 直接用 50-case 训练扩写器；
- 直接把 explicit prompt 当作 ground truth；
- 第一阶段就做 RL；
- 让扩写器自由生成无限长度的 prompt；
- 使用 PICABench 金标准标签作为真实推理输入。

P0 的验收标准应是：在固定 50-case、同一 executor 和同一评测协议下，`superficial + expander` 相比 `superficial baseline` 在 QA accuracy 和物理失败率上有稳定改善，同时 non-edit-region PSNR 不显著下降，并且扩写结果能够解释每个关键物理依赖来自哪里。

## 参考资料

| 资料 | 关键贡献 | 链接 |
|---|---|---|
| PICABench | 三层 prompt、物理 taxonomy、PICAEval、PICA-100K | https://picabench.github.io/ |
| PICABench paper | 物理一致性图像编辑 benchmark | https://arxiv.org/abs/2510.17681 |
| MagicBrush | 人工标注的真实图像编辑指令数据 | https://arxiv.org/abs/2306.10012 |
| InstructPix2Pix | 指令驱动图像编辑模型 | https://arxiv.org/abs/2211.09800 |
| Prompt-to-Prompt | 文本编辑与空间保持的 cross-attention 控制 | https://arxiv.org/abs/2208.01626 |
| CLEVRER | 描述、解释、预测、反事实因果分解 | https://openreview.net/forum?id=HkxYzANYDB |
| PHYRE | 初始状态、干预动作和目标状态物理任务表示 | https://arxiv.org/abs/1908.05656 |
| InPhyRe | 多模态模型的归纳式物理推理和语言偏置 | https://arxiv.org/abs/2509.12263 |
| Complex-Edit | 复杂度可控的指令构造与保持区域风险 | https://arxiv.org/abs/2504.13143 |
| HumanEdit | 人类奖励和多轮人工校验的编辑数据 | https://arxiv.org/abs/2412.04280 |

## 与现有文档的关系

- `docs/development_plan.md`：维护 P0 任务和实施顺序。
- `docs/picabench_examples.md`：说明三层 prompt 和 PICABench 评测口径。
- `docs/tool_router_physics_tool_research.md`：维护 Router、工具和物理依赖区域调研。
- `docs/physical_dataset_progress_report.md`：记录实际遇到的问题、错误和解决过程。

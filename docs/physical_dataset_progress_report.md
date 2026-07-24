# Physical Image Editing Agent 进展汇报

本文档只记录已经发生的阶段性事实、问题、修复和人工观察。后续开发路线、优先级和待办放在 [`development_plan.md`](development_plan.md)。

## 1. 项目当前评测背景

### 背景

本项目目标是基于闭源图像编辑 API 构建物理一致性图像编辑 Agent。当前 MVP 流程：

```text
input image + instruction
  -> Planner
  -> Router，目前 fallback 到 direct_edit
  -> Image Edit API
  -> Verifier
  -> retry / accept
```

本地评测集使用 `Andrew613/PICABench` 的 50 个样本，覆盖 8 个 physics law。

| Category | Physics law | Cases |
|---|---|---:|
| Mechanics | Causality | 7 |
| Mechanics | Deformation | 6 |
| Optics | Light_Propagation | 6 |
| Optics | Light_Source_Effects | 6 |
| Optics | Reflection | 6 |
| Optics | Refraction | 6 |
| State | Global | 7 |
| State | Local | 6 |

### 观察

当前版本主要验证闭环流程，不代表完整工具路由能力。Router 还没有真正接入 detection、segmentation、mask edit 或 local repaint。

## 2. 输出尺寸固定导致 box 错位

### 背景

PICABench 的 `box` 和 `edit_area` 基于原图坐标，但图像编辑 API 倾向输出固定 `1024x1024`。

### 问题

如果直接用原始 box 或简单宽高缩放，会导致 QA crop 和 non-edit PSNR 的区域错位。

### 处理

当前采用 canonical canvas：

```text
原图
  -> contain 到 1024x1024
  -> 保存 coordinate_transform
  -> 调用 image edit API
  -> source box -> canonical box -> output box
```

## 3. Padding 黑边影响结果展示与评测

### 背景

为保持原图比例，非正方形图片会被 contain 到 `1024x1024`，因此出现上下或左右 padding 黑边。

### 问题

黑边可能被模型或 verifier 当作真实图像内容；同时展示时也不符合原始数据集画幅。

### 处理

当前同时保留两种输出：

| 输出 | 用途 |
|---|---|
| padded candidate | 保留 API 原始 `1024x1024` 结果，便于审计 |
| unpadded final image | 去掉 padding，并恢复到原图尺寸，用于主展示和 PICABench 评分 |

Gradio 页面同时展示两者。

## 4. 局部 crop 丢失全局语境

### 背景

PICABench QA 有些问题询问全局位置，例如 upper、lower、left、right、corner、center。

### 问题

如果只给局部 crop，目标会出现在裁剪图中央，VLM 可能基于局部画布回答，而不是完整图片位置。

### 处理

当前按问题类型选择评测视图：

| question_type | evaluation_view |
|---|---|
| `global_position` | full image |
| `local_appearance` | crop |
| `mixed` | full image + crop |
| `unknown` | crop，并标记 context risk |

## 5. QA 批量回答缺项

### 背景

为减少单图耗时，当前按 evaluation view 将多个 QA 合并成批量 VLM 请求。

### 问题

VLM 有时不会返回所有 question index，导致某些 `predicted_answer` 为空。

### 处理

已加入 fallback：批量响应缺失某题答案时，对该题单独补问。

## 6. API 不稳定导致批跑中断

### 背景

批量运行 50 个 PICABench case 时，外部 API 会出现 timeout、429 cooldown、DeploymentNotFound 等问题。

### 问题

普通批跑脚本遇到单个 case 异常会整体退出，导致无法稳定完成全量评测。

### 处理

新增 `run_picabench_resumable.py`：

| 能力 | 说明 |
|---|---|
| resume | 跳过已完成 case |
| attempts | 控制每个 case 最大尝试次数 |
| retry-sleep | 控制失败后等待时间 |
| checkpoint summary | 每完成一个 case 立即写 `summary.json` |

## 7. 新 crop 流程 50-case 结果

### 背景

新 crop 流程已完成，并重新跑完 50 个样本。

输出目录：

```text
outputs/picabench_crop_v3_full_20260721/
```

运行设置：

```text
API_TIMEOUT_SECONDS=90
MAX_AGENT_RETRIES=0
attempts=1，失败样本后续 resume 补跑 attempts=2
```

### 结果

| 指标 | 数值 |
|---|---:|
| records | 50 |
| evaluated | 50 |
| failed | 0 |
| accepted | 48 |
| QA accuracy | 92.70% |
| non-edit PSNR | 22.3037 |

完整结果见 [`picabench_full_run_results.md`](picabench_full_run_results.md)。

### 注意

新流程的 PSNR 与旧流程不可直接比较，因为旧流程存在尺寸和坐标映射问题。当前结果只应作为 crop 修正后的主结果。

## 8. `0816` QA 语义歧义

### 背景

`picabench_0816_light_propagation` 要求将郁金香上移，并重投影墙上的影子。该 case 的部分 QA 参考答案如下：

| QA | Reference |
|---|---|
| Do the tulip's cast shadow edges have distinct boundaries? | No |
| Is the tulip's cast shadow located in the upper third of the wall? | No |
| Is the tulip's cast shadow identical in shape to the tulip's silhouette? | No |

### 观察

这些参考答案和 prompt/直觉存在张力：

| QA | 疑点 |
|---|---|
| shadow edges distinct | prompt 要求 shadow sharp and complete，但 reference 是 No |
| shadow in upper third | 可能指完整影子不全在上三分之一，但问题措辞不清 |
| identical silhouette | 物理上 No 合理，但和 prompt 的 shape matches 容易混淆 |

### 影响

该 case 应标记为 benchmark ambiguity。它仍可用于人工观察主体移动和阴影重投影，但不适合单独作为自动分数结论。

## 9. 5-case 人工检查暴露的 PhysicalIntent 问题

### 背景

刚完成 5 个代表性样例的人工检查，对比了 `superficial baseline`、`PhysicalIntentExpander` 和 `explicit prompt` 三条路径。

| Case | 主要观察 |
|---|---|
| `0358` | `superficial` 对碰倒杯子后的液体边界更自然；`PhysicalIntentExpander` 最差，杯把倒影/反射关系错误；`explicit` 中等，液体边界过于规则 |
| `0000` | `superficial` 和 `PhysicalIntentExpander` 主要只删除 5 of spades，没有预测玻璃桌面和剩余纸牌的重力后果；`explicit` 虽然让黑桃 5 错误出现在桌面上，但至少尝试表现玻璃倾斜和结构坍塌 |
| `0294` | `superficial` 和 `PhysicalIntentExpander` 都没有让摩托车在移除脚撑后倒下；`explicit` 对最终倒伏状态更准确 |
| `0148` | `PhysicalIntentExpander` 完全删除左侧自行车及其阴影；`superficial` 和 `explicit` 仍残留轮子阴影 |
| `0816` | `explicit` 对郁金香上移和影子位置较准确；`superficial` 不够靠左；`PhysicalIntentExpander` 让下半部分郁金香消失 |

### 结论

当前 `PhysicalIntentExpander` 的主要缺陷不是“物理词汇不够多”，而是对干预后的下一个稳定状态预测不足。具体表现为：

1. 在 `Causality + remove` 中，容易只执行局部删除，没有从“支撑/约束被移除”推出受影响物体的新姿态、接触点和阴影。
2. 在 `move + Light_Propagation` 中，容易把目标移动、旧影清理、新影重投影混成一次自由编辑，导致目标主体丢失或位置偏移。
3. 在依赖关系复杂时，扩写后的 prompt 可能比短 prompt 更容易诱导模型改坏局部结构，例如错误反射、过规则液体边界或主体残缺。

### 对开发计划的影响

这条观察已同步到 [`development_plan.md`](development_plan.md) 的 P0：后续优先补强 `StableStatePredictor`，并把 `explicit_prompt` 作为弱监督来源抽取终态约束结构，而不是直接学习长文本。

## 10. StableStatePredictor 规则版落地

### 背景

根据 5-case 人工检查，下一步优先把 `PhysicalIntentExpander` 从“泛化扩写”推进到“显式预测最终稳定状态”。

### 处理

已在 `src/physical_agent/physical_intent.py` 中新增规则版 `StableStatePredictor`，并接入 `TaskProfileValidator.normalize_profile()` 的最终校验前流程。当前覆盖：

| 场景 | 补强内容 |
|---|---|
| `Causality + remove + kickstand` | 补出摩托车倒伏、侧面接触地面、旧脚撑痕迹消失、连续接触阴影 |
| `Causality + remove + card structure` | 补出玻璃桌面/纸牌结构重新稳定、支撑区域空缺、倒落纸牌或新接触关系 |
| `Causality + topple + cup/coffee` | 补出杯子侧倒、咖啡静态铺展、杯口到液体的连续连接、自然液体边界 |
| `Light_Propagation + move/remove` | 补出主体完整性、旧影删除、新影/接收面/光照一致性 |

同时更新短 prompt 标签推断：`kickstand`、`card structure`、`knock over/spill` 会进入 causality/topple 路径。

### 验证

新增 `tests/test_physical_intent.py`，覆盖短 prompt 标签推断和三个关键稳定态补全路径。当前结果：

```text
python -m pytest tests\test_physical_intent.py
5 passed
```

`python -m compileall -q src scripts tests` 因 `__pycache__` 写权限被拒绝失败；已用 `python -B` 完成无字节码导入检查。

## 11. 358/000/294 长 prompt 复查结论

### 背景

使用修复后的 PhysicalIntent 长 prompt 重新生成并替换了 `0000` 和 `0294`，保留 `0358` 的新 PhysicalIntent 输出。随后进行人工审查。

### 观察

| Case | 人工审查结论 |
|---|---|
| `0358` | 杯子倒影/反射关系问题已解决；液体边界仍稍显僵硬 |
| `0000` | 玻璃桌面仍然没有明显变化，剩余纸牌也没有倾斜，说明长 prompt 仍未让 executor 执行结构重排 |
| `0294` | 摩托车脚撑删除后的倒伏/物理后果表现很好 |

### 结论

`PhysicalIntent` 对局部物理后果和明确支撑移除任务已经有收益，但 `0000` 暴露出仅靠长 prompt 仍不足以驱动复杂多物体结构重排。下一步应继续小幅优化 PhysicalIntent 的可执行约束，同时启动 `causal_settle_route` 的 router/executor 原型，而不是只在 prompt 层继续加长描述。

## 12. 0000 prompt 记录复查

### 发现

复查 `outputs/prompt_ablation/run_20260724_162814/report.md` 后确认，`0000` 的历史 prompt 记录中虽然存在 `Final stable state` 字段，但内容仍偏抽象：

```text
glass tabletop and nearby unsupported cards settle into a new stable configuration after the support card is removed
```

这没有明确指定玻璃桌面应向前左角下沉/倾斜、附近非黑桃 5 纸牌应倒落或重新接触地面，也没有把剩余纸牌不能全部保持竖直这一检查项写进最终状态。因此该记录不能视为已经充分表达了用户期望的“对应最终状态”。

### 已修正

已在 `StableStatePredictor` 的 card-structure 分支中加强 `0000` 类任务的规则补全。后续生成的 PhysicalIntent prompt 会显式包含：

- 玻璃桌面在前左支撑牌移除后向前左角旋转并下沉。
- 前左支撑位置保留可见空缺，玻璃不再保持原水平姿态。
- 至少一张附近非黑桃 5 纸牌进入倒落、平躺或重新接地的稳定终态。
- 接触阴影、玻璃反射和相邻纸牌姿态必须匹配新的倾斜结构。

保留旧 run 的 `report.md` 和 `prompt_record.json` 作为历史 API 输入记录，不回写成新 prompt，以避免混淆“实际用于该图片生成的 prompt”和“当前代码会生成的 prompt”。

## 13. 0000 intent-only 长 prompt 优化

### 背景

针对 `0000` 的人工复查结论，先不调用生图 API，只优化 `PhysicalIntent` 组件，使其能够从输入图片和短 prompt：

```text
Remove the 5 of spades card from the structure.
```

生成更可执行的 long prompt。

### 处理

本次优化不是把 `0000` 写成单点 hard-code，而是补强 `Causality + remove + structure/support` 这一类任务：

- VLM system prompt 要求在因果删除任务中先判断被删除物是否是 support、prop、counterweight、container 或 constraint。
- 对结构类删除任务，TaskProfile 必须显式识别 removed support、失去支撑的 load/object、remaining supports、receiving surface 和新 contact/shadow/reflection regions。
- `StableStatePredictor` 会把 remove-only 或 stale-stability 的 VLM 输出修正为 support-removal-and-settle 任务。
- card-structure 的关键 `final_state` 字段会覆盖泛化字段，避免保留 “structure remains visually coherent/stable” 这类没有下游物理后果的描述。
- `PromptRenderer` 会把 `final_state`、`physical_dependencies` 和 `must_pass_checks` 直接写入 long prompt，并渲染成自然语言，而不是 Python/JSON 风格结构。
- PhysicalIntent 的 VLM JSON 输出上限从默认 `900` 提高到 `1800`，减少复杂 TaskProfile 被截断导致坏 JSON 的概率。

### 验证

单元测试：

```text
python -m pytest tests\test_physical_intent.py
7 passed
```

VLM-only prompt comparison：

```text
python -B scripts\compare_physical_intent_prompts.py --case-id picabench_0000_causality --prompt-level superficial --label-mode inferred --output-dir outputs\physical_intent_prompt_compare_000_intent_v5
```

结果文件：

- `outputs/physical_intent_prompt_compare_000_intent_v5/physical_intent_prompt_comparison.md`
- `outputs/physical_intent_prompt_compare_000_intent_v5/physical_intent_prompt_comparison.json`

本次没有调用生图 API。`v5` 中 VLM JSON 正常，`Expansion failures: []`，生成 prompt 明确包含：

- 删除前左垂直的 5-of-spades 支撑牌。
- 玻璃桌面向前左角旋转并下沉，不再保持原水平姿态。
- 前左支撑空缺保留可见 gap。
- 至少一张附近非黑桃 5 纸牌倒落、平躺或重新接地。
- 相邻纸牌需要 lean 或 re-seat，不能全部保持旧的竖直支撑构型。
- 新 contact shadows 和 glass reflections 必须匹配降低后的前左玻璃角。
- 显式禁止旧状态失败，例如玻璃仍保持水平、所有附近纸牌仍保持原构型、5-of-spades 在别处重现。

### 结论

从 intent 组件角度看，`0000` 的短 prompt 已能被扩展为包含明确最终稳定状态、依赖区域和失败禁止项的 long prompt。下一步如果继续验证，应只调用一次生图 API 观察 executor 是否按该 prompt 执行结构重排；如果仍失败，问题更可能在 `causal_settle_route` 或 image executor，而不是 PhysicalIntent 缺少终态描述。

## 14. 0000 最新 PhysicalIntent 单次生图

### 背景

使用 `outputs/physical_intent_prompt_compare_000_intent_v5/physical_intent_prompt_comparison.json` 中的最新 long prompt，单独调用一次 image edit API 验证 executor 响应。不重新调用 PhysicalIntent/VLM，不覆盖既有 gallery。

### 结果

输出目录：

```text
outputs/single_image_edit_000_latest_intent/run_20260724_171605
```

关键文件：

- `candidate_unpadded.png`
- `candidate_padded.png`
- `prompt.txt`
- `prompt_record.json`
- `report.md`

### 人工快速观察

这次输出不再只是局部删除 5-of-spades，而是出现了明显结构重排：玻璃/牌结构有新的倾斜关系，地面上出现倒落纸牌，说明 executor 对 long prompt 中“支撑移除后的稳定态”有响应。残余问题是牌面身份和局部结构仍不够可控，例如倒落牌面不是 prompt 中建议的 clubs/card-back 类型，且周围牌面有较多重绘痕迹。

### 结论

`PhysicalIntent` v5 的长 prompt 对 `0000` 已经能推动 image executor 产生结构性物理后果。下一步优化重点应转向 `causal_settle_route` 的局部控制：限制可改区域、保护非目标牌面身份，并把“玻璃倾斜/倒落牌/支撑空缺”拆成更可执行的区域级编辑约束。

## 15. PhysicalIntent executor prompt 压缩

### 背景

`0000` 的 v5 long prompt 证明补全最终稳定态有效，但 `786` words 不适合作为常规 executor prompt。过长 prompt 会增加文本 token 成本，也更容易引入注意力稀释、局部身份漂移和互相冲突的约束。

### 设计取舍

采用“先详细生成，再确定性压缩”的两层结构：

- 详细 `TaskProfile` 继续由 VLM + rules 生成，用于物理推理、审计、router 和 verifier。
- `detailed_edit_prompt` 保留完整渲染结果，方便 debugging 和人工检查。
- `edit_prompt` 改为压缩后的 executor prompt，只保留 target、physical outcome、dependent regions/effects、preserve scope、must satisfy/failure checks。
- 压缩由 deterministic `PromptCompressor` 完成，不再额外调用 LLM，避免压缩过程引入随机遗漏。

不采用“直接克制生成”的原因是，前期 `0000` 已经暴露 VLM 容易省略最终稳定态。如果在生成阶段就强行短输出，容易重新退化为只删除目标物；先保留结构化 TaskProfile，再按优先级压缩，更适合 agent 组件调试。

### 实现

已在 `src/physical_agent/physical_intent.py` 中新增 `PromptCompressor`：

- 按 physics law 设置预算，`causality` 当前预算为 `420` words。
- 按关键词对依赖、区域和检查项排序，优先保留 support、constraint、stable pose、tilt、fall、grounded、contact、shadow、old-state failure 等信息。
- 不做半句截断；如果超预算，优先减少低优先级完整条目。
- `PhysicalIntentDiagnostics` 新增 `detailed_prompt_length` 和 `prompt_compression_ratio`。

### 验证

单元测试：

```text
python -m pytest tests\test_physical_intent.py
8 passed
```

VLM-only 真实链路：

```text
python -B scripts\compare_physical_intent_prompts.py --case-id picabench_0000_causality --prompt-level superficial --label-mode inferred --output-dir outputs\physical_intent_prompt_compare_000_compressed_v1
```

结果：

- `Expansion failures: []`
- detailed prompt: `766` words
- compressed executor prompt: `420` words
- compression ratio: `0.548`

修正半句截断后，基于同一 TaskProfile 离线重渲染：

- 输出目录：`outputs/physical_intent_prompt_compare_000_compressed_v2_offline`
- detailed prompt: `766` words
- compressed executor prompt: `412` words

压缩版仍保留 000 的关键约束：玻璃前左角下沉、前左支撑 gap、非 5 纸牌倒落/接地、相邻纸牌不能全保持旧构型、新 contact shadows/reflections，以及 old-state failure 禁止项。

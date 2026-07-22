# PICABench 本地样例集说明

本项目使用 `Andrew613/PICABench` 的本地子集作为物理一致性图像编辑评测集。PICABench 的核心目的不是只检查“有没有完成表面编辑指令”，而是检查编辑后图像是否同步满足物理规律，例如删除物体后阴影是否消失、移动物体后投影是否重建、移除支撑物后受影响对象是否进入新的稳定状态。

本地数据源：

```text
Hugging Face dataset: Andrew613/PICABench
local root: data/picabench_examples/
manifest: data/picabench_examples/manifest.json
```

## 数据目录格式

本地目录结构如下：

```text
data/picabench_examples/
  manifest.json
  picabench_XXXX_<physics_law>/
    input.png
    metadata.json
```

`manifest.json` 是批量运行入口，包含所有样本的合并元数据；每个 case 目录下的 `metadata.json` 保存单个样本的完整信息。当前本地子集包含 50 个样本，运行时默认使用 `explicit_prompt` 作为编辑指令。

## 单条样本格式

`manifest.json` 中每个 case 的主要字段如下：

| 字段 | 含义 | 用途 |
|---|---|---|
| `case_id` | 本地样本 ID，例如 `picabench_0000_causality` | 输出目录、日志和结果表索引 |
| `dataset` / `config` / `split` | 原始数据集来源信息 | 追踪样本来源 |
| `row_idx` | 原 PICABench 数据集中的行号 | 复现实验和回查原始样本 |
| `physics_category` | 粗粒度物理类别：`Optics`、`Mechanics`、`State` | 大类统计和 Planner/Router 一级分流 |
| `physics_law` | 具体物理规律标签 | law-specific route、verifier checklist 和结果分析 |
| `edit_operation` | 编辑动作类型 | 判断 add/remove/move/replace/weather 等动作约束 |
| `instruction` | 当前实际运行的编辑指令 | 输入给 agent 的用户指令 |
| `prompt_field` | 当前选用的 prompt 层级 | 本项目固定为 `explicit_prompt` |
| `prompts` | 三层 prompt：`superficial`、`intermediate`、`explicit` | 比较不同提示详细程度 |
| `image_path` | 原始数据集中图像路径 | 数据来源记录 |
| `input_png` | 本地 PNG 输入图路径 | 传给 agent 和评测器 |
| `input_image_size` | 原图宽高 | 坐标映射和恢复原图比例 |
| `edit_area` | 允许/预期发生编辑的区域框 | non-edit PSNR 与局部评估 |
| `annotated_qa_pairs` | 人工标注的 yes/no 问答及对应区域 | PICAEval 逐题评分 |

一个 QA 标注通常包含：

```json
{
  "question": "Is the glass tabletop tilted toward the front-left corner?",
  "answer": "Yes",
  "box": {
    "x": 0.0,
    "y": 0.0,
    "width": 643.18,
    "height": 1018.95
  }
}
```

其中 `question` 是针对最终编辑结果提出的可观察问题，`answer` 是参考答案，只允许 `Yes` 或 `No`，`box` 是该问题关注的图像区域。注意：PICABench 的 QA 主要看最终图像状态，而不是让评测器比较编辑前后过程。

## 三类标签体系

PICABench 中对样本最重要的标签有三类：

| 标签 | 粒度 | 本项目中的作用 |
|---|---|---|
| `physics_category` | 粗粒度物理域 | 区分光学、力学、状态变化，决定总体问题范式 |
| `physics_law` | 中粒度物理机制 | 决定具体 route、依赖区域和 verifier 必检项 |
| `edit_operation` | 编辑动作类型 | 决定主动作、工具顺序、失败模式和 retry 策略 |

三者必须组合使用。比如：

```text
physics_category = Mechanics
physics_law = Causality
edit_operation = remove

=> 不只是 remove_object，而是 remove_support_and_settle：
   删除支撑/约束对象后，还要更新受影响物体姿态、接触点、遮挡和阴影。
```

再比如：

```text
physics_category = Optics
physics_law = Light_Propagation
edit_operation = move

=> 不只是 move_object，而是 move_and_reproject_shadow：
   目标位置改变后，旧阴影要清理，新阴影要按场景光照重新投影。
```

## 物理类别与规律

PICABench 覆盖 3 个物理大类和 8 个物理规律子类：

| Category | Physics law | 中文说明 | 典型检查点 |
|---|---|---|---|
| `Optics` | `Light_Propagation` | 光传播/投影 | cast shadow、contact shadow、方向、软硬、旧阴影残留 |
| `Optics` | `Light_Source_Effects` | 光源效应 | 新光源、照亮区域、色温、二次阴影、反射变化 |
| `Optics` | `Reflection` | 反射 | 镜像/倒影、反射面、水线、高光、尺度和方向 |
| `Optics` | `Refraction` | 折射 | 透明介质后的背景扭曲、边界、高光、caustic |
| `Mechanics` | `Deformation` | 形变 | 受力方向、材料连续性、压痕/拉伸/弯曲是否合理 |
| `Mechanics` | `Causality` | 因果关系 | 支撑、接触、重力、倒伏、稳定状态、连带影响 |
| `State` | `Global` | 全局状态变化 | 天气、季节、昼夜、全局光照和环境一致性 |
| `State` | `Local` | 局部状态变化 | 湿、冻、烧、破裂、材料边界、局部范围控制 |

当前本地 50-case 子集分布：

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

按大类汇总：

| Category | Cases |
|---|---:|
| Optics | 24 |
| Mechanics | 13 |
| State | 13 |

按编辑动作汇总：

| Operation | Cases |
|---|---:|
| `remove` | 18 |
| `others` | 7 |
| `add` | 7 |
| `move` | 5 |
| `weather` | 3 |
| `wet` | 3 |
| `time` | 2 |
| `season` | 2 |
| `replace` | 2 |
| `frozen` | 1 |

## Prompt 层级

PICABench 为每个样本提供三种编辑指令层级：

| Prompt | 含义 | 评测目的 |
|---|---|---|
| `superficial` | 只描述表面编辑动作 | 测试模型是否具有内在物理先验 |
| `intermediate` | 提醒模型需要考虑物理规律，但不写明最终视觉结果 | 测试模型能否把物理提示转成正确后果 |
| `explicit` | 明确描述最终稳定状态和物理视觉后果 | 减少歧义，测试模型是否能执行复杂物理编辑 |

三种 prompt 对应的是同一张图、同一个编辑意图、同一组最终 QA，但给模型的信息量不同。这样可以区分两类能力：模型是否能在短指令下自己推断物理后果，以及模型在后果被明确写出后是否能忠实执行并保持非编辑区域。

论文/项目中用于报告不同模型主结果的默认口径是 `superficial_prompt`，也就是很短的表面编辑指令；`intermediate_prompt` 和 `explicit_prompt` 主要用于分析 prompt 详细程度对结果的影响。因此，如果要和 PICABench 官方模型结果或排行榜做公平比较，应使用 `superficial_prompt`。

本项目当前统一使用 `explicit_prompt`，原因是项目目标是先验证 agent 闭环、坐标评测和物理依赖检查，而不是比较不同 prompt 难度。后续做消融实验时，可以比较：

```text
superficial prompt
intermediate prompt
explicit prompt
agent planner rewritten prompt
route-specific prompt
```

字段位置：

| 位置 | 字段 | 含义 |
|---|---|---|
| Hugging Face 原始数据集 | `superficial_prompt` | 官方默认主评测口径使用的短 prompt |
| Hugging Face 原始数据集 | `intermediate_prompt` | 中等详细程度 prompt |
| Hugging Face 原始数据集 | `explicit_prompt` | 详细 prompt |
| 本地 `manifest.json` / `metadata.json` | `instruction` | 当前实际送入 agent 的编辑指令 |
| 本地 `manifest.json` / `metadata.json` | `prompt_field` | `instruction` 取自哪一种 prompt |
| 本地 `manifest.json` / `metadata.json` | `prompts.superficial` / `prompts.intermediate` / `prompts.explicit` | 三种 prompt 的本地备份 |

当前 50-case 本地子集由 `scripts/download_picabench_examples.py` 下载，脚本参数 `--prompt-field` 默认值是 `explicit_prompt`。因此本项目 2026-07-21 的新 crop 结果属于“详细 prompt 下的内部迭代结果”，不能直接当作 PICABench 官方短 prompt 口径的模型对比结果。

## PICAEval 评测方式

PICABench 论文提出的 PICAEval 是 region-grounded VQA 评测协议。本项目复用了这一思想，并根据闭源编辑 API 的固定输出尺寸问题做了坐标修正。

本项目当前评测流程：

```text
input.png
  -> canonical_input.png: contain 到 1024x1024 并保存 coordinate_transform
  -> image edit API 输出 padded candidate
  -> 去 padding，恢复到原图尺寸 final_image_unpadded.png
  -> 对 annotated_qa_pairs 做 yes/no QA
  -> 计算 non-edit-region PSNR
```

当前记录的两个核心指标：

| 字段 | 含义 |
|---|---|
| `pica_accuracy` | PICAEval QA 正确率，即 VLM 对 annotated yes/no 问题的回答与参考答案一致的比例 |
| `pica_consistency_psnr` | 非编辑区域 PSNR，在 `edit_area` 外比较原图和结果图，越高表示非编辑区域保留越好 |

本项目还按问题类型选择评估视图：

| question_type | evaluation_view | 原因 |
|---|---|---|
| `global_position` | full image | 左右、上下、前后、角落等关系需要完整画布 |
| `local_appearance` | crop | 阴影、反射、材质、接触等局部物理细节需要放大 |
| `mixed` | full image + crop | 同时包含全局位置和局部物理证据 |
| `unknown` | crop + `context_risk` | 无法稳定分类时标记风险 |

## 论文中其他模型的 PICABench 结果

PICABench 论文在 `PICABench-Superficial` 设置下，用 GPT-5 作为 VLM evaluator，对 13 个开闭源图像编辑模型进行了量化比较。论文同时报告 `Acc` 与 `Con`：`Acc` 是 QA accuracy，`Con` 是非编辑区域 consistency/PSNR。下表只摘录 Overall，便于和本项目结果放在同一页理解。

| Model | Overall Acc (%) | Overall Con (dB) |
|---|---:|---:|
| GPT-Image-1.5 | 67.05 | 21.73 |
| Nano Banana Pro | 66.16 | 22.97 |
| Seedream 4.0 | 61.91 | 23.26 |
| GPT-Image-1 | 61.08 | 15.48 |
| Nano Banana | 59.87 | 23.47 |
| Qwen-Image-Edit | 58.29 | 19.43 |
| Flux.1 Kontext + SFT | 50.64 | 25.23 |
| Flux.1 Kontext | 48.93 | 24.57 |
| Step1X-Edit | 48.23 | 24.68 |
| HiDream-E1.1 | 47.90 | 18.91 |
| OmniGen2 | 46.79 | 24.12 |
| Bagel-Think | 46.48 | 26.88 |
| Bagel | 45.07 | 28.42 |
| UniWorld-V1 | 37.68 | 18.48 |
| DiMOO | 35.66 | 23.70 |

论文还报告了 prompt 详细程度对部分模型的影响：

| Model / Prompt | Overall Acc (%) | Overall Con (dB) |
|---|---:|---:|
| Bagel - superficial | 45.07 | 28.42 |
| Bagel - intermediate | 54.06 | 21.14 |
| Bagel - explicit | 65.61 | 15.20 |
| Flux.1 Kontext - superficial | 48.93 | 24.57 |
| Flux.1 Kontext - intermediate | 53.77 | 23.42 |
| Flux.1 Kontext - explicit | 63.30 | 21.54 |
| Qwen-Image-Edit - superficial | 58.29 | 19.43 |
| Qwen-Image-Edit - intermediate | 60.41 | 20.14 |
| Qwen-Image-Edit - explicit | 68.02 | 17.96 |

这个表说明：更详细的 prompt 通常能提高物理 QA accuracy，但也可能降低非编辑区域 consistency，因为模型为了满足复杂物理后果会改动更多图像区域。

## 本项目 50-case 子集结果

本项目当前结果来自：

```text
outputs/picabench_crop_v3_full_20260721/
docs/picabench_full_run_results.md
```

运行设置与论文原始 benchmark 不完全一致：本项目只使用 50-case 子集、使用 `explicit_prompt`、调用 `gpt-image-2` 作为编辑 executor，并带有 agent planner/verifier 与本地 canonical crop 流程。因此数值不能直接等同于论文完整 PICABench 排行，只能作为本项目内部迭代基线。

总体结果：

| 指标 | 数值 |
|---|---:|
| Cases | 50 |
| QA answer accuracy | 92.70% |
| Non-edit-region PSNR | 22.3037 |
| Agent accepted | 48 |

按 physics law 汇总：

| Physics law | 中文 | Category | Cases | QA accuracy | Non-edit PSNR |
|---|---|---|---:|---:|---:|
| Causality | 因果关系 | Mechanics | 7 | 95.10% | 25.4965 |
| Deformation | 形变 | Mechanics | 6 | 85.00% | 21.0145 |
| Global | 全局状态 | State | 7 | 95.24% | 9.5194 |
| Light_Propagation | 光传播 | Optics | 6 | 89.29% | 25.9282 |
| Light_Source_Effects | 光源效应 | Optics | 6 | 90.28% | 21.4594 |
| Local | 局部状态 | State | 6 | 95.83% | 26.4459 |
| Reflection | 反射 | Optics | 6 | 100.00% | 23.7342 |
| Refraction | 折射 | Optics | 6 | 90.00% | 22.1689 |

需要注意：当前本项目结果使用的是较详细的 `explicit_prompt` 和 50-case 子集，因此 QA accuracy 明显高于论文中 full benchmark 的 superficial prompt 结果并不意外。后续若要公平对比，需要固定同一数据规模、同一 prompt 层级、同一 evaluator、同一 crop 协议。

## 当前子集的用途

本地 50-case PICABench 子集主要用于：

1. 验证 agent 闭环是否可运行。
2. 检查图像尺寸、padding、crop 映射和 PSNR 是否稳定。
3. 作为 regression set 追踪 Planner、Router、Executor、Verifier 的改动效果。
4. 定点分析低分物理类型，例如 Light_Propagation、Causality、Deformation、Refraction。
5. 为后续 route-specific planner/verifier 和局部工具链提供可复现测试样本。

当前不应把该子集视为完整 benchmark 排行榜；它更适合作为项目开发过程中的受控验证集。

## 常用命令

查看选中的 case，不调用模型 API：

```powershell
python scripts\run_picabench_examples.py --dry-run
```

运行单个 case：

```powershell
python scripts\run_picabench_examples.py --case-id picabench_0000_causality
```

运行小批量：

```powershell
python scripts\run_picabench_examples.py --limit 3
```

跳过 PICAEval，只运行 agent 编辑闭环：

```powershell
python scripts\run_picabench_examples.py --limit 3 --skip-pica-eval
```

可恢复批量运行：

```powershell
python scripts\run_picabench_resumable.py --resume --attempts 3 --retry-sleep 30
```

查看结果：

```powershell
python scripts\view_picabench_results.py --summary outputs\picabench_crop_v3_full_20260721\summary.json --port 7861
```

输出位置：

```text
outputs/<run_name>/<case_id>/
  canonical_input.png
  coordinate_transform.json
  run_YYYYMMDD_HHMMSS/
    step_00/
      plan.json
      candidate.png
      verify.json
    final_image_unpadded.png
    pica_eval/
      pica_eval.json
      qa_region_XX.png
```

## 与后续开发的关系

PICABench 的三类标签和 QA 标注不应只作为结果统计字段。后续更重要的是把它们接入 agent 决策：

| 模块 | 应如何使用 PICABench 信息 |
|---|---|
| Planner | 用 `physics_category`、`physics_law`、`edit_operation` 生成规则骨架和 must-pass checks |
| Router | 将 law/operation 映射成 `reflection_route`、`shadow_projection_route`、`causal_settle_route` 等 |
| Executor | 根据 route 决定 whole-image、local edit、two-pass 或 best-of-N |
| Verifier | 把 annotated QA 和 law-specific checklist 合并成 blocking gate |
| Retry | 将 QA 失败和 blocking failures 转成结构化 route hints |

因此，PICABench 在本项目中既是评测集，也是推动 agent 结构化规划、路由和验证的任务规格来源。

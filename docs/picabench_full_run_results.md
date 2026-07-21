# PICABench 50-case Run Results

运行目录：`outputs/picabench_full_20260721_resumable/`

本报告按 PICABench 的 `physics_law` 任务类型分组。

## 总体结果

| 指标 | 数值 |
| --- | ---: |
| Cases | 50 | 
| QA answer accuracy | 91.43% | 
| Non-edit-region PSNR | 15.3221 | 

## 按任务类型汇总

| Physics law | Category | Cases | QA accuracy | Non-edit PSNR |
| --- | --- | ---: | ---: | ---: |
| Causality | Mechanics | 7 | 89.39% | 14.6507 |
| Deformation | Mechanics | 6 | 93.33% | 17.3246 |
| Global | State | 7 | 95.24% | 9.5839 |
| Light_Propagation | Optics | 6 | 83.73% | 17.5091 |
| Light_Source_Effects | Optics | 6 | 94.44% | 17.3379 |
| Local | State | 6 | 95.83% | 15.4393 |
| Reflection | Optics | 6 | 79.17% | 14.0420 |
| Refraction | Optics | 6 | 100.0% | 15.8447 |

## 因果关系（Causality）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: |
| `picabench_0000_causality` | Mechanics | remove | Yes | 4/4 | 100.0% | 15.4353 | 2 |
| `picabench_0173_causality` | Mechanics | remove | Yes | 4/5 | 80.0% | 15.7226 | 1 |
| `picabench_0294_causality` | Mechanics | remove | Yes | 3/5 | 60.0% | 11.407 | 1 |
| `picabench_0358_causality` | Mechanics | others | Yes | 6/7 | 85.71% | 21.4233 | 2 |
| `picabench_0589_causality` | Mechanics | others | Yes | 5/5 | 100.0% | 15.438 | 1 |
| `picabench_0733_causality` | Mechanics | others | Yes | 3/3 | 100.0% | 11.5214 | 2 |
| `picabench_0850_causality` | Mechanics | remove | Yes | 3/3 | 100.0% | 11.6076 | 2 |

## 形变（Deformation）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: |
| `picabench_0049_deformation` | Mechanics | others | No | 4/5 | 80.0% | 23.1645 | 1 |
| `picabench_0226_deformation` | Mechanics | add | Yes | 4/4 | 100.0% | 16.4048 | 1 |
| `picabench_0505_deformation` | Mechanics | remove | Yes | 6/6 | 100.0% | 15.6291 | 1 |
| `picabench_0610_deformation` | Mechanics | move | Yes | 5/5 | 100.0% | 17.9538 | 2 |
| `picabench_0700_deformation` | Mechanics | others | No | 4/5 | 80.0% | 15.3216 | 1 |
| `picabench_0821_deformation` | Mechanics | remove | Yes | 3/3 | 100.0% | 15.4739 | 1 |

## 全局状态（Global）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: |
| `picabench_0020_global` | State | time | Yes | 3/3 | 100.0% | 10.4862 | 1 |
| `picabench_0100_global` | State | weather | Yes | 6/6 | 100.0% | 9.436 | 1 |
| `picabench_0164_global` | State | season | Yes | 3/3 | 100.0% | 12.1076 | 2 |
| `picabench_0300_global` | State | weather | Yes | 3/3 | 100.0% | 9.2015 | 2 |
| `picabench_0460_global` | State | time | Yes | 2/3 | 66.67% | - | 1 |
| `picabench_0658_global` | State | weather | Yes | 3/3 | 100.0% | - | 2 |
| `picabench_0744_global` | State | season | Yes | 5/5 | 100.0% | 6.6882 | 1 |

## 光传播（Light_Propagation）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: |
| `picabench_0004_light_propagation` | Optics | remove | Yes | 4/4 | 100.0% | 28.0118 | 1 |
| `picabench_0032_light_propagation` | Optics | remove | Yes | 6/7 | 85.71% | 17.8853 | 1 |
| `picabench_0148_light_propagation` | Optics | remove | Yes | 4/4 | 100.0% | 8.8662 | 1 |
| `picabench_0335_light_propagation` | Optics | move | Yes | 2/3 | 66.67% | 14.6855 | 1 |
| `picabench_0561_light_propagation` | Optics | remove | Yes | 6/6 | 100.0% | 11.7968 | 3 |
| `picabench_0816_light_propagation` | Optics | move | Yes | 3/6 | 50.0% | 23.8087 | 1 |

## 光源效应（Light_Source_Effects）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: |
| `picabench_0039_light_source_effects` | Optics | add | Yes | 2/3 | 66.67% | 33.0345 | 3 |
| `picabench_0117_light_source_effects` | Optics | replace | Yes | 4/4 | 100.0% | 20.732 | 1 |
| `picabench_0261_light_source_effects` | Optics | add | Yes | 5/5 | 100.0% | 10.7706 | 1 |
| `picabench_0380_light_source_effects` | Optics | add | Yes | 3/3 | 100.0% | 13.387 | 1 |
| `picabench_0500_light_source_effects` | Optics | add | Yes | 3/3 | 100.0% | 14.7001 | 1 |
| `picabench_0766_light_source_effects` | Optics | add | Yes | 4/4 | 100.0% | 11.403 | 1 |

## 局部状态（Local）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: |
| `picabench_0064_local` | State | others | Yes | 3/3 | 100.0% | 12.0807 | 1 |
| `picabench_0176_local` | State | others | No | 3/4 | 75.00% | 24.5261 | 1 |
| `picabench_0402_local` | State | wet | Yes | 6/6 | 100.0% | 13.4334 | 3 |
| `picabench_0542_local` | State | wet | Yes | 3/3 | 100.0% | 16.5706 | 2 |
| `picabench_0686_local` | State | wet | Yes | 5/5 | 100.0% | 12.9941 | 1 |
| `picabench_0801_local` | State | frozen | Yes | 7/7 | 100.0% | 13.0311 | 2 |

## 反射（Reflection）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: |
| `picabench_0007_reflection` | Optics | remove | Yes | 4/4 | 100.0% | 10.5502 | 1 |
| `picabench_0081_reflection` | Optics | replace | Yes | 5/5 | 100.0% | 11.9636 | 1 |
| `picabench_0280_reflection` | Optics | move | No | 6/8 | 75.00% | 16.5664 | 2 |
| `picabench_0387_reflection` | Optics | add | Yes | 0/3 | 0.0% | 13.5611 | 1 |
| `picabench_0562_reflection` | Optics | remove | Yes | 4/4 | 100.0% | 14.4392 | 1 |
| `picabench_0799_reflection` | Optics | move | Yes | 7/7 | 100.0% | 17.1716 | 1 |

## 折射（Refraction）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: |
| `picabench_0001_refraction` | Optics | remove | Yes | 5/5 | 100.0% | 28.7574 | 1 |
| `picabench_0017_refraction` | Optics | remove | Yes | 5/5 | 100.0% | 16.4153 | 1 |
| `picabench_0036_refraction` | Optics | remove | Yes | 3/3 | 100.0% | 20.2634 | 1 |
| `picabench_0059_refraction` | Optics | remove | Yes | 3/3 | 100.0% | 5.32 | 1 |
| `picabench_0139_refraction` | Optics | remove | Yes | 3/3 | 100.0% | 17.1978 | 1 |
| `picabench_0269_refraction` | Optics | remove | Yes | 5/5 | 100.0% | 7.1143 | 1 |

## 指标定义

- `QA accuracy`: PICABench annotated yes/no questions answered correctly by the evaluator.
- `Non-edit-region PSNR`: source/candidate PSNR outside the annotated edit area; higher values indicate stronger preservation of non-edited content.
- `Accepted`: whether the agent verifier accepted the final candidate.

## 优化优先级分析

从 50-case full run 的数据看，当前最需要优化的类型不是整体状态转移，而是光学类中的反射和光传播。

| 优先级 | Physics law | QA accuracy | 主要证据 | 当前问题判断 |
| ---: | --- | ---: | --- | --- |
| 1 | Reflection | 79.17% | 全部 law 中最低；`picabench_0387_reflection` 为 0/3，`picabench_0280_reflection` 为 6/8 | 反射依赖没有被稳定执行；目标位置、镜像尺度、水面接触和背景反射遮挡需要专门 route |
| 2 | Light_Propagation | 83.73% | 第二低；`picabench_0816_light_propagation` 为 3/6，`picabench_0335_light_propagation` 为 2/3 | 阴影几何和软硬控制不足；移动物体后 shadow projection 没有按光源重新约束 |
| 3 | Causality | 89.39% | `picabench_0294_causality` 为 3/5，且 agent verifier 误判为 pass | 支撑移除后的最终稳定态没有强制执行；接触阴影和倒伏姿态需要显式力学 route |

其他类型暂时不是第一优化对象：`Refraction` 达到 100%，`Local` 和 `Global` 均在 95% 左右，`Light_Source_Effects` 和 `Deformation` 也超过 93%。不过 `Global` 的 non-edit PSNR 只有 9.5839，这说明全局状态任务虽然 QA 高，但会天然大范围改图，不能用低 PSNR 直接判为失败。

### 失败样本揭示的问题

最低分样本集中暴露了三类缺口。

| Case | Law | Agent accepted | PICAEval | 失败现象 | 说明 |
| --- | --- | :---: | ---: | --- | --- |
| `picabench_0387_reflection` | Reflection | Yes | 0/3 | QA 认为船没有出现在评测区域，反射和微波纹也无法判断 | 当前 `direct_edit` 对 add-object 的空间落点不稳定；verifier 没有严格检查“目标是否在指定区域可见” |
| `picabench_0816_light_propagation` | Light_Propagation | Yes | 3/6 | tulip 阴影过清晰、位置过高、形状过像实体轮廓 | planner 把 shadow 写成 sharp and complete，和目标 QA 所需的 softer projection 相冲突 |
| `picabench_0335_light_propagation` | Light_Propagation | Yes | 2/3 | 杯子的投影不可见，无法判断是否与 laptop 阴影同向 | 移动物体 route 没有强制保留/重投影 cast shadow |
| `picabench_0294_causality` | Causality | Yes | 3/5 | kickstand 被删了，但摩托车仍被判为直立，没有左侧连续接触阴影 | verifier 与 PICAEval 明显不一致；力学最终稳定态没有被硬约束 |
| `picabench_0280_reflection` | Reflection | No | 6/8 | 船屋反射缺失，船到码头距离不满足几何约束 | verifier 能识别部分问题，但当前 route 缺少几何定位和反射同步工具 |

一个关键结论是：低分并不总是 planner 没写到。`picabench_0387_reflection` 的 plan 已经写了中心放船、反射尺度、倒影位置和微波纹，但最终 PICAEval 为 0/3，且 verifier 仍通过。这说明当前最大的系统缺口是 route 和 verifier 没有把 plan 中的物理依赖变成可验证、可定位的执行约束。

## 对应需要提升的 Plan 与 Route

### 1. Reflection：最高优先级

Reflection 是最需要优化的类型。它的失败不是简单的“忘记写反射”，而是对象、反射、水面/镜面接触和场景透视之间没有绑定。

需要提升的 plan：

| Plan 字段 | 当前不足 | 建议增强 |
| --- | --- | --- |
| `target` | 常写成泛泛的 `image` | 改为结构化目标：主体、反射面、反射区域、接触线 |
| `physics_dependencies` | 只有 `reflection, perspective, lighting, contact` 这类关键词 | 显式列出：主体 bbox、反射 bbox、反射轴/水线、尺度关系、亮度/饱和度差异、表面扰动 |
| `edit_prompt` | 描述完整，但缺少可执行区域约束 | 增加“目标必须位于 annotated/edit region 或指定画面坐标附近”的约束 |
| `verifier_focus` | 太笼统 | 拆成 checklist：目标可见、反射可见、反射直接位于主体下方/镜面对称、尺度一致、接触线存在、背景反射被正确遮挡 |

需要提升的 route：

```text
reflection_add_or_move_route
  -> locate reflective surface / waterline
  -> local edit object into target region
  -> generate paired reflection in reflected region
  -> add contact band / ripple / specular adjustment
  -> run reflection-specific verifier
```

如果暂时不接入分割和几何工具，也应至少把 route 从通用 `direct_edit` 区分为 `reflection_direct_edit`，使用更强的结构化 prompt 和 reflection QA checklist。对于 add/move 反射任务，应该优先考虑局部编辑或两阶段编辑：先保证主体位置正确，再补反射和水面接触。

### 2. Light_Propagation：第二优先级

Light_Propagation 的主要问题是移动或删除物体后，阴影没有按光源重新投影，或者 prompt 错误地要求过硬、过完整的阴影。

需要提升的 plan：

| Plan 字段 | 当前不足 | 建议增强 |
| --- | --- | --- |
| `physics_dependencies` | 泛化为 `shadows, lighting, perspective` | 显式估计主光源方向、参考物阴影方向、目标阴影终点、阴影软硬、遮挡关系 |
| `edit_prompt` | 容易写出与评测目标冲突的 shadow 描述 | 对 shadow 使用相对约束：与参考物同方向、同软硬趋势、随距离变软/变淡 |
| `preserve` | 常只保留背景和光照 | 加入“保留参考阴影作为方向/软硬标尺” |
| `verifier_focus` | 只写 shadow accuracy | 拆成方向、位置、长度、软硬、可见性、是否残留旧阴影 |

需要提升的 route：

```text
shadow_projection_route
  -> identify dominant light direction from existing shadows
  -> select nearby reference shadows
  -> edit/move target object
  -> reproject cast shadow and contact shadow
  -> verify against reference shadow orientation and softness
```

这里最重要的是避免 planner 直接臆造“sharp and complete”。例如 `picabench_0816_light_propagation` 中，PICAEval 期望阴影边缘不应过清晰，也不应与 tulip 轮廓完全相同；因此 plan 应把阴影作为光源、距离和投射面共同决定的结果，而不是物体 silhouette 的硬拷贝。

### 3. Causality：第三优先级

Causality 的平均分高于前两类，但失败样本很有代表性：删除支撑后只完成了局部擦除，没有强制生成力学后的最终稳定状态。

需要提升的 plan：

| Plan 字段 | 当前不足 | 建议增强 |
| --- | --- | --- |
| `operation` | `remove` 容易被图像模型理解为只删除物体 | 改写为 `remove_support_and_settle`、`remove_contact_and_repose` 这类因果操作 |
| `physics_dependencies` | 列出 gravity/contact，但没有状态转移约束 | 明确 before/after 支撑关系、重心变化、最终接触面、连续接触阴影 |
| `edit_prompt` | 有时没有把“最终稳定态”作为硬条件 | 加入“not merely remove; object must be in final gravity-settled pose” |
| `verifier_focus` | 对目标删除检查强，对后果检查弱 | 把支撑移除后果作为 pass 必要条件：倒伏/下落/倾斜/新接触点必须成立 |

需要提升的 route：

```text
causal_settle_route
  -> detect support/contact relation
  -> infer stable final state after support removal
  -> edit object pose and support artifact together
  -> add contact shadow / occlusion / ground deformation if needed
  -> reject if only support is removed but dependent object remains unchanged
```

`picabench_0294_causality` 是典型例子：如果删除摩托车 kickstand，route 不能只执行 object removal，而应把“摩托车倒向左侧并形成连续接触阴影”作为必要编辑结果。

## 推荐的短期改进顺序

1. 先改 verifier：加入 law-specific checklist，尤其是 Reflection 和 Light_Propagation。这样可以减少“agent accepted 但 PICAEval 低分”的问题。
2. 再改 planner schema：把 `physics_dependencies` 从字符串改成结构化字段，例如 `objects_to_edit`、`dependent_regions`、`reference_cues`、`must_pass_checks`。
3. 最后改 route：先实现 rule-based routing，不必一开始接完整 CV 工具链。至少区分 `reflection_route`、`shadow_projection_route`、`causal_settle_route` 和通用 `direct_edit`。
4. 对 Reflection add/move 与 Light_Propagation move 使用更高重试预算，因为它们是当前数据中最容易掉分的操作组合。

最值得汇报的结论是：当前 91.43% 的总体 QA accuracy 说明 MVP 闭环有效，但类型级结果表明通用 `direct_edit` 已经到达瓶颈。下一步的主要增益点不是继续堆 prompt，而是把 PICABench 的 physics law 转化为 route-specific planning 和 route-specific verification。


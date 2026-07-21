# Physical Image Editing Agent 进展汇报

## 条目 1：项目当前评测背景

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

本地评测集使用 `Andrew613/PICABench` 的 50 个样本，覆盖 8 个 physics law，使用 `explicit_prompt`。

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

### 问题

当前版本主要验证闭环流程，不代表完整工具路由能力。Router 还没有真正接入 detection、segmentation、mask edit 或 local repaint。

### 解决

后续将 8 个 physics law 映射成 rule-based route 和 law-specific verifier checklist。

---

## 条目 2：输出尺寸固定导致 box 错位

### 背景

PICABench 的 `box` 和 `edit_area` 基于原图坐标，但图像编辑 API 倾向输出固定 `1024x1024`。

### 问题

如果直接用原始 box 或简单宽高缩放，会导致 QA crop 和 non-edit PSNR 的区域错位。

### 解决

当前采用 canonical canvas：

```text
原图
  -> contain 到 1024x1024
  -> 保存 coordinate_transform
  -> 调用 image edit API
  -> source box -> canonical box -> output box
```

后续需要补充坐标映射单元测试。

---

## 条目 3：padding 黑边影响结果展示与评测

### 背景

为保持原图比例，非正方形图片会被 contain 到 `1024x1024`，因此出现上下或左右 padding 黑边。

### 问题

黑边可能被模型或 verifier 当作真实图像内容；同时展示时也不符合原始数据集画幅。

### 解决

当前同时保留两种输出：

| 输出 | 用途 |
|---|---|
| padded candidate | 保留 API 原始 `1024x1024` 结果，便于审计 |
| unpadded final image | 去掉 padding，并恢复到原图尺寸，用于主展示和 PICABench 评分 |

Gradio 页面同时展示两者。

---

## 条目 4：局部 crop 丢失全局语境

### 背景

PICABench QA 有些问题询问全局位置，例如 upper/lower/left/right/corner/center。

### 问题

如果只给局部 crop，目标会出现在裁剪图中央，VLM 会基于局部画布回答，而不是完整图片位置。

### 解决

当前按问题类型选择评测视图：

| question_type | evaluation_view |
|---|---|
| global_position | full_image |
| local_appearance | crop |
| mixed | full_image + crop |
| unknown | crop，并标记 context_risk |

后续继续改进问题分类规则。

---

## 条目 5：QA 批量回答缺项

### 背景

为减少单图耗时，当前按 evaluation_view 将多个 QA 合并成批量 VLM 请求。

### 问题

VLM 有时不会返回所有 question index，导致某些 `predicted_answer` 为空。

### 解决

已加入 fallback：批量响应缺失某题答案时，对该题单独补问。

后续记录 fallback 次数，用于判断评测稳定性。

---

## 条目 6：API 不稳定导致批跑中断

### 背景

批量运行 50 个 PICABench case 时，外部 API 会出现 timeout、429 cooldown、DeploymentNotFound 等问题。

### 问题

普通批跑脚本遇到单个 case 异常会整体退出，导致无法稳定完成全量评测。

### 解决

新增 `run_picabench_resumable.py`：

| 能力 | 说明 |
|---|---|
| resume | 跳过已完成 case |
| attempts | 控制每个 case 最大尝试次数 |
| retry-sleep | 控制失败后等待时间 |
| checkpoint summary | 每完成一个 case 立即写 `summary.json` |

---

## 条目 7：新 crop 流程 50 case 结果

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

### 问题

新流程的 PSNR 与旧流程不可直接比较，因为旧流程存在尺寸和坐标映射问题。

### 解决

当前只将新结果作为 crop 修正后的主结果：

| 指标 | 数值 |
|---|---:|
| records | 50 |
| evaluated | 50 |
| failed | 0 |
| accepted | 48 |
| QA accuracy | 92.70% |
| non-edit PSNR | 22.3037 |

Gradio 展示入口：

```text
http://127.0.0.1:7861
```

---

## 条目 8：0816 QA 语义歧义

### 背景

`picabench_0816_light_propagation` 要求将郁金香上移，并重投影墙上的影子。该 case 的部分 QA 参考答案如下：

| QA | Reference |
|---|---|
| Do the tulip's cast shadow edges have distinct boundaries? | No |
| Is the tulip's cast shadow located in the upper third of the wall? | No |
| Is the tulip's cast shadow identical in shape to the tulip's silhouette? | No |

### 问题

这些参考答案和 prompt/直觉存在张力：

| QA | 疑点 |
|---|---|
| shadow edges distinct | prompt 要求 shadow sharp and complete，但 reference 是 No |
| shadow in upper third | 可能指完整影子不全在上三分之一，但问题措辞不清 |
| identical silhouette | 物理上 No 合理，但和 prompt 的 shape matches 容易混淆 |

### 解决


---

## 条目 9：后续计划

### 背景

当前系统已能跑通闭环、批量评测和 Gradio 展示。

### 问题

系统还没有真正体现复杂 agent 工具路由能力。

### 解决

| 方向 | 目标 |
|---|---|
| 分类 router | 根据 physics_law 选择不同编辑策略 |
| law-specific verifier | 为 8 个 law 设计检查项 |
| QA 可信度标记 | 标注 global/crop/mixed、context_risk、benchmark ambiguity |
| 局部工具链 | 引入 detection / segmentation / mask edit / local repaint |
| 消融实验 | 比较 raw prompt、explicit prompt、planner、verifier retry、router 的增益 |

# Tool Router 与物理编辑工具调研笔记

## 核心结论

图像生成/编辑 agent 的工具扩展不应按模型名称堆叠，而应按“编辑动作 + 物理依赖 + 所需空间输入”组织。GenArtist 的关键经验是为每个工具描述 skill、required inputs、characteristics，并用检测/分割/布局生成等辅助工具补齐缺失的位置输入；IMAGAgent 的关键经验是让工具链编排看到当前图像、当前原子子任务和历史反馈，从而动态选择 detection、segmentation、inpainting、API edit 等工具。

物理一致性任务需要把工具路由从 `direct_edit/local_edit` 扩展为物理类别感知路由。光学任务通常需要光照/阴影/反射区域定位与全局或局部重绘；力学任务通常需要目标、支撑、接触区、受影响对象的联合定位；状态转移任务需要全局场景变换或局部材料状态变换，并用保留区一致性约束避免无关内容漂移。

评分机制不能只依赖 VLM 总分。PICABench/PICAEval 的可复用思想是将物理正确性拆成区域 grounded yes/no QA，并对编辑区域裁剪后评估；项目后续应把 annotated QA、尺寸/画幅检查、非编辑区域一致性和 VLM 分项评分合并为统一的 accept/retry gate。

## 候选工具层

| 工具层 | 代表工具/算法 | 适合解决的问题 | 局限 |
| --- | --- | --- | --- |
| Open-set detection | GroundingDINO | 用文本目标定位物体、支撑、灯、反射物、阴影宿主等 | 检测框不等于精确可编辑区域，小物体和遮挡目标易错 |
| Segmentation | SAM / SAM2 | 从 box/point 生成 mask，用于局部编辑、删除、保护区 | 不理解物理语义；透明物、阴影、反射常需额外提示或人工/规则扩 mask |
| Inpainting | LaMa, diffusion inpainting, API edit with mask | 删除物体、清理背景、修复局部区域 | 只补洞，不自动推导因果后果；大结构变形和光照重算能力有限 |
| Semantic mask editing | DiffEdit | 文本条件下自动推断需改区域，减少手工 mask | mask 来自语义差异，未必覆盖阴影、反射、接触痕迹 |
| Object insertion/replacement | AnyDoor, IP-Adapter-like edit | 添加/替换对象并保留对象身份与局部外观 | 需要后续光照、接触、阴影一致性检查 |
| Spatial control | ControlNet, depth/canny/pose/layout preprocessors | 保持结构、姿态、边缘、深度或布局 | 需要可用的条件图；物理规律仍需外部规划和验证 |
| Drag/edit geometry | DragDiffusion, DragonDiffusion | 移动、拉伸、形变、姿态局部调整 | 需要点/轨迹/区域输入，自动化路由难度较高 |
| Candidate selection | Best-of-N + VLM/PICAEval | 处理生成随机性，选物理分数最高候选 | 成本线性增加；评分器偏差会放大 |

## 面向本项目的路由草案

| route | 触发条件 | 工具链 | 验证重点 |
| --- | --- | --- | --- |
| `direct_global_edit` | 天气、季节、时间、整体光照 | image edit API | 全局色温、阴影方向、材料状态、无关几何保持 |
| `localized_inpaint` | 小目标删除/替换，背景应保持 | detector -> segmenter -> mask edit/inpaint | 目标消失、背景连续、非编辑区 PSNR/SSIM、画幅保持 |
| `remove_with_physics` | 删除支撑物、光源、反射物、遮挡物 | detect target + detect dependent regions -> expanded mask/prompt -> edit | 目标及其阴影/反射/接触痕迹同步更新，因果结果稳定 |
| `add_with_effects` | 添加物体或打开灯/火/水源 | detect receiving surfaces -> edit -> possibly second pass for effects | 新对象接触、阴影、反射、照明/材料响应 |
| `move_or_deform` | 移动、拉伸、倾斜、倒塌 | detect object + optional keypoints/drag handles -> edit | 几何连续、接触点、受力方向、阴影随形变化 |
| `qa_eval_only` | 评测或 debug | crop annotated regions -> VQA yes/no -> aggregate | 每个物理问题的可解释通过/失败证据 |

## 下一步实现顺序

1. 定义 `ToolSpec`：name、route、required_inputs、provided_outputs、cost、risk、physics_tags、failure_modes。
2. 将 Planner 输出扩展为 task profile：operation、physics_law、target_objects、dependent_effects、edit_scope、preserve_scope。
3. Router 根据 task profile 选择 route，而不是只信任 Planner 的 `route` 字段。
4. 加入确定性 guardrails：输出尺寸、输入/输出有效性、非编辑区保护、最大候选数和成本预算。
5. 将 PICABench annotated QA 接入 verifier，形成 `semantic_score + physics_qa_score + preservation_score + guardrail_pass` 的 accept gate。

## 待整理问题与补充

- 本地是否允许安装/运行 GroundingDINO、SAM2、LaMa 等模型仍需确认；如果不允许，第一阶段可先实现工具接口和 mock/metadata-based routing。
- ATR 本地 PDF 目前无法被 `pdftotext` 解析，暂不作为一手细读依据。
- 对透明、阴影、反射这类非实体区域，需要研究 mask 扩展策略：目标 mask 本身不足以覆盖物理依赖区域。

# PICABench 50-case Full Run Results

运行目录：`outputs/picabench_crop_v3_full_20260721/`

本报告对应 2026-07-21 新 crop / 去黑边评测流程：编辑 API 使用 `1024x1024` canonical 输入，结果同时保留 padded candidate 与去黑边 final image；评分使用去黑边并恢复到原图尺寸后的 final image。

## 总体结果

| 指标 | 数值 |
| --- | ---: |
| Cases | 50 |
| QA answer accuracy | 92.7% |
| Non-edit-region PSNR | 22.3037 |
| Agent accepted | 48 |

## 按任务类型汇总

| Physics law | 中文 | Category | Cases | QA accuracy | Non-edit PSNR |
| --- | --- | --- | ---: | ---: | ---: |
| Causality | 因果关系 | Mechanics | 7 | 95.1% | 25.4965 |
| Deformation | 形变 | Mechanics | 6 | 85% | 21.0145 |
| Global | 全局状态 | State | 7 | 95.24% | 9.5194 |
| Light_Propagation | 光传播 | Optics | 6 | 89.29% | 25.9282 |
| Light_Source_Effects | 光源效应 | Optics | 6 | 90.28% | 21.4594 |
| Local | 局部状态 | State | 6 | 95.83% | 26.4459 |
| Reflection | 反射 | Optics | 6 | 100% | 23.7342 |
| Refraction | 折射 | Optics | 6 | 90% | 22.1689 |

## 因果关系（Causality）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts | Final image |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: | --- |
| `picabench_0000_causality` | Mechanics | remove | Yes | 4/4 | 100% | 19.8437 | 1 | unpadded |
| `picabench_0173_causality` | Mechanics | remove | Yes | 4/5 | 80% | 37.5536 | 1 | unpadded |
| `picabench_0294_causality` | Mechanics | remove | Yes | 5/5 | 100% | 19.0013 | 1 | unpadded |
| `picabench_0358_causality` | Mechanics | others | No | 6/7 | 85.71% | 20.4955 | 1 | unpadded |
| `picabench_0589_causality` | Mechanics | others | Yes | 5/5 | 100% | 34.5259 | 1 | unpadded |
| `picabench_0733_causality` | Mechanics | others | Yes | 3/3 | 100% | 27.4814 | 1 | unpadded |
| `picabench_0850_causality` | Mechanics | remove | Yes | 3/3 | 100% | 19.5742 | 1 | unpadded |

## 形变（Deformation）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts | Final image |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: | --- |
| `picabench_0049_deformation` | Mechanics | others | Yes | 4/5 | 80% | 18.5794 | 1 | unpadded |
| `picabench_0226_deformation` | Mechanics | add | Yes | 2/4 | 50% | 23.4436 | 1 | unpadded |
| `picabench_0505_deformation` | Mechanics | remove | Yes | 6/6 | 100% | 21.141 | 1 | unpadded |
| `picabench_0610_deformation` | Mechanics | move | Yes | 5/5 | 100% | 22.8327 | 1 | unpadded |
| `picabench_0700_deformation` | Mechanics | others | No | 4/5 | 80% | 19.8972 | 1 | unpadded |
| `picabench_0821_deformation` | Mechanics | remove | Yes | 3/3 | 100% | 20.1929 | 1 | unpadded |

## 全局状态（Global）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts | Final image |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: | --- |
| `picabench_0020_global` | State | time | Yes | 3/3 | 100% | 9.8884 | 1 | unpadded |
| `picabench_0100_global` | State | weather | Yes | 6/6 | 100% | 9.7559 | 1 | unpadded |
| `picabench_0164_global` | State | season | Yes | 3/3 | 100% | 12.7252 | 1 | unpadded |
| `picabench_0300_global` | State | weather | Yes | 3/3 | 100% | 8.4844 | 1 | unpadded |
| `picabench_0460_global` | State | time | Yes | 2/3 | 66.67% | - | 1 | unpadded |
| `picabench_0658_global` | State | weather | Yes | 3/3 | 100% | - | 1 | unpadded |
| `picabench_0744_global` | State | season | Yes | 5/5 | 100% | 6.7429 | 1 | unpadded |

## 光传播（Light_Propagation）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts | Final image |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: | --- |
| `picabench_0004_light_propagation` | Optics | remove | Yes | 4/4 | 100% | 34.128 | 1 | unpadded |
| `picabench_0032_light_propagation` | Optics | remove | Yes | 6/7 | 85.71% | 31.4857 | 1 | unpadded |
| `picabench_0148_light_propagation` | Optics | remove | Yes | 4/4 | 100% | 14.6235 | 1 | unpadded |
| `picabench_0335_light_propagation` | Optics | move | Yes | 3/3 | 100% | 27.6556 | 1 | unpadded |
| `picabench_0561_light_propagation` | Optics | remove | Yes | 6/6 | 100% | 34.0854 | 1 | unpadded |
| `picabench_0816_light_propagation` | Optics | move | Yes | 3/6 | 50% | 13.5912 | 1 | unpadded |

## 光源效应（Light_Source_Effects）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts | Final image |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: | --- |
| `picabench_0039_light_source_effects` | Optics | add | Yes | 2/3 | 66.67% | 29.9343 | 1 | unpadded |
| `picabench_0117_light_source_effects` | Optics | replace | Yes | 3/4 | 75% | 28.1325 | 1 | unpadded |
| `picabench_0261_light_source_effects` | Optics | add | Yes | 5/5 | 100% | 17.0157 | 1 | unpadded |
| `picabench_0380_light_source_effects` | Optics | add | Yes | 3/3 | 100% | 16.958 | 1 | unpadded |
| `picabench_0500_light_source_effects` | Optics | add | Yes | 3/3 | 100% | 13.5326 | 1 | unpadded |
| `picabench_0766_light_source_effects` | Optics | add | Yes | 4/4 | 100% | 23.1833 | 1 | unpadded |

## 局部状态（Local）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts | Final image |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: | --- |
| `picabench_0064_local` | State | others | Yes | 3/3 | 100% | 14.239 | 1 | unpadded |
| `picabench_0176_local` | State | others | Yes | 3/4 | 75% | 36.7053 | 1 | unpadded |
| `picabench_0402_local` | State | wet | Yes | 6/6 | 100% | 31.093 | 1 | unpadded |
| `picabench_0542_local` | State | wet | Yes | 3/3 | 100% | 21.4826 | 1 | unpadded |
| `picabench_0686_local` | State | wet | Yes | 5/5 | 100% | 24.7882 | 1 | unpadded |
| `picabench_0801_local` | State | frozen | Yes | 7/7 | 100% | 30.3671 | 1 | unpadded |

## 反射（Reflection）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts | Final image |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: | --- |
| `picabench_0007_reflection` | Optics | remove | Yes | 4/4 | 100% | 27.3002 | 1 | unpadded |
| `picabench_0081_reflection` | Optics | replace | Yes | 5/5 | 100% | 22.1533 | 1 | unpadded |
| `picabench_0280_reflection` | Optics | move | Yes | 8/8 | 100% | 20.9507 | 1 | unpadded |
| `picabench_0387_reflection` | Optics | add | Yes | 3/3 | 100% | 29.4973 | 1 | unpadded |
| `picabench_0562_reflection` | Optics | remove | Yes | 4/4 | 100% | 20.2531 | 1 | unpadded |
| `picabench_0799_reflection` | Optics | move | Yes | 7/7 | 100% | 22.2505 | 1 | unpadded |

## 折射（Refraction）

| Case | Category | Operation | Accepted | QA correct/total | QA accuracy | Non-edit PSNR | Attempts | Final image |
| --- | --- | --- | :---: | ---: | ---: | ---: | ---: | --- |
| `picabench_0001_refraction` | Optics | remove | Yes | 3/5 | 60% | 34.7899 | 1 | unpadded |
| `picabench_0017_refraction` | Optics | remove | Yes | 5/5 | 100% | 23.7002 | 1 | unpadded |
| `picabench_0036_refraction` | Optics | remove | Yes | 3/3 | 100% | 26.7043 | 1 | unpadded |
| `picabench_0059_refraction` | Optics | remove | Yes | 3/3 | 100% | 6.2298 | 1 | unpadded |
| `picabench_0139_refraction` | Optics | remove | Yes | 3/3 | 100% | 22.4613 | 1 | unpadded |
| `picabench_0269_refraction` | Optics | remove | Yes | 4/5 | 80% | 19.1279 | 1 | unpadded |

## 指标定义

- `QA accuracy`: PICABench annotated yes/no questions answered correctly by the evaluator.
- `Non-edit-region PSNR`: source/candidate PSNR outside the annotated edit area; higher values indicate stronger preservation of non-edited content.
- `Accepted`: whether the agent verifier accepted the final candidate.
- `Final image`: `unpadded` means scoring uses the output with padding removed and restored to source-image size.

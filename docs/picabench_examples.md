# PICABench Example Subset

This project uses a small local subset of PICABench for physical-consistency image editing checks.

Source dataset: `Andrew613/PICABench` on Hugging Face.

Local files:

```text
data/picabench_examples/
  manifest.json
  picabench_XXXX_.../
    input.png
    metadata.json
```

Each `metadata.json` stores the PICABench row index, physics category, physics law, edit operation, all three prompts, annotated QA pairs, edit areas, and the runnable instruction.

The current representative subset is fixed by row index:

| row | category | law | operation | reason to include |
| --- | --- | --- | --- | --- |
| 0 | Mechanics | Causality | remove | Removing a support must update contact, gravity, tilt, shadows, and reflections. |
| 100 | State | Global | weather | Rain-to-sun requires global illumination, dry materials, shadows, and visibility changes. |
| 300 | State | Global | weather | Snow addition tests accumulation, material change, haze, and tree/road coverage. |
| 500 | Optics | Light_Source_Effects | add | Turning on a lamp tests a new light source and second-order shadow changes. |
| 700 | Mechanics | Deformation | others | Stretching a band tests material deformation, contact, and tension. |
| 850 | Mechanics | Causality | remove | Removing a swing must update the person's pose, support, shadows, and inpainting. |

Download or refresh the fixed subset:

```powershell
python scripts\download_picabench_examples.py --row-idx 0 --row-idx 100 --row-idx 300 --row-idx 500 --row-idx 700 --row-idx 850 --retries 4
```

Inspect the selected cases without calling model APIs:

```powershell
python scripts\run_picabench_examples.py --dry-run
```

Run one case through the agent:

```powershell
python scripts\run_picabench_examples.py --case-id picabench_0000_causality
```

Run a small batch:

```powershell
python scripts\run_picabench_examples.py --limit 3
```

Agent outputs are written under:

```text
outputs/picabench/<case_id>/run_YYYYMMDD_HHMMSS/
```

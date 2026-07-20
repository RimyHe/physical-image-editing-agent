from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from physical_agent.config import load_settings
from physical_agent.orchestrator import run_agent


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run the physical editing agent on PICABench examples.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "picabench_examples" / "manifest.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "picabench")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="Run only this case_id. Repeatable.")
    parser.add_argument("--limit", type=int, help="Run at most this many cases after filtering.")
    parser.add_argument("--dry-run", action="store_true", help="Print selected cases without calling image APIs.")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cases = manifest.get("cases") or []
    if args.case_ids:
        wanted = set(args.case_ids)
        cases = [case for case in cases if case.get("case_id") in wanted]
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No PICABench cases selected.")

    for case in cases:
        print(f"{case['case_id']} | {case.get('physics_category')} | {case.get('physics_law')}")
        print(f"  image: {case['input_png']}")
        print(f"  instruction: {case['instruction']}")
    if args.dry_run:
        return 0

    settings = load_settings()
    summary: list[dict[str, Any]] = []
    for case in cases:
        case_output_root = args.output_root / case["case_id"]
        state = run_agent(settings, Path(case["input_png"]), case["instruction"], case_output_root)
        record = {
            "case_id": case["case_id"],
            "physics_category": case.get("physics_category"),
            "physics_law": case.get("physics_law"),
            "edit_operation": case.get("edit_operation"),
            "accepted": state.accepted,
            "final_image": state.final_image,
            "run_dir": state.run_dir,
            "calls": state.calls,
            "elapsed_seconds": state.elapsed_seconds,
        }
        summary.append(record)

    args.output_root.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_root / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved run summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

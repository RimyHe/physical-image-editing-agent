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
from physical_agent.openai_compat import OpenAICompatClient
from physical_agent.orchestrator import run_agent
from physical_agent.pica_eval import evaluate_picabench_case


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run the physical editing agent on PICABench examples.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "picabench_examples" / "manifest.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "picabench")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="Run only this case_id. Repeatable.")
    parser.add_argument("--limit", type=int, help="Run at most this many cases after filtering.")
    parser.add_argument("--dry-run", action="store_true", help="Print selected cases without calling image APIs.")
    parser.add_argument(
        "--skip-pica-eval",
        action="store_true",
        help="Skip PICABench-style QA accuracy and non-edit PSNR evaluation after each run.",
    )
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
    eval_client = OpenAICompatClient(settings) if not args.skip_pica_eval else None
    summary: list[dict[str, Any]] = []
    for case in cases:
        case_output_root = args.output_root / case["case_id"]
        state = run_agent(settings, Path(case["input_png"]), case["instruction"], case_output_root)
        pica_eval = None
        if eval_client and state.final_image:
            pica_eval = evaluate_picabench_case(
                eval_client,
                settings.verifier_model,
                Path(case["input_png"]),
                Path(state.final_image),
                case,
                Path(state.run_dir) / "pica_eval",
            )
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
        if pica_eval:
            record.update(
                {
                    "pica_accuracy": pica_eval.accuracy,
                    "pica_correct": pica_eval.correct,
                    "pica_total": pica_eval.total,
                    "pica_consistency_psnr": pica_eval.consistency_psnr,
                }
            )
        summary.append(record)

    args.output_root.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_root / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics = aggregate_metrics(summary)
    if metrics:
        metrics_path = args.output_root / "summary_metrics.json"
        metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved PICABench-style metrics to {metrics_path}")
    print(f"Saved run summary to {summary_path}")
    return 0


def aggregate_metrics(summary: list[dict[str, Any]]) -> dict[str, Any]:
    evaluated = [record for record in summary if record.get("pica_accuracy") is not None]
    if not evaluated:
        return {}
    accuracies = [float(record["pica_accuracy"]) for record in evaluated]
    consistency_values = [
        float(record["pica_consistency_psnr"])
        for record in evaluated
        if isinstance(record.get("pica_consistency_psnr"), (int, float))
    ]
    by_law: dict[str, dict[str, Any]] = {}
    for record in evaluated:
        law = str(record.get("physics_law") or "unknown")
        bucket = by_law.setdefault(law, {"count": 0, "accuracy_sum": 0.0, "consistency_sum": 0.0, "consistency_count": 0})
        bucket["count"] += 1
        bucket["accuracy_sum"] += float(record["pica_accuracy"])
        if isinstance(record.get("pica_consistency_psnr"), (int, float)):
            bucket["consistency_sum"] += float(record["pica_consistency_psnr"])
            bucket["consistency_count"] += 1
    return {
        "evaluated_cases": len(evaluated),
        "accuracy": sum(accuracies) / len(accuracies),
        "accuracy_percent": 100 * sum(accuracies) / len(accuracies),
        "consistency_psnr": (sum(consistency_values) / len(consistency_values)) if consistency_values else None,
        "by_physics_law": {
            law: {
                "count": bucket["count"],
                "accuracy": bucket["accuracy_sum"] / bucket["count"],
                "accuracy_percent": 100 * bucket["accuracy_sum"] / bucket["count"],
                "consistency_psnr": (
                    bucket["consistency_sum"] / bucket["consistency_count"] if bucket["consistency_count"] else None
                ),
            }
            for law, bucket in sorted(by_law.items())
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())

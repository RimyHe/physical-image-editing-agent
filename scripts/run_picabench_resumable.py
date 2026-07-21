from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from physical_agent.config import load_settings
from physical_agent.openai_compat import OpenAICompatClient
from physical_agent.orchestrator import run_agent
from physical_agent.pica_eval import evaluate_picabench_case, prepare_canonical_input, write_unpadded_output
from run_picabench_examples import aggregate_metrics


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run PICABench examples with per-case retry and checkpointing.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "picabench_examples" / "manifest.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "picabench_resumable")
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--retry-sleep", type=int, default=30)
    parser.add_argument("--resume", action="store_true", help="Skip cases already present in summary.json.")
    args = parser.parse_args()

    args.output_root.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cases = manifest.get("cases") or []
    if args.case_ids:
        wanted = set(args.case_ids)
        cases = [case for case in cases if case.get("case_id") in wanted]
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No PICABench cases selected.")

    summary_path = args.output_root / "summary.json"
    summary: list[dict[str, Any]] = []
    if args.resume and summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    completed = {record.get("case_id") for record in summary if record.get("error") is None}
    settings = load_settings()
    eval_client = OpenAICompatClient(settings)

    for index, case in enumerate(cases, start=1):
        case_id = case["case_id"]
        if case_id in completed:
            print(f"[{index}/{len(cases)}] skip completed {case_id}", flush=True)
            continue

        print(f"[{index}/{len(cases)}] run {case_id}", flush=True)
        record = run_case_with_retry(settings, eval_client, case, args.output_root, args.attempts, args.retry_sleep)
        summary = [old for old in summary if old.get("case_id") != case_id]
        summary.append(record)
        write_summary(args.output_root, summary)

    return 0


def run_case_with_retry(
    settings: Any,
    eval_client: OpenAICompatClient,
    case: dict[str, Any],
    output_root: Path,
    attempts: int,
    retry_sleep: int,
) -> dict[str, Any]:
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            case_output_root = output_root / case["case_id"]
            case_output_root.mkdir(parents=True, exist_ok=True)
            canonical_input = case_output_root / "canonical_input.png"
            transform_path = case_output_root / "coordinate_transform.json"
            transform = prepare_canonical_input(Path(case["input_png"]), canonical_input, transform_path)
            eval_case = dict(case)
            eval_case["coordinate_transform"] = transform
            eval_case["canonical_input_png"] = str(canonical_input)
            state = run_agent(settings, canonical_input, case["instruction"], case_output_root, eval_case)
            final_image_padded = state.final_image
            final_image_unpadded = None
            if state.final_image:
                final_image_unpadded = str(Path(state.run_dir) / "final_image_unpadded.png")
                write_unpadded_output(Path(state.final_image), Path(final_image_unpadded), transform)
            pica_eval = None
            if final_image_unpadded:
                pica_eval = evaluate_picabench_case(
                    eval_client,
                    settings.verifier_model,
                    Path(case["input_png"]),
                    Path(final_image_unpadded),
                    case,
                    Path(state.run_dir) / "pica_eval",
                )
            record: dict[str, Any] = {
                "case_id": case["case_id"],
                "physics_category": case.get("physics_category"),
                "physics_law": case.get("physics_law"),
                "edit_operation": case.get("edit_operation"),
                "accepted": state.accepted,
                "final_image": final_image_unpadded,
                "final_image_padded": final_image_padded,
                "final_image_unpadded": final_image_unpadded,
                "run_dir": state.run_dir,
                "canonical_input": str(canonical_input),
                "coordinate_transform": str(transform_path),
                "calls": state.calls,
                "elapsed_seconds": state.elapsed_seconds,
                "attempt": attempt,
                "error": None,
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
            return record
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"  attempt {attempt}/{attempts} failed: {last_error}", flush=True)
            if attempt < attempts:
                time.sleep(retry_sleep)

    return {
        "case_id": case["case_id"],
        "physics_category": case.get("physics_category"),
        "physics_law": case.get("physics_law"),
        "edit_operation": case.get("edit_operation"),
        "accepted": False,
        "final_image": None,
        "run_dir": None,
        "calls": None,
        "elapsed_seconds": None,
        "attempt": attempts,
        "error": last_error,
        "pica_accuracy": None,
        "pica_correct": None,
        "pica_total": None,
        "pica_consistency_psnr": None,
    }


def write_summary(output_root: Path, summary: list[dict[str, Any]]) -> None:
    summary_path = output_root / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics = aggregate_metrics(summary)
    if metrics:
        (output_root / "summary_metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    raise SystemExit(main())

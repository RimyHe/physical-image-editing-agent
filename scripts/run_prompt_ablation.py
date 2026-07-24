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
from physical_agent.editor import execute_edit
from physical_agent.openai_compat import OpenAICompatClient
from physical_agent.physical_intent import PhysicalIntentExpander
from physical_agent.pica_eval import prepare_canonical_input, write_unpadded_output


VARIANTS = ("superficial", "physical_intent", "explicit")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run prompt ablation on selected PICABench cases.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "picabench_examples" / "manifest.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "prompt_ablation")
    parser.add_argument(
        "--case",
        action="append",
        dest="case_keys",
        required=True,
        help="Case id, row number, or numeric key such as 358/000/294. Repeatable.",
    )
    parser.add_argument(
        "--variant",
        action="append",
        choices=VARIANTS,
        dest="variants",
        help="Variant to run. Repeatable. Defaults to superficial, physical_intent, explicit.",
    )
    parser.add_argument(
        "--label-mode",
        choices=["inferred", "gold"],
        default="inferred",
        help="PhysicalIntent label mode. Gold is analysis-only and passes PICABench labels to the expander.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cases = select_cases(load_manifest(args.manifest), args.case_keys)
    variants = tuple(args.variants or VARIANTS)
    print_selection(cases, variants, args.label_mode)
    if args.dry_run:
        return 0

    settings = load_settings()
    client = OpenAICompatClient(settings)
    expander = PhysicalIntentExpander(client, settings.planner_model)
    run_dir = args.output_root / time.strftime("run_%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=False)

    records: list[dict[str, Any]] = []
    for case_index, case in enumerate(cases, start=1):
        case_id = str(case["case_id"])
        print(f"[{case_index}/{len(cases)}] {case_id}", flush=True)
        case_dir = run_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        canonical_input = case_dir / "canonical_input.png"
        transform_path = case_dir / "coordinate_transform.json"
        transform = prepare_canonical_input(Path(str(case["input_png"])), canonical_input, transform_path)

        case_record: dict[str, Any] = {
            "case_id": case_id,
            "row_idx": case.get("row_idx"),
            "physics_category": case.get("physics_category"),
            "physics_law": case.get("physics_law"),
            "edit_operation": case.get("edit_operation"),
            "input_png": case.get("input_png"),
            "canonical_input": str(canonical_input),
            "coordinate_transform": str(transform_path),
            "variants": {},
        }
        for variant in variants:
            print(f"  - {variant}", flush=True)
            case_record["variants"][variant] = run_variant(
                client=client,
                expander=expander,
                settings=settings,
                case=case,
                variant=variant,
                case_dir=case_dir,
                canonical_input=canonical_input,
                transform=transform,
                label_mode=args.label_mode,
            )
        records.append(case_record)
        write_outputs(run_dir, records, variants, args.label_mode)

    print(f"Saved ablation report to {run_dir / 'report.md'}")
    print(f"Saved ablation summary to {run_dir / 'summary.json'}")
    return 0


def load_manifest(path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return list(manifest.get("cases") or [])


def select_cases(cases: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for key in keys:
        normalized = normalize_case_key(key)
        matches = [
            case
            for case in cases
            if str(case.get("case_id")) == key
            or normalize_case_key(str(case.get("row_idx"))) == normalized
            or f"_{normalized}_" in str(case.get("case_id"))
        ]
        if not matches:
            raise SystemExit(f"No case matched {key!r}.")
        if len(matches) > 1:
            ids = ", ".join(str(case.get("case_id")) for case in matches)
            raise SystemExit(f"Case key {key!r} matched multiple cases: {ids}")
        selected.append(matches[0])
    return selected


def normalize_case_key(value: str) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits.zfill(4) if digits else str(value)


def print_selection(cases: list[dict[str, Any]], variants: tuple[str, ...], label_mode: str) -> None:
    print(f"Selected {len(cases)} cases; variants={list(variants)}; label_mode={label_mode}")
    for case in cases:
        print(
            "  {case_id} | {law} | {operation}".format(
                case_id=case.get("case_id"),
                law=case.get("physics_law"),
                operation=case.get("edit_operation"),
            )
        )


def run_variant(
    client: OpenAICompatClient,
    expander: PhysicalIntentExpander,
    settings: Any,
    case: dict[str, Any],
    variant: str,
    case_dir: Path,
    canonical_input: Path,
    transform: dict[str, Any],
    label_mode: str,
) -> dict[str, Any]:
    variant_dir = case_dir / variant
    variant_dir.mkdir(parents=True, exist_ok=True)
    prompt_record = build_prompt(expander, case, variant, label_mode, canonical_input)
    prompt = str(prompt_record.get("prompt") or "")
    (variant_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    (variant_dir / "prompt_record.json").write_text(
        json.dumps(prompt_record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    candidate_padded = variant_dir / "candidate_padded.png"
    candidate_unpadded = variant_dir / "candidate_unpadded.png"
    record: dict[str, Any] = {
        "prompt": prompt,
        "prompt_words": len(prompt.split()),
        "prompt_record": str(variant_dir / "prompt_record.json"),
        "candidate_padded": str(candidate_padded),
        "candidate_unpadded": str(candidate_unpadded),
        "error": None,
    }
    try:
        execute_edit(client, settings.image_edit_model, canonical_input, prompt, candidate_padded)
        write_unpadded_output(candidate_padded, candidate_unpadded, transform)
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        print(f"    failed: {record['error']}", flush=True)
    return record


def build_prompt(
    expander: PhysicalIntentExpander,
    case: dict[str, Any],
    variant: str,
    label_mode: str,
    canonical_input: Path,
) -> dict[str, Any]:
    prompts = case.get("prompts") if isinstance(case.get("prompts"), dict) else {}
    if variant == "superficial":
        prompt = str(prompts.get("superficial") or case.get("instruction") or "")
        return {"variant": variant, "prompt": prompt}
    if variant == "explicit":
        prompt = str(prompts.get("explicit") or case.get("instruction") or "")
        return {"variant": variant, "prompt": prompt}
    if variant != "physical_intent":
        raise ValueError(f"Unsupported variant: {variant}")

    superficial = str(prompts.get("superficial") or case.get("instruction") or "")
    task_labels = None
    if label_mode == "gold":
        task_labels = {
            "physics_category": str(case.get("physics_category") or ""),
            "physics_law": str(case.get("physics_law") or ""),
            "edit_operation": str(case.get("edit_operation") or ""),
        }
    try:
        profile = expander.expand(canonical_input, superficial, task_labels=task_labels)
        return {
            "variant": variant,
            "input_prompt": superficial,
            "prompt": str(profile.get("edit_prompt") or superficial),
            "task_profile": profile,
            "diagnostics": profile.get("diagnostics"),
        }
    except Exception as exc:
        return {
            "variant": variant,
            "input_prompt": superficial,
            "prompt": superficial,
            "error": f"{type(exc).__name__}: {exc}",
            "diagnostics": {"expansion_failures": ["expander_call_failed"]},
        }


def write_outputs(run_dir: Path, records: list[dict[str, Any]], variants: tuple[str, ...], label_mode: str) -> None:
    (run_dir / "summary.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "report.md").write_text(render_report(records, variants, label_mode), encoding="utf-8")


def render_report(records: list[dict[str, Any]], variants: tuple[str, ...], label_mode: str) -> str:
    lines = [
        "# Prompt Ablation Report",
        "",
        f"- Variants: `{', '.join(variants)}`",
        f"- PhysicalIntent label mode: `{label_mode}`",
        "- Each variant uses one image edit call and no retry.",
        "",
    ]
    for record in records:
        lines.extend(render_case(record, variants))
    return "\n".join(lines).rstrip() + "\n"


def render_case(record: dict[str, Any], variants: tuple[str, ...]) -> list[str]:
    lines = [
        f"## {record.get('case_id')}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Physics law | `{record.get('physics_law')}` |",
        f"| Edit operation | `{record.get('edit_operation')}` |",
        f"| Canonical input | `{record.get('canonical_input')}` |",
        "",
    ]
    for variant in variants:
        variant_record = record.get("variants", {}).get(variant, {})
        lines.extend(
            [
                f"### {variant}",
                "",
                f"- Prompt words: `{variant_record.get('prompt_words')}`",
                f"- Candidate padded: `{variant_record.get('candidate_padded')}`",
                f"- Candidate unpadded: `{variant_record.get('candidate_unpadded')}`",
                f"- Error: `{variant_record.get('error')}`",
                "",
                "```text",
                str(variant_record.get("prompt") or "").strip(),
                "```",
                "",
            ]
        )
    return lines


if __name__ == "__main__":
    raise SystemExit(main())

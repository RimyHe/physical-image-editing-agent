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
from physical_agent.physical_intent import PhysicalIntentExpander


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Compare PhysicalIntent-generated prompts with PICABench explicit prompts."
    )
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "picabench_examples" / "manifest.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "physical_intent_prompt_compare")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="Compare only this case_id. Repeatable.")
    parser.add_argument("--limit", type=int, help="Compare at most this many cases after filtering.")
    parser.add_argument(
        "--label-mode",
        choices=["inferred", "gold"],
        default="inferred",
        help="Use inferred labels from the prompt, or pass PICABench labels for analysis-only runs.",
    )
    parser.add_argument(
        "--prompt-level",
        choices=["superficial", "intermediate"],
        default="superficial",
        help="Input prompt level for PhysicalIntent. The explicit prompt is always held out for comparison.",
    )
    parser.add_argument("--model", help="Override planner/PhysicalIntent model from .env.")
    parser.add_argument("--dry-run", action="store_true", help="Print selected cases without calling the VLM API.")
    args = parser.parse_args()

    cases = select_cases(load_manifest(args.manifest), args.case_ids, args.limit)
    if not cases:
        raise SystemExit("No PICABench cases selected.")

    print_selection(cases, args.prompt_level, args.label_mode)
    if args.dry_run:
        return 0

    settings = load_settings()
    client = OpenAICompatClient(settings)
    expander = PhysicalIntentExpander(client, args.model or settings.planner_model)

    records: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id"))
        print(f"[{index}/{len(cases)}] expand {case_id}", flush=True)
        try:
            records.append(compare_case(expander, case, args.prompt_level, args.label_mode))
        except Exception as exc:
            print(f"  failed: {type(exc).__name__}: {exc}", flush=True)
            records.append(error_record(case, args.prompt_level, args.label_mode, exc))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "physical_intent_prompt_comparison.json"
    md_path = args.output_dir / "physical_intent_prompt_comparison.md"
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(records, args.prompt_level, args.label_mode), encoding="utf-8")
    print(f"Saved JSON comparison to {json_path}")
    print(f"Saved Markdown comparison to {md_path}")
    return 0


def load_manifest(path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return list(manifest.get("cases") or [])


def select_cases(
    cases: list[dict[str, Any]],
    case_ids: list[str] | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    if case_ids:
        wanted = set(case_ids)
        cases = [case for case in cases if case.get("case_id") in wanted]
    if limit is not None:
        cases = cases[:limit]
    return cases


def print_selection(cases: list[dict[str, Any]], prompt_level: str, label_mode: str) -> None:
    print(f"Selected {len(cases)} case(s); prompt_level={prompt_level}; label_mode={label_mode}")
    for case in cases:
        print(
            "  {case_id} | {category} | {law} | {operation}".format(
                case_id=case.get("case_id"),
                category=case.get("physics_category"),
                law=case.get("physics_law"),
                operation=case.get("edit_operation"),
            )
        )


def compare_case(
    expander: PhysicalIntentExpander,
    case: dict[str, Any],
    prompt_level: str,
    label_mode: str,
) -> dict[str, Any]:
    prompts = case.get("prompts") if isinstance(case.get("prompts"), dict) else {}
    input_prompt = str(prompts.get(prompt_level) or case.get("instruction") or "")
    explicit_prompt = str(prompts.get("explicit") or case.get("instruction") or "")
    task_labels = None
    if label_mode == "gold":
        task_labels = {
            "physics_category": str(case.get("physics_category") or ""),
            "physics_law": str(case.get("physics_law") or ""),
            "edit_operation": str(case.get("edit_operation") or ""),
        }

    profile = expander.expand(
        image_path=Path(str(case.get("input_png"))),
        instruction=input_prompt,
        task_labels=task_labels,
    )
    generated_prompt = str(profile.get("edit_prompt") or "")
    diagnostics = profile.get("diagnostics") if isinstance(profile.get("diagnostics"), dict) else {}

    return {
        "case_id": case.get("case_id"),
        "physics_category": case.get("physics_category"),
        "physics_law": case.get("physics_law"),
        "edit_operation": case.get("edit_operation"),
        "label_mode": label_mode,
        "input_prompt_level": prompt_level,
        "input_prompt": input_prompt,
        "generated_prompt": generated_prompt,
        "explicit_prompt": explicit_prompt,
        "generated_prompt_words": len(generated_prompt.split()),
        "explicit_prompt_words": len(explicit_prompt.split()),
        "labels_used_by_component": profile.get("labels"),
        "diagnostics": diagnostics,
        "task_profile": {
            "physical_operation": profile.get("physical_operation"),
            "final_state": profile.get("final_state"),
            "target_objects": profile.get("target_objects"),
            "affected_objects": profile.get("affected_objects"),
            "physical_dependencies": profile.get("physical_dependencies"),
            "dependent_regions": profile.get("dependent_regions"),
            "preserve_scope": profile.get("preserve_scope"),
            "reference_cues": profile.get("reference_cues"),
            "uncertainties": profile.get("uncertainties"),
            "must_pass_checks": profile.get("must_pass_checks"),
            "route_hints": profile.get("route_hints"),
        },
    }


def error_record(
    case: dict[str, Any],
    prompt_level: str,
    label_mode: str,
    exc: Exception,
) -> dict[str, Any]:
    prompts = case.get("prompts") if isinstance(case.get("prompts"), dict) else {}
    return {
        "case_id": case.get("case_id"),
        "physics_category": case.get("physics_category"),
        "physics_law": case.get("physics_law"),
        "edit_operation": case.get("edit_operation"),
        "label_mode": label_mode,
        "input_prompt_level": prompt_level,
        "input_prompt": str(prompts.get(prompt_level) or case.get("instruction") or ""),
        "generated_prompt": "",
        "explicit_prompt": str(prompts.get("explicit") or case.get("instruction") or ""),
        "generated_prompt_words": 0,
        "explicit_prompt_words": len(str(prompts.get("explicit") or case.get("instruction") or "").split()),
        "labels_used_by_component": None,
        "diagnostics": {
            "validation_errors": [],
            "validation_warnings": [],
            "auto_filled_fields": [],
            "expansion_failures": ["expander_call_failed"],
            "evidence_conflicts": [],
            "prompt_length": 0,
            "error": f"{type(exc).__name__}: {exc}",
        },
        "task_profile": {},
    }


def render_markdown(records: list[dict[str, Any]], prompt_level: str, label_mode: str) -> str:
    lines = [
        "# PhysicalIntent Prompt Comparison",
        "",
        f"- Input prompt level: `{prompt_level}`",
        f"- Label mode: `{label_mode}`",
        "- PICABench `explicit_prompt` is shown only as a comparison target, not as runtime input.",
        "",
    ]
    for record in records:
        lines.extend(render_record(record))
    return "\n".join(lines).rstrip() + "\n"


def render_record(record: dict[str, Any]) -> list[str]:
    diagnostics = record.get("diagnostics") if isinstance(record.get("diagnostics"), dict) else {}
    profile = record.get("task_profile") if isinstance(record.get("task_profile"), dict) else {}
    lines = [
        f"## {record.get('case_id')}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Physics category | `{record.get('physics_category')}` |",
        f"| Physics law | `{record.get('physics_law')}` |",
        f"| Edit operation | `{record.get('edit_operation')}` |",
        f"| Labels used by component | `{record.get('labels_used_by_component')}` |",
        f"| Generated prompt words | `{record.get('generated_prompt_words')}` |",
        f"| Explicit prompt words | `{record.get('explicit_prompt_words')}` |",
        f"| Validation errors | `{diagnostics.get('validation_errors', [])}` |",
        f"| Validation warnings | `{diagnostics.get('validation_warnings', [])}` |",
        f"| Expansion failures | `{diagnostics.get('expansion_failures', [])}` |",
        "",
        "### Input Prompt",
        "",
        fenced(record.get("input_prompt")),
        "",
        "### PhysicalIntent Generated Prompt",
        "",
        fenced(record.get("generated_prompt")),
        "",
        "### PICABench Explicit Prompt",
        "",
        fenced(record.get("explicit_prompt")),
        "",
        "### Generated TaskProfile Summary",
        "",
        fenced(json.dumps(profile, ensure_ascii=False, indent=2), "json"),
        "",
    ]
    return lines


def fenced(value: Any, language: str = "text") -> str:
    return f"```{language}\n{str(value or '').strip()}\n```"


if __name__ == "__main__":
    raise SystemExit(main())

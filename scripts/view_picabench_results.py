from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import gradio as gr


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


LAWS = ["All", "Causality", "Deformation", "Global", "Light_Propagation", "Light_Source_Effects", "Local", "Reflection", "Refraction"]
CATEGORIES = ["All", "Mechanics", "Optics", "State"]
OPERATIONS = ["All", "add", "deform", "move", "others", "remove", "replace", "weather"]


def load_records(summary_path: Path, manifest_path: Path) -> list[dict[str, Any]]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_by_id = {case["case_id"]: case for case in manifest.get("cases", [])}
    records: list[dict[str, Any]] = []
    for record in summary:
        merged = {**manifest_by_id.get(record["case_id"], {}), **record}
        merged["pica_eval_path"] = find_pica_eval(Path(record["run_dir"])) if record.get("run_dir") else None
        records.append(merged)
    return sorted(records, key=lambda item: item["case_id"])


def find_pica_eval(run_dir: Path) -> str | None:
    path = run_dir / "pica_eval" / "pica_eval.json"
    return str(path) if path.exists() else None


def filter_records(records: list[dict[str, Any]], law: str, category: str, operation: str) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if (law == "All" or record.get("physics_law") == law)
        and (category == "All" or record.get("physics_category") == category)
        and (operation == "All" or record.get("edit_operation") == operation)
    ]


def summary_rows(records: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [
            record["case_id"],
            record.get("physics_law", ""),
            record.get("physics_category", ""),
            record.get("edit_operation", ""),
            "Yes" if record.get("accepted") else "No",
            format_percent(record.get("pica_accuracy")),
            format_number(record.get("pica_consistency_psnr")),
            record.get("attempt", ""),
        ]
        for record in records
    ]


def format_percent(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.2f}%"


def format_number(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value):.4f}"


def case_choices(records: list[dict[str, Any]]) -> list[str]:
    return [record["case_id"] for record in records]


def select_case(records: list[dict[str, Any]], case_id: str | None) -> tuple[Any, ...]:
    record = next((item for item in records if item["case_id"] == case_id), None)
    if not record:
        return (None, None, "请选择一个 case。", "", "", [], [])

    instruction = str(record.get("instruction") or "")
    score_markdown = "\n".join(
        [
            f"### {record['case_id']}",
            f"- 任务类型：`{record.get('physics_law', '-')}`",
            f"- 物理类别：`{record.get('physics_category', '-')}`",
            f"- 编辑操作：`{record.get('edit_operation', '-')}`",
            f"- Agent 验证：**{'通过' if record.get('accepted') else '未通过'}**",
            f"- QA 正确率：**{format_percent(record.get('pica_accuracy'))}**（{record.get('pica_correct', '-')}/{record.get('pica_total', '-')}）",
            f"- 未编辑区域 PSNR：**{format_number(record.get('pica_consistency_psnr'))}**",
            f"- 耗时：`{record.get('elapsed_seconds', '-')} 秒`，尝试次数：`{record.get('attempt', '-')}`",
        ]
    )

    qa_rows: list[list[Any]] = []
    gallery: list[tuple[str, str]] = []
    pica_path = record.get("pica_eval_path")
    if pica_path and Path(pica_path).exists():
        pica = json.loads(Path(pica_path).read_text(encoding="utf-8"))
        for item in pica.get("qa_results", []):
            qa_rows.append(
                [
                    item.get("index", ""),
                    item.get("question", ""),
                    item.get("reference_answer", ""),
                    item.get("predicted_answer", ""),
                    "Yes" if item.get("correct") else "No",
                    item.get("rationale", ""),
                ]
            )
            crop_path = item.get("crop_path")
            if crop_path and Path(crop_path).exists():
                gallery.append((crop_path, f"Q{item.get('index', '')}"))

    return (
        record.get("input_png"),
        record.get("final_image"),
        score_markdown,
        instruction,
        record.get("run_dir", ""),
        qa_rows,
        gallery,
    )


def build_app(records: list[dict[str, Any]]) -> gr.Blocks:
    headers = ["Case", "Physics law", "Category", "Operation", "Accepted", "QA accuracy", "Non-edit PSNR", "Attempts"]
    qa_headers = ["Index", "Question", "Reference", "Prediction", "Correct", "Rationale"]

    with gr.Blocks(title="PICABench Results Viewer") as app:
        gr.Markdown("# PICABench 结果查看器\n浏览原图、编辑指令、模型结果和物理一致性评分。")
        with gr.Row():
            law = gr.Dropdown(LAWS, value="All", label="任务类型")
            category = gr.Dropdown(CATEGORIES, value="All", label="物理类别")
            operation = gr.Dropdown(OPERATIONS, value="All", label="编辑操作")
            case = gr.Dropdown(case_choices(records), label="选择 Case", scale=2)

        table = gr.Dataframe(
            value=summary_rows(records),
            headers=headers,
            datatype=["str"] * len(headers),
            interactive=False,
            label="Case 总览",
            wrap=True,
        )
        with gr.Row():
            original = gr.Image(label="原图", type="filepath")
            result = gr.Image(label="模型结果", type="filepath")
        score = gr.Markdown("请选择一个 case。")
        instruction = gr.Textbox(label="修改指令", lines=8, interactive=False)
        run_dir = gr.Textbox(label="运行目录", interactive=False)
        qa_table = gr.Dataframe(
            headers=qa_headers,
            datatype=["number", "str", "str", "str", "str", "str"],
            interactive=False,
            label="PICABench QA 逐题结果",
            wrap=True,
        )
        qa_gallery = gr.Gallery(label="QA 裁剪区域", columns=4, height="auto", object_fit="contain")

        def update_filters(selected_law: str, selected_category: str, selected_operation: str):
            filtered = filter_records(records, selected_law, selected_category, selected_operation)
            choices = case_choices(filtered)
            selected = choices[0] if choices else None
            details = select_case(records, selected)
            return summary_rows(filtered), gr.update(choices=choices, value=selected), *details

        def update_case(selected_case: str):
            return select_case(records, selected_case)

        filter_outputs = [table, case, original, result, score, instruction, run_dir, qa_table, qa_gallery]
        law.change(update_filters, [law, category, operation], filter_outputs)
        category.change(update_filters, [law, category, operation], filter_outputs)
        operation.change(update_filters, [law, category, operation], filter_outputs)
        case.change(
            update_case,
            [case],
            [original, result, score, instruction, run_dir, qa_table, qa_gallery],
        )

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the Gradio PICABench results viewer.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=ROOT / "outputs" / "picabench_full_20260721_resumable" / "summary.json",
    )
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "picabench_examples" / "manifest.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    records = load_records(args.summary, args.manifest)
    if not records:
        raise SystemExit("No records found.")
    app = build_app(records)
    app.launch(server_name=args.host, server_port=args.port, share=args.share)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

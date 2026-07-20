from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .openai_compat import OpenAICompatClient, vision_user_message


PICAEVAL_SYSTEM = """You are a strict PICABench-style image editing evaluator.
Answer each question using only the visible content inside its cropped region.
Return strict JSON only with key answers. answers must be a list of objects with keys index, answer, rationale.
Each answer must be exactly "Yes" or "No"."""


@dataclass
class QAEvalResult:
    index: int
    question: str
    reference_answer: str
    predicted_answer: str
    correct: bool
    crop_path: str | None = None
    rationale: str | None = None


@dataclass
class PicaEvalResult:
    accuracy: float | None
    correct: int
    total: int
    consistency_psnr: float | None
    qa_results: list[QAEvalResult]


def evaluate_picabench_case(
    client: OpenAICompatClient,
    model: str,
    source_image: Path,
    edited_image: Path,
    metadata: dict[str, Any],
    output_dir: Path,
) -> PicaEvalResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    qa_pairs = list(metadata.get("annotated_qa_pairs") or [])
    qa_results = evaluate_qa_pairs(client, model, edited_image, metadata, qa_pairs, output_dir)
    total = len(qa_results)
    correct = sum(1 for item in qa_results if item.correct)
    accuracy = correct / total if total else None
    consistency_psnr = compute_non_edit_psnr(source_image, edited_image, metadata.get("edit_area") or [])
    result = PicaEvalResult(
        accuracy=accuracy,
        correct=correct,
        total=total,
        consistency_psnr=consistency_psnr,
        qa_results=qa_results,
    )
    (output_dir / "pica_eval.json").write_text(
        json.dumps(_to_jsonable(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def evaluate_qa_pairs(
    client: OpenAICompatClient,
    model: str,
    edited_image: Path,
    metadata: dict[str, Any],
    qa_pairs: list[dict[str, Any]],
    output_dir: Path,
) -> list[QAEvalResult]:
    if not qa_pairs:
        return []

    crop_paths: list[Path] = []
    with Image.open(edited_image) as raw_image:
        image = raw_image.convert("RGB")
        original_size = _metadata_image_size(metadata) or image.size
        for index, qa in enumerate(qa_pairs):
            box = qa.get("box") or _first_box(metadata.get("edit_area"))
            crop_path = output_dir / f"qa_region_{index:02d}.png"
            crop_region(image, box, original_size).save(crop_path)
            crop_paths.append(crop_path)

    question_lines = []
    for index, qa in enumerate(qa_pairs):
        question_lines.append(f"{index}. {qa.get('question', '')}")
    user_text = (
        "Evaluate these cropped edited-image regions. Image 0 corresponds to question 0, and so on.\n"
        f"Edit instruction: {metadata.get('instruction', '')}\n"
        f"Physics law: {metadata.get('physics_law', '')}\n"
        "Questions:\n"
        + "\n".join(question_lines)
        + "\nReturn one Yes/No answer per question. Do not compare with the original image."
    )
    response = client.chat_json(
        model,
        [
            {"role": "system", "content": PICAEVAL_SYSTEM},
            vision_user_message(user_text, crop_paths),
        ],
        max_tokens=1200,
    )
    predicted = _answers_by_index(response.get("answers"))
    results: list[QAEvalResult] = []
    for index, qa in enumerate(qa_pairs):
        reference = _normalize_yes_no(qa.get("answer"))
        answer_obj = predicted.get(index, {})
        prediction = _normalize_yes_no(answer_obj.get("answer"))
        results.append(
            QAEvalResult(
                index=index,
                question=str(qa.get("question") or ""),
                reference_answer=reference,
                predicted_answer=prediction,
                correct=bool(reference and prediction and reference == prediction),
                crop_path=str(crop_paths[index]),
                rationale=answer_obj.get("rationale"),
            )
        )
    return results


def crop_region(image: Image.Image, box: dict[str, Any] | None, original_size: tuple[int, int]) -> Image.Image:
    if not box:
        return image.copy()
    width, height = image.size
    original_width, original_height = original_size
    scale_x = width / original_width
    scale_y = height / original_height
    x1 = int(max(0, float(box.get("x", 0)) * scale_x))
    y1 = int(max(0, float(box.get("y", 0)) * scale_y))
    x2 = int(min(width, (float(box.get("x", 0)) + float(box.get("width", 0))) * scale_x))
    y2 = int(min(height, (float(box.get("y", 0)) + float(box.get("height", 0))) * scale_y))
    if x2 <= x1 or y2 <= y1:
        return image.copy()
    return image.crop((x1, y1, x2, y2))


def compute_non_edit_psnr(source_image: Path, edited_image: Path, edit_areas: list[dict[str, Any]]) -> float | None:
    with Image.open(source_image) as raw_source, Image.open(edited_image) as raw_edited:
        source = raw_source.convert("RGB")
        edited = raw_edited.convert("RGB").resize(source.size, Image.Resampling.BICUBIC)
        if not edit_areas:
            mask = Image.new("1", source.size, 0)
        else:
            mask = Image.new("1", source.size, 0)
            draw = ImageDraw.Draw(mask)
            for area in edit_areas:
                x1 = max(0, float(area.get("x", 0)))
                y1 = max(0, float(area.get("y", 0)))
                x2 = min(source.width, x1 + float(area.get("width", 0)))
                y2 = min(source.height, y1 + float(area.get("height", 0)))
                if x2 > x1 and y2 > y1:
                    draw.rectangle((x1, y1, x2, y2), fill=1)

        source_pixels = source.load()
        edited_pixels = edited.load()
        mask_pixels = mask.load()
        squared_error = 0.0
        count = 0
        for y in range(source.height):
            for x in range(source.width):
                if mask_pixels[x, y]:
                    continue
                src = source_pixels[x, y]
                dst = edited_pixels[x, y]
                squared_error += sum((float(dst[channel]) - float(src[channel])) ** 2 for channel in range(3))
                count += 3
        if count == 0:
            return None
        mse = squared_error / count
        if mse == 0:
            return float("inf")
        return round(10 * math.log10((255.0**2) / mse), 4)


def _metadata_image_size(metadata: dict[str, Any]) -> tuple[int, int] | None:
    size = metadata.get("input_image_size") or {}
    width = size.get("width")
    height = size.get("height")
    if width and height:
        return int(width), int(height)
    return None


def _first_box(value: Any) -> dict[str, Any] | None:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return first
    return None


def _answers_by_index(raw_answers: Any) -> dict[int, dict[str, Any]]:
    answers: dict[int, dict[str, Any]] = {}
    if not isinstance(raw_answers, list):
        return answers
    for item in raw_answers:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        answers[index] = item
    return answers


def _normalize_yes_no(value: Any) -> str:
    text = str(value or "").strip().lower().rstrip(".")
    if text == "yes":
        return "Yes"
    if text == "no":
        return "No"
    return ""


def _to_jsonable(result: PicaEvalResult) -> dict[str, Any]:
    value = asdict(result)
    if value["consistency_psnr"] == float("inf"):
        value["consistency_psnr"] = "inf"
    return value

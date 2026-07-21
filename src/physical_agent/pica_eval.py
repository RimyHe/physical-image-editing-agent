from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .openai_compat import OpenAICompatClient, vision_user_message


PICAEVAL_SYSTEM = """You are a strict PICABench-style image editing evaluator.
Return strict JSON only with key answers. answers must be a list of objects with keys index, answer, rationale.
Each answer must be exactly "Yes" or "No"."""

CANONICAL_SIZE = (1024, 1024)


@dataclass
class QAEvalResult:
    index: int
    question: str
    reference_answer: str
    predicted_answer: str
    correct: bool
    question_type: str
    evaluation_view: str
    crop_path: str | None = None
    full_image_path: str | None = None
    source_box: dict[str, float] | None = None
    mapped_box: dict[str, float] | None = None
    output_size: tuple[int, int] | None = None
    context_risk: bool = False
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
    consistency_psnr = compute_non_edit_psnr(source_image, edited_image, metadata.get("edit_area") or [], metadata)
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

    eval_items: list[dict[str, Any]] = []
    with Image.open(edited_image) as raw_image:
        image = raw_image.convert("RGB")
        output_size = image.size
        transform = coordinate_transform(metadata, output_size)
        for index, qa in enumerate(qa_pairs):
            box = qa.get("box") or _first_box(metadata.get("edit_area"))
            mapped_box = source_box_to_output_box(box, transform, output_size) if box else None
            crop_path = output_dir / f"qa_region_{index:02d}.png"
            crop_region(image, mapped_box).save(crop_path)
            question = str(qa.get("question") or "")
            question_type = classify_question(question)
            evaluation_view = evaluation_view_for_question(question_type)
            eval_items.append(
                {
                    "index": index,
                    "qa": qa,
                    "question": question,
                    "question_type": question_type,
                    "evaluation_view": evaluation_view,
                    "crop_path": crop_path,
                    "source_box": _box_to_float_dict(box),
                    "mapped_box": _box_to_float_dict(mapped_box),
                    "output_size": output_size,
                }
            )

    predictions = evaluate_qa_batches(client, model, edited_image, metadata, eval_items)
    results: list[QAEvalResult] = []
    for item in eval_items:
        index = item["index"]
        qa = item["qa"]
        prediction, rationale = predictions.get(index, ("", None))
        reference = _normalize_yes_no(qa.get("answer"))
        results.append(
            QAEvalResult(
                index=index,
                question=item["question"],
                reference_answer=reference,
                predicted_answer=prediction,
                correct=bool(reference and prediction and reference == prediction),
                question_type=item["question_type"],
                evaluation_view=item["evaluation_view"],
                crop_path=str(item["crop_path"]),
                full_image_path=str(edited_image) if item["evaluation_view"] in {"full_image", "mixed"} else None,
                source_box=item["source_box"],
                mapped_box=item["mapped_box"],
                output_size=item["output_size"],
                context_risk=item["question_type"] == "unknown",
                rationale=rationale,
            )
        )
    return results


def evaluate_qa_batches(
    client: OpenAICompatClient,
    model: str,
    edited_image: Path,
    metadata: dict[str, Any],
    eval_items: list[dict[str, Any]],
) -> dict[int, tuple[str, str | None]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in eval_items:
        grouped.setdefault(item["evaluation_view"], []).append(item)

    predictions: dict[int, tuple[str, str | None]] = {}
    for view, items in grouped.items():
        if view == "full_image":
            image_paths = [edited_image]
            mapping = "\n".join(
                f"Question {item['index']} uses image 0 (the full edited image)." for item in items
            )
        elif view == "mixed":
            image_paths = [edited_image] + [item["crop_path"] for item in items]
            mapping = "\n".join(
                f"Question {item['index']} uses image 0 as the full image and image {position} as its zoomed crop."
                for position, item in enumerate(items, start=1)
            )
        else:
            image_paths = [item["crop_path"] for item in items]
            mapping = "\n".join(
                f"Question {item['index']} corresponds to image {position}."
                for position, item in enumerate(items)
            )

        if view == "full_image":
            view_instruction = "Answer using the full edited image. Use the whole canvas as the position reference."
        elif view == "mixed":
            view_instruction = "Use the full image for global position and each paired crop for local evidence."
        else:
            view_instruction = "Answer using only the corresponding cropped edited-image region."

        questions = "\n".join(
            f"Question {item['index']}: {item['question']}" for item in items
        )
        user_text = (
            f"{view_instruction}\n"
            f"Edit instruction: {metadata.get('instruction', '')}\n"
            f"Physics law: {metadata.get('physics_law', '')}\n"
            f"{mapping}\n"
            f"{questions}\n"
            "Return one Yes/No answer for every listed question. Do not compare with the original image."
        )
        response = client.chat_json(
            model,
            [
                {"role": "system", "content": PICAEVAL_SYSTEM},
                vision_user_message(user_text, image_paths),
            ],
            max_tokens=max(900, 180 * len(items)),
        )
        answer_map = _answers_by_index(response.get("answers"))
        for item in items:
            answer_obj = answer_map.get(item["index"], {})
            prediction = _normalize_yes_no(answer_obj.get("answer"))
            rationale = answer_obj.get("rationale")
            if not prediction:
                prediction, rationale = evaluate_single_qa(client, model, edited_image, metadata, item)
            predictions[item["index"]] = (prediction, rationale)
    return predictions


def evaluate_single_qa(
    client: OpenAICompatClient,
    model: str,
    edited_image: Path,
    metadata: dict[str, Any],
    item: dict[str, Any],
) -> tuple[str, str | None]:
    view = item["evaluation_view"]
    image_paths = _evaluation_image_paths(edited_image, item["crop_path"], view)
    view_instruction = {
        "crop": "Answer using only the cropped edited-image region.",
        "full_image": "Answer using the full edited image. Use the whole canvas as the position reference.",
        "mixed": "Image 0 is the full edited image. Image 1 is a zoomed crop of the annotated region. Use the full image for global position and the crop for local evidence.",
    }[view]
    user_text = (
        f"{view_instruction}\n"
        f"Edit instruction: {metadata.get('instruction', '')}\n"
        f"Physics law: {metadata.get('physics_law', '')}\n"
        f"Question 0: {item['question']}\n"
        "Return one Yes/No answer for question 0. Do not compare with the original image."
    )
    response = client.chat_json(
        model,
        [
            {"role": "system", "content": PICAEVAL_SYSTEM},
            vision_user_message(user_text, image_paths),
        ],
        max_tokens=500,
    )
    answer_obj = _answers_by_index(response.get("answers")).get(0, {})
    return _normalize_yes_no(answer_obj.get("answer")), answer_obj.get("rationale")


def crop_region(image: Image.Image, box: dict[str, Any] | None) -> Image.Image:
    if not box:
        return image.copy()
    width, height = image.size
    x1 = int(max(0, float(box.get("x", 0))))
    y1 = int(max(0, float(box.get("y", 0))))
    x2 = int(min(width, float(box.get("x", 0)) + float(box.get("width", 0))))
    y2 = int(min(height, float(box.get("y", 0)) + float(box.get("height", 0))))
    if x2 <= x1 or y2 <= y1:
        return image.copy()
    return image.crop((x1, y1, x2, y2))


def compute_non_edit_psnr(
    source_image: Path,
    edited_image: Path,
    edit_areas: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> float | None:
    with Image.open(source_image) as raw_source, Image.open(edited_image) as raw_edited:
        edited = raw_edited.convert("RGB")
        transform = coordinate_transform(metadata or {}, edited.size, raw_source.size)
        source = source_canvas_for_output(raw_source.convert("RGB"), transform, edited.size)
        if not edit_areas:
            mask = Image.new("1", edited.size, 0)
        else:
            mask = Image.new("1", edited.size, 0)
            draw = ImageDraw.Draw(mask)
            for area in edit_areas:
                mapped = source_box_to_output_box(area, transform, edited.size)
                x1 = max(0, float(mapped.get("x", 0)))
                y1 = max(0, float(mapped.get("y", 0)))
                x2 = min(edited.width, x1 + float(mapped.get("width", 0)))
                y2 = min(edited.height, y1 + float(mapped.get("height", 0)))
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


def prepare_canonical_input(
    source_image: Path,
    output_image: Path,
    transform_path: Path | None = None,
    canonical_size: tuple[int, int] = CANONICAL_SIZE,
) -> dict[str, Any]:
    with Image.open(source_image) as raw_image:
        image = raw_image.convert("RGB")
        transform = contain_transform(image.size, canonical_size)
        canonical = render_canonical_canvas(image, transform)
        output_image.parent.mkdir(parents=True, exist_ok=True)
        canonical.save(output_image, format="PNG")
    if transform_path:
        transform_path.parent.mkdir(parents=True, exist_ok=True)
        transform_path.write_text(json.dumps(transform, ensure_ascii=False, indent=2), encoding="utf-8")
    return transform


def contain_transform(source_size: tuple[int, int], canonical_size: tuple[int, int] = CANONICAL_SIZE) -> dict[str, Any]:
    source_width, source_height = source_size
    canvas_width, canvas_height = canonical_size
    scale = min(canvas_width / source_width, canvas_height / source_height)
    scaled_width = int(round(source_width * scale))
    scaled_height = int(round(source_height * scale))
    pad_x = (canvas_width - scaled_width) / 2
    pad_y = (canvas_height - scaled_height) / 2
    return {
        "source_size": [source_width, source_height],
        "canonical_size": [canvas_width, canvas_height],
        "mode": "contain",
        "scale": scale,
        "pad_x": pad_x,
        "pad_y": pad_y,
        "scaled_size": [scaled_width, scaled_height],
    }


def render_canonical_canvas(image: Image.Image, transform: dict[str, Any]) -> Image.Image:
    canvas_width, canvas_height = _pair(transform["canonical_size"])
    scaled_width, scaled_height = _pair(transform["scaled_size"])
    pad_x = int(round(float(transform["pad_x"])))
    pad_y = int(round(float(transform["pad_y"])))
    resized = image.resize((scaled_width, scaled_height), Image.Resampling.BICUBIC)
    canvas = Image.new("RGB", (canvas_width, canvas_height), (0, 0, 0))
    canvas.paste(resized, (pad_x, pad_y))
    return canvas


def coordinate_transform(
    metadata: dict[str, Any],
    output_size: tuple[int, int],
    fallback_source_size: tuple[int, int] | None = None,
) -> dict[str, Any]:
    transform = metadata.get("coordinate_transform") or metadata.get("_coord_transform")
    if isinstance(transform, dict):
        return transform
    source_size = _metadata_image_size(metadata) or fallback_source_size or output_size
    return identity_transform(source_size)


def identity_transform(source_size: tuple[int, int]) -> dict[str, Any]:
    source_width, source_height = source_size
    return {
        "source_size": [source_width, source_height],
        "canonical_size": [source_width, source_height],
        "mode": "identity",
        "scale": 1.0,
        "pad_x": 0.0,
        "pad_y": 0.0,
        "scaled_size": [source_width, source_height],
    }


def source_box_to_output_box(
    box: dict[str, Any],
    transform: dict[str, Any],
    output_size: tuple[int, int],
) -> dict[str, float]:
    canonical = source_box_to_canonical_box(box, transform)
    return canonical_box_to_output_box(canonical, transform, output_size)


def source_box_to_canonical_box(box: dict[str, Any], transform: dict[str, Any]) -> dict[str, float]:
    scale = float(transform["scale"])
    pad_x = float(transform["pad_x"])
    pad_y = float(transform["pad_y"])
    return {
        "x": float(box.get("x", 0)) * scale + pad_x,
        "y": float(box.get("y", 0)) * scale + pad_y,
        "width": float(box.get("width", 0)) * scale,
        "height": float(box.get("height", 0)) * scale,
    }


def canonical_box_to_output_box(
    box: dict[str, Any],
    transform: dict[str, Any],
    output_size: tuple[int, int],
) -> dict[str, float]:
    canonical_width, canonical_height = _pair(transform["canonical_size"])
    output_width, output_height = output_size
    scale_x = output_width / canonical_width
    scale_y = output_height / canonical_height
    return {
        "x": float(box.get("x", 0)) * scale_x,
        "y": float(box.get("y", 0)) * scale_y,
        "width": float(box.get("width", 0)) * scale_x,
        "height": float(box.get("height", 0)) * scale_y,
    }


def source_canvas_for_output(
    source: Image.Image,
    transform: dict[str, Any],
    output_size: tuple[int, int],
) -> Image.Image:
    canonical_size = _pair(transform["canonical_size"])
    if source.size == canonical_size:
        canvas = source
    else:
        canvas = render_canonical_canvas(source, transform)
    if canvas.size != output_size:
        canvas = canvas.resize(output_size, Image.Resampling.BICUBIC)
    return canvas


def classify_question(question: str) -> str:
    text = question.casefold()
    global_terms = {
        "left",
        "right",
        "upper",
        "lower",
        "top",
        "bottom",
        "center",
        "corner",
        "foreground",
        "background",
        "perspective",
        "aligned",
        "distant",
        "between",
        "beside",
        "behind",
        "in front",
        "frame",
    }
    local_terms = {
        "shadow",
        "reflection",
        "refraction",
        "contact",
        "wet",
        "dry",
        "melt",
        "frozen",
        "broken",
        "texture",
        "highlight",
        "caustic",
        "occlusion",
        "waterline",
        "ripple",
        "ripples",
        "edge",
        "surface",
        "continuous",
    }
    has_global = any(_contains_term(text, term) for term in global_terms)
    has_local = any(_contains_term(text, term) for term in local_terms)
    if has_global and has_local:
        return "mixed"
    if has_global:
        return "global_position"
    if has_local:
        return "local_appearance"
    return "unknown"


def _contains_term(text: str, term: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
    return bool(re.search(pattern, text))


def evaluation_view_for_question(question_type: str) -> str:
    if question_type == "global_position":
        return "full_image"
    if question_type == "mixed":
        return "mixed"
    return "crop"


def _evaluation_image_paths(edited_image: Path, crop_path: Path, view: str) -> list[Path]:
    if view == "full_image":
        return [edited_image]
    if view == "mixed":
        return [edited_image, crop_path]
    return [crop_path]


def write_unpadded_output(
    edited_image: Path,
    output_image: Path,
    transform: dict[str, Any],
    resize_to_source: bool = True,
) -> Path:
    with Image.open(edited_image) as raw_image:
        image = raw_image.convert("RGB")
        pad_x = float(transform.get("pad_x", 0.0))
        pad_y = float(transform.get("pad_y", 0.0))
        scaled_width, scaled_height = _pair(transform.get("scaled_size", image.size))
        canonical_width, canonical_height = _pair(transform.get("canonical_size", image.size))
        output_width, output_height = image.size
        scale_x = output_width / canonical_width
        scale_y = output_height / canonical_height
        x1 = int(round(pad_x * scale_x))
        y1 = int(round(pad_y * scale_y))
        x2 = int(round((pad_x + scaled_width) * scale_x))
        y2 = int(round((pad_y + scaled_height) * scale_y))
        crop = image.crop((max(0, x1), max(0, y1), min(output_width, x2), min(output_height, y2)))
        if resize_to_source:
            source_width, source_height = _pair(transform.get("source_size", crop.size))
            if crop.size != (source_width, source_height):
                crop = crop.resize((source_width, source_height), Image.Resampling.BICUBIC)
        output_image.parent.mkdir(parents=True, exist_ok=True)
        crop.save(output_image, format="PNG")
    return output_image


def _metadata_image_size(metadata: dict[str, Any]) -> tuple[int, int] | None:
    size = metadata.get("input_image_size") or {}
    width = size.get("width")
    height = size.get("height")
    if width and height:
        return int(width), int(height)
    return None


def _box_to_float_dict(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    return {
        "x": float(value.get("x", 0)),
        "y": float(value.get("y", 0)),
        "width": float(value.get("width", 0)),
        "height": float(value.get("height", 0)),
    }


def _pair(value: Any) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return int(value[0]), int(value[1])
    raise ValueError(f"Expected size pair, got {value!r}")


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

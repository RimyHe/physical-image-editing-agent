from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

from PIL import Image


DATASET = "Andrew613/PICABench"
CONFIG = "default"
SPLIT = "picabench"
ROWS_URL = "https://datasets-server.huggingface.co/rows"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Download a small runnable PICABench subset as PNG inputs plus metadata."
    )
    parser.add_argument("--output-root", type=Path, default=Path("data/picabench_examples"))
    parser.add_argument("--count", type=int, default=6, help="Number of examples to save.")
    parser.add_argument("--offset", type=int, default=0, help="Starting row offset in the PICABench split.")
    parser.add_argument(
        "--row-idx",
        type=int,
        action="append",
        dest="row_indices",
        help="Download an exact PICABench row. Repeat to build a fixed subset.",
    )
    parser.add_argument("--scan-limit", type=int, default=160, help="Maximum rows to inspect while filtering.")
    parser.add_argument("--batch-size", type=int, default=8, help="Rows fetched per datasets-server request.")
    parser.add_argument("--retries", type=int, default=3, help="Retries for transient Hugging Face errors.")
    parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        help="Optional physics_category filter. Repeat for multiple categories.",
    )
    parser.add_argument(
        "--prompt-field",
        choices=["explicit_prompt", "intermediate_prompt", "superficial_prompt"],
        default="explicit_prompt",
        help="Prompt field to write as the runnable instruction.",
    )
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be positive")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    wanted_categories = {c.casefold() for c in args.categories or []}

    if args.row_indices:
        selected = fetch_row_indices(args.row_indices, args.batch_size, args.timeout, args.retries)
        filtered = []
        for item in selected:
            row = item["row"]
            if wanted_categories and row.get("physics_category", "").casefold() not in wanted_categories:
                continue
            filtered.append(item)
        selected = filtered
    else:
        selected = []
        inspected = 0
        offset = args.offset
        while len(selected) < args.count and inspected < args.scan_limit:
            length = min(args.batch_size, args.scan_limit - inspected)
            rows = fetch_rows(offset, length, args.timeout, args.retries)
            if not rows:
                break
            for wrapped in rows:
                row_index = int(wrapped["row_idx"])
                row = wrapped["row"]
                inspected += 1
                if wanted_categories and row.get("physics_category", "").casefold() not in wanted_categories:
                    continue
                selected.append({"row_idx": row_index, "row": row})
                if len(selected) >= args.count:
                    break
            offset += len(rows)

    if not selected:
        raise SystemExit("No matching PICABench rows found.")

    cases = []
    for item in selected:
        row_idx = item["row_idx"]
        row = item["row"]
        case_id = f"picabench_{row_idx:04d}_{slug(row.get('physics_law') or row.get('physics_category') or 'case')}"
        case_dir = output_root / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        image_info = row.get("input_image") or {}
        image_url = image_info.get("src")
        if not image_url:
            raise RuntimeError(f"Row {row_idx} has no input_image.src")

        input_png = case_dir / "input.png"
        if not input_png.exists():
            image_bytes = fetch_bytes(image_url, args.timeout, args.retries)
            with Image.open(BytesIO(image_bytes)) as img:
                img.convert("RGB").save(input_png, format="PNG")
            time.sleep(0.2)

        instruction = row.get(args.prompt_field) or row.get("explicit_prompt") or row.get("superficial_prompt") or ""
        metadata = {
            "case_id": case_id,
            "dataset": DATASET,
            "config": CONFIG,
            "split": SPLIT,
            "row_idx": row_idx,
            "physics_category": row.get("physics_category"),
            "physics_law": row.get("physics_law"),
            "edit_operation": row.get("edit_operation"),
            "instruction": instruction,
            "prompt_field": args.prompt_field,
            "prompts": {
                "superficial": row.get("superficial_prompt"),
                "intermediate": row.get("intermediate_prompt"),
                "explicit": row.get("explicit_prompt"),
            },
            "image_path": row.get("image_path"),
            "input_png": str(input_png),
            "input_image_size": {
                "width": image_info.get("width"),
                "height": image_info.get("height"),
            },
            "edit_area": row.get("edit_area"),
            "annotated_qa_pairs": row.get("annotated_qa_pairs"),
        }
        metadata_path = case_dir / "metadata.json"
        if not metadata_path.exists():
            write_json(metadata_path, metadata)
        cases.append(metadata)

    manifest = {
        "dataset": DATASET,
        "config": CONFIG,
        "split": SPLIT,
        "source": f"https://huggingface.co/datasets/{DATASET}",
        "count": len(cases),
        "prompt_field": args.prompt_field,
        "cases": cases,
    }
    write_json(output_root / "manifest.json", manifest)
    print(f"Saved {len(cases)} PICABench examples to {output_root}")
    for case in cases:
        print(f"{case['case_id']}: {case['instruction']}")
    return 0


def fetch_rows(offset: int, length: int, timeout: int, retries: int) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "dataset": DATASET,
            "config": CONFIG,
            "split": SPLIT,
            "offset": offset,
            "length": length,
        }
    )
    payload = fetch_json(f"{ROWS_URL}?{query}", timeout, retries)
    return payload.get("rows") or []


def fetch_row_indices(row_indices: list[int], batch_size: int, timeout: int, retries: int) -> list[dict[str, Any]]:
    wanted = list(dict.fromkeys(int(index) for index in row_indices))
    if not wanted:
        return []
    by_index: dict[int, dict[str, Any]] = {}
    start = min(wanted)
    end = max(wanted)
    offset = start
    while offset <= end:
        length = min(max(batch_size, 1), end - offset + 1)
        for wrapped in fetch_rows(offset, length, timeout, retries):
            by_index[int(wrapped["row_idx"])] = {"row_idx": int(wrapped["row_idx"]), "row": wrapped["row"]}
        offset += length
        time.sleep(0.2)
    missing = [index for index in wanted if index not in by_index]
    if missing:
        raise RuntimeError(f"PICABench rows were not returned: {missing}")
    return [by_index[index] for index in wanted]


def fetch_json(url: str, timeout: int, retries: int) -> dict[str, Any]:
    return json.loads(fetch_bytes(url, timeout, retries).decode("utf-8"))


def fetch_bytes(url: str, timeout: int, retries: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "physical-image-editing-agent/0.1"})
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 - show the final upstream error after retries.
            last_error = exc
            if attempt >= retries:
                break
            if isinstance(exc, HTTPError) and exc.code == 429:
                time.sleep(10 * (attempt + 1))
            else:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}") from last_error


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return text.strip("_") or "case"


if __name__ == "__main__":
    raise SystemExit(main())

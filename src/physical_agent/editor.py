from __future__ import annotations

from pathlib import Path

from .image_io import ensure_valid_png, write_b64_image
from .openai_compat import OpenAICompatClient


def execute_edit(
    client: OpenAICompatClient,
    model: str,
    source_image: Path,
    edit_prompt: str,
    output_path: Path,
) -> Path:
    ensure_valid_png(source_image)
    b64_json = client.edit_image(model, source_image, edit_prompt)
    write_b64_image(b64_json, output_path)
    ensure_valid_png(output_path)
    return output_path

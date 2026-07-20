from __future__ import annotations

from pathlib import Path
from typing import Any

from .openai_compat import OpenAICompatClient, vision_user_message


PLANNER_SYSTEM = """You are the Planner in a physical-consistency image editing agent.
Return strict JSON only. Plan the edit, identify physical dependencies, and write an executable image-edit prompt.
JSON keys: target, operation, preserve, physics_dependencies, route, edit_prompt, verifier_focus.
Use route "direct_edit" unless a local mask/tool is required."""


def plan_edit(
    client: OpenAICompatClient,
    model: str,
    image_path: Path,
    instruction: str,
    previous_failure: str | None = None,
) -> dict[str, Any]:
    repair_context = f"\nPrevious verifier failure to address: {previous_failure}" if previous_failure else ""
    user_text = (
        "Create a concise plan for this image edit.\n"
        f"User instruction: {instruction}{repair_context}\n"
        "The edit prompt must explicitly mention physical consistency such as shadows, reflections, occlusion, contact, lighting, and perspective when relevant."
    )
    return client.chat_json(
        model,
        [
            {"role": "system", "content": PLANNER_SYSTEM},
            vision_user_message(user_text, [image_path]),
        ],
    )

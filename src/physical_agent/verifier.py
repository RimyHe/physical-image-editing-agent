from __future__ import annotations

from pathlib import Path
from typing import Any

from .openai_compat import OpenAICompatClient, vision_user_message


VERIFIER_SYSTEM = """You are the Verifier in a physical-consistency image editing agent.
Compare the original image and candidate image against the plan and user instruction.
Return strict JSON only with keys: pass, instruction_score, preservation_score, physics_score, issues, repair_instruction, rationale.
Scores are integers from 0 to 10. pass is true only when the edit follows the instruction and physical consistency is acceptable."""


def verify_edit(
    client: OpenAICompatClient,
    model: str,
    original_image: Path,
    candidate_image: Path,
    instruction: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    user_text = (
        "Original image is first; candidate edited image is second.\n"
        f"User instruction: {instruction}\n"
        f"Plan JSON: {plan}\n"
        "Check target edit, preserved content, shadows/reflections/occlusion/contact/lighting/perspective, and visible artifacts."
    )
    result = client.chat_json(
        model,
        [
            {"role": "system", "content": VERIFIER_SYSTEM},
            vision_user_message(user_text, [original_image, candidate_image]),
        ],
    )
    result["pass"] = bool(result.get("pass"))
    return result

from __future__ import annotations

from pathlib import Path
from typing import Any

from .openai_compat import OpenAICompatClient
from .physical_intent import PhysicalIntentExpander, render_edit_prompt


def plan_edit(
    client: OpenAICompatClient,
    model: str,
    image_path: Path,
    instruction: str,
    previous_failure: str | None = None,
) -> dict[str, Any]:
    """Expand the user request and expose a backward-compatible planner result."""
    expander = PhysicalIntentExpander(client, model)
    task_profile = expander.expand(
        image_path=image_path,
        instruction=instruction,
        previous_failure=previous_failure,
    )
    return {
        "target": task_profile.get("affected_objects", []),
        "operation": task_profile.get("physical_operation", ""),
        "preserve": task_profile.get("preserve_scope", []),
        "physics_dependencies": task_profile.get("physical_dependencies", []),
        "route": "direct_edit",
        "edit_prompt": render_edit_prompt(task_profile, instruction),
        "verifier_focus": task_profile.get("must_pass_checks", []),
        "task_profile": task_profile,
    }
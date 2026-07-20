from __future__ import annotations

from typing import Any


def select_route(plan: dict[str, Any]) -> dict[str, str]:
    requested = str(plan.get("route", "direct_edit")).lower()
    if requested not in {"direct_edit", "local_edit"}:
        requested = "direct_edit"
    if requested == "local_edit":
        return {
            "route": "direct_edit",
            "reason": "MVP has no mask/local CV tool yet; falling back to whole-image edit.",
        }
    return {"route": "direct_edit", "reason": "Use verified gpt-image-2 image edit endpoint."}

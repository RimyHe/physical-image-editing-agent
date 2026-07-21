from __future__ import annotations

from pathlib import Path
from typing import Any

from .openai_compat import OpenAICompatClient, vision_user_message


VERIFIER_SYSTEM = """You are the Verifier in a physical-consistency image editing agent.
Compare the original image and candidate image against the plan and user instruction.
Return strict JSON only with keys: pass, instruction_score, preservation_score, physics_score, check_results, blocking_failures, issues, repair_instruction, route_hints, rationale.
Scores are integers from 0 to 10. check_results is a list of objects with keys check, pass, severity, evidence.
blocking_failures and route_hints are lists of strings. pass is true only when the edit follows the instruction, all required checks pass, and physical consistency is acceptable."""


def verify_edit(
    client: OpenAICompatClient,
    model: str,
    original_image: Path,
    candidate_image: Path,
    instruction: str,
    plan: dict[str, Any],
    route: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = _profile_from_plan(plan, metadata)
    required_checks = _required_checks(profile, route)
    view_protocol = (
        "Use the full candidate image for global position, perspective, and frame-location checks. "
        "Use local visual evidence for shadows, reflections, contact, material state, refraction, and artifacts. "
        "If the task references PICABench crops, assume boxes have been mapped through the canonical coordinate protocol."
    )
    user_text = (
        "Original image is first; candidate edited image is second.\n"
        f"User instruction: {instruction}\n"
        f"Plan JSON: {plan}\n"
        f"Route decision: {route or {}}\n"
        f"Task profile: {profile}\n"
        f"Required must-pass checks: {required_checks}\n"
        f"Evaluation view protocol: {view_protocol}\n"
        "Evaluate every required check explicitly. Mark a blocking failure if any required physical consequence is missing, "
        "even when the visible target edit is partially correct. For Causality remove/support tasks, do not pass if the support "
        "is removed but the affected object remains in its old stable pose. For Reflection add/move tasks, do not pass if the "
        "object is visible but the reflection is missing or misaligned. For Light_Propagation move/add/remove tasks, do not pass "
        "if the new cast/contact shadow is missing, remains at the old position, or conflicts with reference shadows."
    )
    result = client.chat_json(
        model,
        [
            {"role": "system", "content": VERIFIER_SYSTEM},
            vision_user_message(user_text, [original_image, candidate_image]),
        ],
        max_tokens=1400,
    )
    return normalize_verification_result(result, required_checks)


def normalize_verification_result(result: dict[str, Any], required_checks: list[str]) -> dict[str, Any]:
    check_results = result.get("check_results")
    if not isinstance(check_results, list):
        check_results = []
    blocking_failures = result.get("blocking_failures")
    if not isinstance(blocking_failures, list):
        blocking_failures = []
    failed_required = []
    for item in check_results:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "")).lower()
        if item.get("pass") is False and severity in {"required", "blocking", "critical"}:
            failed_required.append(str(item.get("check") or "required check failed"))
    if failed_required:
        blocking_failures.extend(failed_required)
    for key in ["instruction_score", "preservation_score", "physics_score"]:
        try:
            result[key] = int(result.get(key, 0))
        except (TypeError, ValueError):
            result[key] = 0
    result["check_results"] = check_results
    result["blocking_failures"] = list(dict.fromkeys(str(item) for item in blocking_failures if item))
    result["issues"] = result.get("issues") if isinstance(result.get("issues"), list) else []
    result["route_hints"] = result.get("route_hints") if isinstance(result.get("route_hints"), list) else []
    result["required_checks"] = required_checks
    result["pass"] = bool(result.get("pass")) and not result["blocking_failures"]
    return result


def _profile_from_plan(plan: dict[str, Any], metadata: dict[str, Any] | None) -> dict[str, Any]:
    metadata = metadata or {}
    return {
        "physics_category": plan.get("physics_category") or metadata.get("physics_category"),
        "physics_law": plan.get("physics_law") or metadata.get("physics_law"),
        "edit_operation": plan.get("operation") or plan.get("edit_operation") or metadata.get("edit_operation"),
        "physical_operation": plan.get("physical_operation"),
        "target": plan.get("target"),
        "preserve": plan.get("preserve"),
        "physics_dependencies": plan.get("physics_dependencies"),
        "verifier_focus": plan.get("verifier_focus"),
        "must_pass_checks": plan.get("must_pass_checks"),
    }


def _required_checks(profile: dict[str, Any], route: dict[str, Any] | None) -> list[str]:
    checks: list[str] = []
    law = str(profile.get("physics_law") or "").casefold()
    operation = str(profile.get("edit_operation") or "").casefold()
    checks.extend(_as_string_list(profile.get("must_pass_checks")))
    checks.extend(_as_string_list((route or {}).get("verification_focus")))
    if "reflection" in law:
        if operation in {"add", "move"}:
            checks.extend(
                [
                    "target object is visible at the intended location",
                    "reflection is visible on the reflective surface",
                    "reflection aligns with the target object and reflective surface",
                    "contact line, waterline, highlight, or ripple is physically consistent when relevant",
                ]
            )
        elif operation == "remove":
            checks.extend(
                [
                    "removed target is absent",
                    "target reflection/highlight is also removed",
                    "reflective surface is reconstructed without artifacts",
                ]
            )
    elif "light_propagation" in law or "light propagation" in law:
        checks.extend(
            [
                "target edit is completed at the intended location",
                "old cast/contact shadow is removed or updated",
                "new cast/contact shadow is visible when physically required",
                "shadow direction, softness, and placement match reference lighting",
            ]
        )
    elif "causality" in law:
        checks.extend(
            [
                "intervention target is changed or removed as instructed",
                "affected objects show the predicted final stable state",
                "new contact points, occlusion, and contact shadows are physically consistent",
            ]
        )
    elif "local" == law:
        checks.extend(
            [
                "local state change is visible in the target region",
                "state change respects material boundaries",
                "unrelated regions are preserved",
            ]
        )
    elif "global" == law:
        checks.extend(
            [
                "global state change is applied consistently across the scene",
                "scene structure and object identities are preserved where required",
            ]
        )
    return list(dict.fromkeys(check for check in checks if check))


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []

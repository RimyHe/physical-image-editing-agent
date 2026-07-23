from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .openai_compat import OpenAICompatClient, vision_user_message


TASK_PROFILE_SYSTEM = """You are the PhysicalIntentExpander in a physical-consistency image editing agent.
Return strict JSON only. Convert a short image-editing instruction and image evidence into a TaskProfile.

Required top-level JSON keys:
physical_operation, final_state, affected_objects, physical_dependencies, dependent_regions,
preserve_scope, reference_cues, uncertainties, must_pass_checks.

Field requirements:
- physical_operation: the intervention rewritten as a physical state transition, not just a visual verb.
- final_state: an object describing the intended final stable scene state, including pose, support, contact, material, or lighting changes when relevant.
- affected_objects: objects changed directly or indirectly by the intervention.
- physical_dependencies: observable effects that must be updated, such as shadow, reflection, refraction, occlusion, contact, support, lighting, or material state.
- dependent_regions: image regions that need coordinated editing beyond the target object, such as a cast-shadow area, reflective surface, contact patch, or background reconstruction area.
- preserve_scope: objects and regions that should remain unchanged.
- reference_cues: visible evidence in the input image that constrains the edit, such as light direction, surface plane, perspective, material boundary, or nearby reference shadow.
- uncertainties: details that cannot be established confidently from the image or instruction. Do not silently invent them.
- must_pass_checks: observable checks that follow from the final state and can be given to a verifier.

Rules:
- Use the image as evidence. Do not treat an imagined or hidden physical state as certain.
- Expand the instruction, but do not add unsupported objects, events, or stylistic changes.
- For removal or support changes, describe the affected objects and their final stable state.
- For reflection, shadow, or refraction edits, represent the subject, dependent surface, and coupled visual effect separately.
- Keep preserve_scope narrow and relevant to the requested edit.
- Use empty lists or explicit uncertainty instead of guessing.
- Follow the policy scaffold as a checklist, not as evidence that a physical effect is present.
"""


BASE_POLICY_SCAFFOLD = {
    "evidence_policy": "Only assert visual facts supported by the input image or the user instruction.",
    "state_policy": "Describe the intended final stable state, not only the requested intervention.",
    "dependency_policy": "Include coupled visual effects when the edit changes support, contact, lighting, reflection, shadow, refraction, occlusion, or material state.",
    "preservation_policy": "Protect unrelated objects, background regions, camera perspective, and material appearance.",
    "uncertainty_policy": "Record uncertain or unverifiable details instead of inventing them.",
}


CATEGORY_SCAFFOLDS = {
    "optics": {
        "physics_focus": ["light direction", "shadow or reflection geometry", "material appearance", "occlusion boundaries"],
        "required_checks": ["coupled optical effects are updated in the dependent region", "lighting and material appearance remain coherent"],
    },
    "mechanics": {
        "physics_focus": ["support", "contact points", "gravity", "stable pose", "occlusion from changed pose"],
        "required_checks": ["affected objects reach a plausible final stable state", "new or removed contacts and contact shadows are consistent"],
    },
    "state": {
        "physics_focus": ["state boundary", "material appearance", "localization", "unchanged surrounding context"],
        "required_checks": ["the requested state change is localized", "unrelated regions and material boundaries are preserved"],
    },
}

LAW_SCAFFOLDS = {
    "reflection": {
        "physics_focus": ["subject -> reflective surface -> reflected subject", "reflection position, orientation, scale, and softness", "reflection/contact line or waterline"],
        "required_checks": ["the subject and its reflection are jointly updated", "the reflective surface is reconstructed without unrelated changes"],
        "avoid": ["adding a generic realistic reflection without identifying its surface or correspondence"],
    },
    "light_propagation": {
        "physics_focus": ["light direction", "old cast/contact shadow", "new shadow on the receiving surface", "softness and distance falloff"],
        "required_checks": ["old shadow is removed when the object moves", "new shadow direction and softness match visible reference shadows"],
        "avoid": ["copying a sharp object silhouette as the shadow", "inventing a light source not supported by the scene"],
    },
    "refraction": {
        "physics_focus": ["transparent medium", "internal liquid or air state", "distorted background", "glass/reflection artifacts"],
        "required_checks": ["medium-specific distortion is updated", "glass geometry and surrounding scene are preserved"],
        "avoid": ["describing generic blur instead of the medium-dependent optical change"],
    },
    "causality": {
        "physics_focus": ["intervention target", "affected objects", "support loss or force change", "final stable pose", "new contacts and shadows"],
        "required_checks": ["the affected object does not remain in an impossible old pose", "support/contact relationships match the final state"],
        "avoid": ["describing only removal of the cause while leaving the consequence unchanged"],
    },
}

OPERATION_SCAFFOLDS = {
    "remove": {"operation_focus": ["remove the target and repair all necessary dependent regions"]},
    "add": {"operation_focus": ["add the target with correct placement, contact, occlusion, and dependent effects"]},
    "move": {"operation_focus": ["remove old-position effects and create new-position effects"]},
    "replace": {"operation_focus": ["preserve the scene role while changing the target state or appearance"]},
    "deform": {"operation_focus": ["preserve material continuity while changing geometry or pose"]},
    "wet": {"operation_focus": ["localize wetness, liquid, gloss, darkening, and contact effects to the relevant surface"]},
}


def build_policy_scaffold(
    instruction: str = "",
    task_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    labels = task_labels or infer_task_labels(instruction)
    category = normalize_label(labels.get("physics_category"))
    law = normalize_label(labels.get("physics_law"))
    operation = normalize_label(labels.get("edit_operation"))
    scaffold: dict[str, Any] = dict(BASE_POLICY_SCAFFOLD)
    scaffold.update(
        {
            "physics_category": category or "unknown",
            "physics_law": law or "unknown",
            "edit_operation": operation or "unknown",
            "physics_focus": [],
            "required_checks": [],
            "operation_focus": [],
            "avoid": [],
        }
    )
    if category in CATEGORY_SCAFFOLDS:
        merge_scaffold(scaffold, CATEGORY_SCAFFOLDS[category])
    if law in LAW_SCAFFOLDS:
        merge_scaffold(scaffold, LAW_SCAFFOLDS[law])
    if operation in OPERATION_SCAFFOLDS:
        merge_scaffold(scaffold, OPERATION_SCAFFOLDS[operation])
    return scaffold


def infer_task_labels(instruction: str) -> dict[str, str]:
    text = instruction.casefold()
    operation = first_match(text, {
        "remove": ["remove", "erase", "delete", "eliminate"],
        "add": ["add", "insert", "place", "introduce"],
        "move": ["move", "reposition", "relocate", "shift"],
        "replace": ["replace", "swap", "change into"],
        "deform": ["bend", "deform", "collapse", "topple", "tilt", "knock over"],
        "wet": ["wet", "spill", "melt", "moisten", "water"],
    })
    law = first_match(text, {
        "reflection": ["reflection", "reflected", "mirror", "glossy", "reflective"],
        "refraction": ["refraction", "refract", "distort through glass", "waterline", "caustic"],
        "light_propagation": ["shadow", "cast shadow", "contact shadow", "light direction", "illumination"],
        "causality": ["support", "supported", "gravity", "fall", "fallen", "stable", "resting", "contact"],
    })
    if law in {"reflection", "refraction", "light_propagation"}:
        category = "optics"
    elif law == "causality":
        category = "mechanics"
    elif operation in {"wet", "deform", "replace"}:
        category = "state"
    else:
        category = "unknown"
    return {"physics_category": category, "physics_law": law, "edit_operation": operation}


def first_match(text: str, candidates: dict[str, list[str]]) -> str:
    for label, keywords in candidates.items():
        if any(keyword in text for keyword in keywords):
            return label
    return ""


def normalize_label(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").casefold()).strip("_")


def merge_scaffold(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, list):
            target[key] = list(dict.fromkeys([*target.get(key, []), *value]))
        else:
            target[key] = value


def validate_task_profile(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "physical_operation": str,
        "final_state": dict,
        "affected_objects": list,
        "physical_dependencies": list,
        "dependent_regions": list,
        "preserve_scope": list,
        "reference_cues": list,
        "uncertainties": list,
        "must_pass_checks": list,
    }
    for key, expected_type in required.items():
        if key not in profile:
            errors.append(f"missing:{key}")
        elif not isinstance(profile[key], expected_type):
            errors.append(f"type:{key}:{expected_type.__name__}")
    if isinstance(profile.get("final_state"), dict) and not profile["final_state"]:
        errors.append("empty:final_state")
    if isinstance(profile.get("must_pass_checks"), list) and not profile["must_pass_checks"]:
        errors.append("empty:must_pass_checks")
    return errors


def render_edit_prompt(profile: dict[str, Any], user_instruction: str) -> str:
    final_state = profile.get("final_state") or {}
    sections = [
        "Edit the input image according to the following physically grounded task.",
        f"Original instruction: {user_instruction}",
        f"Physical operation: {profile.get('physical_operation', '')}",
        f"Intended final stable state: {final_state}",
        f"Affected objects: {profile.get('affected_objects', [])}",
        f"Physical dependencies to update consistently: {profile.get('physical_dependencies', [])}",
        f"Dependent regions to edit when needed: {profile.get('dependent_regions', [])}",
        f"Preserve unchanged: {profile.get('preserve_scope', [])}",
        f"Reference cues: {profile.get('reference_cues', [])}",
        "Do not invent unsupported objects or changes. Keep the edit limited to the requested target and its necessary dependent regions.",
    ]
    return "\n".join(sections)


class PhysicalIntentExpander:
    def __init__(self, client: OpenAICompatClient, model: str):
        self.client = client
        self.model = model

    def expand(
        self,
        image_path: Path,
        instruction: str,
        previous_failure: str | None = None,
        policy_scaffold: dict[str, Any] | None = None,
        task_labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        repair_context = f"\nPrevious verifier failure to address: {previous_failure}" if previous_failure else ""
        scaffold = policy_scaffold or build_policy_scaffold(instruction, task_labels)
        user_text = (
            "Create a TaskProfile for the image edit.\n"
            f"User instruction: {instruction}{repair_context}\n"
            f"Policy scaffold: {scaffold}\n"
            "Return only the required JSON object."
        )
        profile = self.client.chat_json(
            self.model,
            [
                {"role": "system", "content": TASK_PROFILE_SYSTEM},
                vision_user_message(user_text, [image_path]),
            ],
        )
        profile["policy_scaffold"] = scaffold
        profile["validation_errors"] = validate_task_profile(profile)
        return profile
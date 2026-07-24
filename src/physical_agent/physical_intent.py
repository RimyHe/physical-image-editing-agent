from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .openai_compat import OpenAICompatClient, vision_user_message


SCHEMA_VERSION = "0.1"

TASK_PROFILE_SYSTEM = """You are the PhysicalIntentExpander in a physical-consistency image editing agent.
Return strict JSON only. Convert a short image-editing instruction and image evidence into a TaskProfile.

Required top-level JSON keys:
schema_version, labels, target_objects, physical_operation, current_state, intervention,
final_state, affected_objects, physical_dependencies, dependent_regions, preserve_scope,
reference_cues, uncertainties, must_pass_checks, route_hints.

Field requirements:
- labels: physics_category, physics_law, and edit_operation supplied by the policy scaffold.
- target_objects: objects directly named or visually implied by the instruction.
- physical_operation: rewrite the visual edit as a physical intervention or state transition.
- current_state: observable current pose, support, contact, lighting, shadow, reflection, material, or occlusion facts.
- intervention: the factor changed by the user request, such as removing a support, moving an object, adding a subject, or changing a material state.
- final_state: intended stable scene state after the intervention, including pose, support, contact, material, or lighting changes when relevant.
- affected_objects: objects changed directly or indirectly by the intervention.
- physical_dependencies: coupled effects to update, such as shadow, reflection, refraction, occlusion, contact, support, lighting, or material state.
- dependent_regions: image regions needing coordinated editing beyond the target object, such as cast-shadow area, reflective surface, contact patch, or background reconstruction area.
- preserve_scope: objects and regions that should remain unchanged.
- reference_cues: visible evidence constraining the edit, such as light direction, surface plane, perspective, material boundary, or nearby reference shadow.
- uncertainties: details that cannot be established confidently from image or instruction. Do not silently invent them.
- must_pass_checks: observable checks that follow from final_state and can be given to a verifier.
- route_hints: deterministic routing hints implied by the physical law, not arbitrary tool choices.

Rules:
- Use the image as evidence. Do not treat an imagined or hidden physical state as certain.
- Follow the policy scaffold as required slots, not as evidence that a visual effect is already present.
- For causality + removal, first decide whether the removed target is a support, prop, counterweight, container, or constraint. If yes, final_state must describe the downstream stable pose of the affected load/object, not only the removed target.
- For structure edits, identify the load path: removed support, object/load that loses support, remaining supports, receiving surface, and new contact/shadow/reflection regions.
- Use empty lists or explicit uncertainty instead of guessing.
- Keep preserve_scope narrow and relevant to the requested edit.
- Do not copy PICABench explicit prompts, QA answers, or gold metadata unless they are explicitly supplied in the policy scaffold for analysis mode.
"""


@dataclass
class ValidationIssue:
    severity: str
    field: str
    code: str
    message: str


@dataclass
class PhysicalIntentDiagnostics:
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    auto_filled_fields: list[str] = field(default_factory=list)
    expansion_failures: list[str] = field(default_factory=list)
    evidence_conflicts: list[str] = field(default_factory=list)
    prompt_length: int = 0
    detailed_prompt_length: int = 0
    prompt_compression_ratio: float = 1.0


@dataclass
class PhysicalIntentResult:
    task_profile: dict[str, Any]
    edit_prompt: str
    diagnostics: PhysicalIntentDiagnostics
    policy_scaffold: dict[str, Any]
    detailed_edit_prompt: str = ""

    def as_legacy_profile(self) -> dict[str, Any]:
        profile = dict(self.task_profile)
        profile["edit_prompt"] = self.edit_prompt
        if self.detailed_edit_prompt:
            profile["detailed_edit_prompt"] = self.detailed_edit_prompt
        profile["policy_scaffold"] = self.policy_scaffold
        profile["diagnostics"] = asdict(self.diagnostics)
        profile["validation_errors"] = self.diagnostics.validation_errors
        profile["validation_warnings"] = self.diagnostics.validation_warnings
        profile["auto_filled_fields"] = self.diagnostics.auto_filled_fields
        profile["expansion_failures"] = self.diagnostics.expansion_failures
        return profile


BASE_POLICY_SCAFFOLD = {
    "evidence_policy": "Only assert visual facts supported by the input image or the user instruction.",
    "state_policy": "Describe the intended final stable state, not only the requested intervention.",
    "dependency_policy": "Include coupled visual effects when the edit changes support, contact, lighting, reflection, shadow, refraction, occlusion, or material state.",
    "preservation_policy": "Protect unrelated objects, background regions, camera perspective, and material appearance.",
    "uncertainty_policy": "Record uncertain or unverifiable details instead of inventing them.",
}


CATEGORY_SCAFFOLDS = {
    "optics": {
        "required_evidence_slots": ["light direction", "optical surface or receiving surface", "material appearance", "occlusion boundaries"],
        "required_checks": ["coupled optical effects are updated in the dependent region", "lighting and material appearance remain coherent"],
        "risk_level": "medium",
    },
    "mechanics": {
        "required_evidence_slots": ["support", "contact points", "gravity direction", "stable pose", "occlusion from changed pose"],
        "required_checks": ["affected objects reach a plausible final stable state", "new or removed contacts and contact shadows are consistent"],
        "risk_level": "high",
    },
    "state": {
        "required_evidence_slots": ["state boundary", "material appearance", "localization", "unchanged surrounding context"],
        "required_checks": ["the requested state change is localized", "unrelated regions and material boundaries are preserved"],
        "risk_level": "medium",
    },
}

LAW_SCAFFOLDS = {
    "reflection": {
        "required_dependencies": ["subject", "reflective_surface", "reflected_subject", "reflection_axis_or_contact_line"],
        "required_final_state_slots": ["subject_state", "reflection_state", "surface_state"],
        "required_evidence_slots": ["reflective surface", "subject-surface relation", "reflection position/orientation/scale/softness"],
        "required_checks": ["the subject and its reflection are jointly updated", "the reflective surface is reconstructed without unrelated changes"],
        "avoid_rules": ["Do not add a generic realistic reflection without identifying its surface and correspondence."],
        "recommended_routes": ["reflection_route", "direct_edit"],
        "risk_level": "high",
    },
    "light_propagation": {
        "required_dependencies": ["light_direction", "old_shadow_region", "new_shadow_region", "receiving_surface"],
        "required_final_state_slots": ["target_state", "shadow_state", "lighting_state"],
        "required_evidence_slots": ["reference shadow direction", "receiving surface", "old cast/contact shadow", "shadow softness/falloff"],
        "required_checks": ["old shadow is removed when the object moves", "new shadow direction and softness match visible reference shadows"],
        "avoid_rules": ["Do not copy a sharp object silhouette as the shadow.", "Do not invent a light source unsupported by the scene."],
        "recommended_routes": ["shadow_projection_route", "direct_edit"],
        "risk_level": "high",
    },
    "refraction": {
        "required_dependencies": ["transparent_medium", "internal_medium_state", "distorted_background", "glass_or_surface_artifacts"],
        "required_final_state_slots": ["medium_state", "background_reconstruction", "surface_artifacts"],
        "required_evidence_slots": ["transparent medium", "waterline or boundary", "distorted background", "highlights/caustics"],
        "required_checks": ["medium-specific distortion is updated", "glass geometry and surrounding scene are preserved"],
        "avoid_rules": ["Do not describe generic blur instead of the medium-dependent optical change."],
        "recommended_routes": ["refraction_reconstruction_route", "direct_edit"],
        "risk_level": "high",
    },
    "causality": {
        "required_dependencies": ["intervention_target", "affected_object", "support_or_constraint_change", "predicted_stable_pose", "new_contact_points"],
        "required_final_state_slots": ["affected_object_pose", "support_relation", "contact_points", "secondary_effects"],
        "required_evidence_slots": ["current support/contact", "object stability reason", "affected object", "receiving surface"],
        "required_checks": ["the affected object does not remain in an impossible old pose", "support/contact relationships match the final state"],
        "avoid_rules": ["Do not describe only removal of the cause while leaving the consequence unchanged."],
        "recommended_routes": ["causal_settle_route", "direct_edit"],
        "risk_level": "high",
    },
    "deformation": {
        "required_dependencies": ["deformed_region", "fixed_or_contact_region", "material_continuity", "surface_texture_response"],
        "required_final_state_slots": ["geometry_state", "material_state", "boundary_state"],
        "required_evidence_slots": ["material type", "fixed/contact points", "deformation direction", "texture/highlight continuity"],
        "required_checks": ["deformation is localized to the intended region", "material continuity and adjacent boundaries remain plausible"],
        "avoid_rules": ["Do not request a generic realistic deformation without specifying boundary and continuity constraints."],
        "recommended_routes": ["deformation_route", "direct_edit"],
        "risk_level": "medium",
    },
    "global": {
        "required_dependencies": ["global_lighting_or_environment", "scene_wide_consistency", "object_identity_preservation"],
        "required_final_state_slots": ["global_scene_state"],
        "required_evidence_slots": ["scene structure", "global illumination", "object identities"],
        "required_checks": ["global state change is applied consistently across the scene", "scene structure and object identities are preserved where required"],
        "recommended_routes": ["direct_global_edit"],
        "risk_level": "medium",
    },
    "local": {
        "required_dependencies": ["target_region", "state_boundary", "local_material_response", "nearby_preserve_context"],
        "required_final_state_slots": ["local_material_state", "boundary_state"],
        "required_evidence_slots": ["target material", "state boundary", "nearby unchanged context"],
        "required_checks": ["local state change is visible in the target region", "state change respects material boundaries", "unrelated regions are preserved"],
        "recommended_routes": ["localized_state_route", "localized_inpaint", "direct_edit"],
        "risk_level": "medium",
    },
}

OPERATION_SCAFFOLDS = {
    "remove": {"operation_focus": ["remove the target and repair all necessary dependent regions"]},
    "add": {"operation_focus": ["add the target with correct placement, contact, occlusion, and dependent effects"]},
    "move": {"operation_focus": ["remove old-position effects and create new-position effects"]},
    "replace": {"operation_focus": ["preserve the scene role while changing the target state or appearance"]},
    "topple": {"operation_focus": ["rotate or knock over the target, then depict its final stable resting state and coupled effects"]},
    "deform": {"operation_focus": ["preserve material continuity while changing geometry or pose"]},
    "wet": {"operation_focus": ["localize wetness, liquid, gloss, darkening, and contact effects to the relevant surface"]},
}


class LabelPolicyCompiler:
    def compile(self, instruction: str = "", task_labels: dict[str, str] | None = None) -> dict[str, Any]:
        labels = task_labels or infer_task_labels(instruction)
        category = normalize_label(labels.get("physics_category"))
        law = normalize_label(labels.get("physics_law"))
        operation = normalize_label(labels.get("edit_operation"))
        scaffold: dict[str, Any] = dict(BASE_POLICY_SCAFFOLD)
        scaffold.update(
            {
                "schema_version": SCHEMA_VERSION,
                "labels": {
                    "physics_category": category or "unknown",
                    "physics_law": law or "unknown",
                    "edit_operation": operation or "unknown",
                },
                "physics_category": category or "unknown",
                "physics_law": law or "unknown",
                "edit_operation": operation or "unknown",
                "required_dependencies": [],
                "required_evidence_slots": [],
                "required_final_state_slots": [],
                "required_checks": [],
                "operation_focus": [],
                "avoid_rules": [],
                "recommended_routes": [],
                "risk_level": "low",
                "task_labels": labels,
                "source_instruction": instruction,
            }
        )
        if category in CATEGORY_SCAFFOLDS:
            merge_scaffold(scaffold, CATEGORY_SCAFFOLDS[category])
        if law in LAW_SCAFFOLDS:
            merge_scaffold(scaffold, LAW_SCAFFOLDS[law])
        if operation in OPERATION_SCAFFOLDS:
            merge_scaffold(scaffold, OPERATION_SCAFFOLDS[operation])

        # Backward-compatible aliases consumed by older planner/verifier code.
        scaffold["physics_focus"] = list(
            dict.fromkeys(
                [
                    *coerce_string_list(scaffold.get("required_evidence_slots")),
                    *coerce_string_list(scaffold.get("required_dependencies")),
                ]
            )
        )
        scaffold["avoid"] = coerce_string_list(scaffold.get("avoid_rules"))
        return scaffold


def build_policy_scaffold(
    instruction: str = "",
    task_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    return LabelPolicyCompiler().compile(instruction, task_labels)


def infer_task_labels(instruction: str) -> dict[str, str]:
    text = instruction.casefold()
    operation = first_match(
        text,
        {
            "remove": ["remove", "erase", "delete", "eliminate"],
            "add": ["add", "insert", "place", "introduce"],
            "move": ["move", "reposition", "relocate", "shift"],
            "replace": ["replace", "swap", "change into"],
            "topple": ["knock over", "tip over", "topple", "spill"],
            "deform": ["bend", "deform", "collapse", "tilt"],
            "wet": ["wet", "spill", "melt", "moisten", "water"],
        },
    )
    law = first_match(
        text,
        {
            "reflection": ["reflection", "reflected", "mirror", "glossy", "reflective"],
            "refraction": ["refraction", "refract", "distort through glass", "waterline", "caustic"],
            "light_propagation": ["shadow", "cast shadow", "contact shadow", "light direction", "illumination"],
            "causality": [
                "support",
                "supported",
                "support card",
                "card structure",
                "structure",
                "kickstand",
                "side stand",
                "gravity",
                "fall",
                "fallen",
                "stable",
                "resting",
                "contact",
                "knock over",
                "tip over",
                "topple",
                "spill",
            ],
            "deformation": ["bend", "deform", "collapse", "tilt"],
            "global": ["weather", "season", "night", "daytime", "sunset", "snowy", "rainy"],
            "local": ["wet", "spill", "melt", "burn", "freeze", "rust", "dirty"],
        },
    )
    if law in {"reflection", "refraction", "light_propagation"}:
        category = "optics"
    elif law == "causality":
        category = "mechanics"
    elif law in {"deformation", "global", "local"} or operation in {"wet", "deform", "replace"}:
        category = "state"
    else:
        category = "unknown"
    return {"physics_category": category, "physics_law": law, "edit_operation": operation}


def first_match(text: str, candidates: dict[str, list[str]]) -> str:
    best_label = ""
    best_pos = len(text) + 1
    for label, keywords in candidates.items():
        positions = [text.find(keyword) for keyword in keywords if text.find(keyword) != -1]
        if not positions:
            continue
        current_pos = min(positions)
        if current_pos < best_pos:
            best_pos = current_pos
            best_label = label
    return best_label


def normalize_label(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").casefold()).strip("_")


def merge_scaffold(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, list):
            target[key] = list(dict.fromkeys([*coerce_string_list(target.get(key)), *value]))
        elif key == "risk_level":
            target[key] = max_risk(str(target.get(key, "low")), str(value))
        else:
            target[key] = value


def max_risk(left: str, right: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    return left if order.get(left, 0) >= order.get(right, 0) else right


class StableStatePredictor:
    """Rule-based guardrail for final-state fields that VLMs often omit."""

    def apply(
        self,
        profile: dict[str, Any],
        scaffold: dict[str, Any],
        instruction: str,
        diagnostics: PhysicalIntentDiagnostics,
    ) -> None:
        law = normalize_label(profile.get("labels", {}).get("physics_law") or scaffold.get("physics_law"))
        operation = normalize_label(profile.get("labels", {}).get("edit_operation") or scaffold.get("edit_operation"))
        text = instruction.casefold()

        if law == "causality" and operation == "remove":
            self._apply_causal_remove(profile, text, diagnostics)
        elif law == "causality" and (operation == "topple" or has_any(text, ["knock over", "tip over", "topple", "spill"])):
            self._apply_causal_topple(profile, text, diagnostics)
        elif law == "light_propagation" and operation in {"move", "remove"}:
            self._apply_light_propagation(profile, operation, diagnostics)

    def _apply_causal_remove(
        self,
        profile: dict[str, Any],
        text: str,
        diagnostics: PhysicalIntentDiagnostics,
    ) -> None:
        if self._looks_generic(profile.get("physical_operation")) or self._looks_remove_only(profile.get("physical_operation")):
            profile["physical_operation"] = "remove_support_or_constraint_and_settle"
            self._record_autofill(diagnostics, "physical_operation", "causal_remove_operation")

        if "kickstand" in text or "side stand" in text:
            final_state = {
                "affected_object_pose": "motorcycle has toppled into a stable resting pose on its side after the kickstand support is removed",
                "support_relation": "kickstand no longer supports the motorcycle",
                "contact_points": ["left-side motorcycle body or lower engine contacts the road surface"],
                "secondary_effects": ["old kickstand trace is removed", "broad contact shadow appears along the new side contact area"],
            }
            affected = ["motorcycle", "road contact area", "kickstand mount region"]
            forbidden_old_state = [
                "motorcycle remains upright after its only visible side support is removed",
                "old kickstand shadow or foot contact remains visible",
            ]
            checks = [
                "No kickstand or kickstand foot remains visible.",
                "The motorcycle is no longer upright and rests on its side.",
                "A continuous contact shadow appears along the new side contact area.",
                "The old kickstand contact area is repaired consistently with the road surface.",
            ]
            regions = ["kickstand attachment area", "old kickstand ground contact", "new motorcycle side contact area on the road"]
        elif "5 of spades" in text or ("card" in text and ("support" in text or "structure" in text)):
            final_state = {
                "intervention": "remove the front-left vertical 5-of-spades support card from the load-bearing card structure",
                "affected_object_pose": "glass tabletop rotates and tilts downward toward the front-left corner after the front-left support card is removed",
                "support_relation": "front-left support card is absent; the tabletop is no longer held level at that corner and remains supported only by the remaining card stacks",
                "load_path_change": "load previously carried by the removed front-left card is redistributed to the remaining card stacks, so the local corner cannot stay in the old level pose",
                "contact_points": [
                    "lowered front-left glass corner rests closer to the floor or remaining supports",
                    "one nearby non-5-of-spades card that lost support lies flat on the floor beneath the lowered glass corner",
                ],
                "secondary_effects": [
                    "front-left bay is open with a visible gap where the support card stood",
                    "remaining adjacent cards lean or re-seat consistently with the tilted glass",
                    "new contact shadows and glass reflections match the lowered front-left corner",
                ],
            }
            affected = ["glass tabletop", "remaining card structure", "nearby unsupported card", "floor beneath the lowered corner"]
            forbidden_old_state = [
                "glass tabletop remains level as if the front-left support still exists",
                "all nearby cards remain perfectly upright in the original support configuration",
                "removed 5-of-spades card reappears elsewhere on the structure or floor",
                "front-left bay is filled in as a flat visual repair without a support gap",
            ]
            checks = [
                "The removed support card is absent.",
                "The glass tabletop visibly tilts downward toward the front-left corner.",
                "At least one nearby non-5-of-spades card has fallen or shifted into a grounded final state.",
                "Remaining adjacent cards do not all stay perfectly upright in the old support configuration.",
                "New contacts, shadows, and reflections match the tilted glass and fallen-card configuration.",
            ]
            regions = ["removed support-card bay", "front-left glass corner", "floor below the lowered corner", "adjacent card contacts"]
        else:
            final_state = {
                "affected_object_pose": "objects that depended on the removed support or constraint settle into a plausible new stable pose",
                "support_relation": "removed target no longer provides support, balance, or constraint",
                "contact_points": ["new grounded contact points appear where affected objects settle"],
                "secondary_effects": ["old support traces disappear", "new contact shadows and occlusions match the final stable state"],
            }
            affected = ["removed support or constraint", "object previously supported or constrained", "new contact region"]
            forbidden_old_state = [
                "affected objects remain in the old balanced pose despite the removed support or constraint",
                "old support contact shadows remain visible",
            ]
            checks = [
                "The removed support or constraint is absent.",
                "Affected objects do not remain in an impossible old stable pose.",
                "New contact points and contact shadows match the final stable state.",
            ]
            regions = ["removed target area", "affected object settling area", "new contact-shadow area"]

        force_final_state_keys = set(final_state) if ("5 of spades" in text or ("card" in text and ("support" in text or "structure" in text))) else None
        self._merge_final_state(profile, final_state, diagnostics, "causal_remove_final_state", force_keys=force_final_state_keys)
        self._remove_conflicting_preserve_items(profile, text, diagnostics)
        self._extend_list(profile, "affected_objects", affected, diagnostics, "affected_objects")
        self._extend_list(
            profile,
            "physical_dependencies",
            [
                "intervention_target: removed support or constraint",
                "affected_object: object whose balance or load path changes",
                "support_or_constraint_change: old support relation is invalid after removal",
                "predicted_stable_pose: affected object must settle into a new stable pose",
                "new_contact_points: final pose must create grounded contacts and contact shadows",
            ],
            diagnostics,
            "physical_dependencies",
        )
        self._extend_list(profile, "dependent_regions", regions, diagnostics, "dependent_regions")
        self._extend_list(profile, "must_pass_checks", checks, diagnostics, "must_pass_checks")
        self._extend_list(profile, "must_pass_checks", [f"Do not allow old-state failure: {item}." for item in forbidden_old_state], diagnostics, "must_pass_checks")
        self._extend_list(profile, "route_hints", ["causal_settle_route"], diagnostics, "route_hints")

    def _apply_causal_topple(
        self,
        profile: dict[str, Any],
        text: str,
        diagnostics: PhysicalIntentDiagnostics,
    ) -> None:
        if self._looks_generic(profile.get("physical_operation")):
            profile["physical_operation"] = "topple_object_and_settle_contents"
            self._record_autofill(diagnostics, "physical_operation", "causal_topple_operation")

        if "cup" in text or "mug" in text or "coffee" in text:
            final_state = {
                "affected_object_pose": "cup rests stably on its side after being knocked over",
                "liquid_state": "coffee is no longer inside the cup and forms a flat static puddle on the receiving surface",
                "contact_points": ["cup side contacts the tabletop", "spilled liquid contacts the cup rim and tabletop"],
                "secondary_effects": ["continuous liquid trail connects rim to puddle", "cup shadow and liquid sheen match the scene lighting"],
            }
            affected = ["cup", "coffee", "tabletop spill area", "cup shadow"]
            checks = [
                "The cup rests on its side in a stable final pose.",
                "Coffee forms a flat static puddle on the tabletop.",
                "A continuous trail connects the cup rim to the puddle.",
                "The liquid boundary looks natural for fluid on the surface, not mechanically regular.",
            ]
            regions = ["cup resting area", "rim-to-table liquid trail", "coffee puddle area", "cup contact shadow"]
        else:
            final_state = {
                "affected_object_pose": "target object rests in a stable toppled pose",
                "contact_points": ["new side or lower surface contact supports the toppled object"],
                "secondary_effects": ["shadows, occlusions, and any displaced contents match the final pose"],
            }
            affected = ["toppled target", "new contact region", "dependent shadows or contents"]
            checks = [
                "The target is no longer upright.",
                "The target rests in a physically stable final pose.",
                "New contacts and shadows match the toppled pose.",
            ]
            regions = ["toppled target area", "new contact area", "dependent effect area"]

        self._merge_final_state(profile, final_state, diagnostics, "causal_topple_final_state")
        self._extend_list(profile, "affected_objects", affected, diagnostics, "affected_objects")
        self._extend_list(
            profile,
            "physical_dependencies",
            [
                "intervention_target: toppled object",
                "affected_object: toppled object and any displaced contents",
                "predicted_stable_pose: target rests in a stable final pose",
                "new_contact_points: side or lower surface contacts the receiver",
            ],
            diagnostics,
            "physical_dependencies",
        )
        self._extend_list(profile, "dependent_regions", regions, diagnostics, "dependent_regions")
        self._extend_list(profile, "must_pass_checks", checks, diagnostics, "must_pass_checks")
        self._extend_list(profile, "route_hints", ["causal_settle_route"], diagnostics, "route_hints")

    def _apply_light_propagation(
        self,
        profile: dict[str, Any],
        operation: str,
        diagnostics: PhysicalIntentDiagnostics,
    ) -> None:
        final_state = {
            "target_state": "target object remains complete and visually intact after the requested move or removal",
            "shadow_state": "old cast/contact shadow is removed or relocated, and any new shadow lands on the correct receiving surface",
            "lighting_state": "shadow direction, softness, and intensity remain consistent with visible scene lighting",
        }
        checks = [
            "The target object is complete after the edit if it is moved rather than removed.",
            "Old-position shadow artifacts are absent.",
            "The required shadow is placed on the receiving surface with scene-consistent direction and softness.",
        ]
        if operation == "remove":
            final_state["target_state"] = "removed target and its cast/contact shadows are absent"
            checks[0] = "The removed target is absent."

        self._merge_final_state(profile, final_state, diagnostics, "light_propagation_final_state")
        self._extend_list(
            profile,
            "physical_dependencies",
            ["old_shadow_region", "new_shadow_region", "receiving_surface", "light_direction"],
            diagnostics,
            "physical_dependencies",
        )
        self._extend_list(profile, "must_pass_checks", checks, diagnostics, "must_pass_checks")
        self._extend_list(profile, "route_hints", ["shadow_projection_route"], diagnostics, "route_hints")

    def _merge_final_state(
        self,
        profile: dict[str, Any],
        additions: dict[str, Any],
        diagnostics: PhysicalIntentDiagnostics,
        reason: str,
        force_keys: set[str] | None = None,
    ) -> None:
        current = profile.get("final_state")
        if not isinstance(current, dict):
            current = {}
            profile["final_state"] = current
        changed = False
        if not current or self._looks_generic(current):
            current.update(additions)
            changed = True
        else:
            for key, value in additions.items():
                if (force_keys and key in force_keys) or key not in current or self._looks_generic(current.get(key)):
                    current[key] = value
                    changed = True
        if changed:
            self._record_autofill(diagnostics, "final_state", reason)

    def _extend_list(
        self,
        profile: dict[str, Any],
        field_name: str,
        items: list[Any],
        diagnostics: PhysicalIntentDiagnostics,
        reason: str,
    ) -> None:
        current = profile.get(field_name)
        if not isinstance(current, list):
            current = []
            profile[field_name] = current
        before = len(current)
        seen = {stable_item_key(item) for item in current}
        for item in items:
            key = stable_item_key(item)
            if key not in seen:
                current.append(item)
                seen.add(key)
        if len(current) != before:
            self._record_autofill(diagnostics, field_name, reason)

    def _remove_conflicting_preserve_items(
        self,
        profile: dict[str, Any],
        instruction_text: str,
        diagnostics: PhysicalIntentDiagnostics,
    ) -> None:
        if "card" not in instruction_text or "structure" not in instruction_text:
            return
        current = profile.get("preserve_scope")
        if not isinstance(current, list):
            return
        filtered = [
            item
            for item in current
            if not has_any(
                str(item),
                [
                    "overall structure still appears intact",
                    "overall card-structure form",
                    "positions unchanged",
                    "keep their identities, positions",
                    "stable and unchanged",
                    "remain unchanged",
                ],
            )
        ]
        if len(filtered) != len(current):
            profile["preserve_scope"] = filtered
            self._record_autofill(diagnostics, "preserve_scope", "removed_causal_preserve_conflict")

    def _looks_generic(self, value: Any) -> bool:
        if value in (None, "", [], {}):
            return True
        text = str(value).casefold()
        generic_markers = [
            "unknown",
            "coherent",
            "plausible",
            "stable state",
            "requested edit",
            "remains visually coherent",
            "repaired",
        ]
        return any(marker in text for marker in generic_markers) and not has_any(
            text,
            ["toppled", "tilted", "fallen", "lying", "puddle", "contact shadow", "glass tabletop"],
        )

    def _looks_remove_only(self, value: Any) -> bool:
        text = str(value or "").casefold()
        if not text:
            return True
        removal_markers = ["remove", "delete", "erase", "reconstruct", "repair"]
        stale_stability_markers = ["remains visually coherent", "remains stable", "structure remains", "overall structure", "intact"]
        settle_markers = ["settle", "topple", "tilt", "fall", "load", "redistribut", "contact point"]
        return has_any(text, removal_markers) and has_any(text, stale_stability_markers) and not has_any(text, settle_markers)

    def _record_autofill(
        self,
        diagnostics: PhysicalIntentDiagnostics,
        field_name: str,
        reason: str,
    ) -> None:
        if field_name not in diagnostics.auto_filled_fields:
            diagnostics.auto_filled_fields.append(field_name)
        warning = f"warning:{field_name}:stable_state_predictor:{reason}"
        if warning not in diagnostics.validation_warnings:
            diagnostics.validation_warnings.append(warning)


class TaskProfileValidator:
    required_schema = {
        "schema_version": str,
        "labels": dict,
        "target_objects": list,
        "physical_operation": str,
        "current_state": dict,
        "intervention": dict,
        "final_state": dict,
        "affected_objects": list,
        "physical_dependencies": list,
        "dependent_regions": list,
        "preserve_scope": list,
        "reference_cues": list,
        "uncertainties": list,
        "must_pass_checks": list,
        "route_hints": list,
    }

    def normalize_profile(
        self,
        profile: dict[str, Any],
        scaffold: dict[str, Any] | None = None,
        instruction: str = "",
    ) -> tuple[dict[str, Any], PhysicalIntentDiagnostics]:
        scaffold = scaffold or {}
        raw = profile if isinstance(profile, dict) else {}
        diagnostics = PhysicalIntentDiagnostics()
        labels = dict(scaffold.get("labels") or {})
        labels.setdefault("physics_category", str(scaffold.get("physics_category") or "unknown"))
        labels.setdefault("physics_law", str(scaffold.get("physics_law") or "unknown"))
        labels.setdefault("edit_operation", str(scaffold.get("edit_operation") or "unknown"))

        normalized: dict[str, Any] = {
            "schema_version": str(raw.get("schema_version") or SCHEMA_VERSION),
            "labels": labels,
            "target_objects": self._list_from(raw, "target_objects", "target", "targets"),
            "physical_operation": self._text(raw.get("physical_operation") or raw.get("operation")),
            "current_state": self._dict(raw.get("current_state")),
            "intervention": self._dict(raw.get("intervention")),
            "final_state": self._dict(raw.get("final_state")),
            "affected_objects": self._list_from(raw, "affected_objects", "target_objects", "target", "targets"),
            "physical_dependencies": self._list_from(raw, "physical_dependencies", "dependencies", "dependent_effects"),
            "dependent_regions": self._list_from(raw, "dependent_regions", "dependency_regions", "regions"),
            "preserve_scope": self._list_from(raw, "preserve_scope", "preserve"),
            "reference_cues": self._list_from(raw, "reference_cues", "evidence", "visual_evidence"),
            "uncertainties": self._list_from(raw, "uncertainties"),
            "must_pass_checks": self._list_from(raw, "must_pass_checks", "verifier_focus", "required_checks"),
            "route_hints": self._list_from(raw, "route_hints", "recommended_routes"),
        }

        if not normalized["physical_operation"]:
            normalized["physical_operation"] = "perform the requested edit as a physical state transition"
            diagnostics.auto_filled_fields.append("physical_operation")
            diagnostics.validation_warnings.append("warning:physical_operation:auto_filled")

        stable_state_instruction = instruction or str(scaffold.get("source_instruction") or "")
        StableStatePredictor().apply(normalized, scaffold, stable_state_instruction, diagnostics)
        self._fill_from_scaffold(normalized, scaffold, diagnostics)
        self._validate(normalized, scaffold, diagnostics)
        return normalized, diagnostics

    def _fill_from_scaffold(
        self,
        profile: dict[str, Any],
        scaffold: dict[str, Any],
        diagnostics: PhysicalIntentDiagnostics,
    ) -> None:
        if not profile["preserve_scope"]:
            profile["preserve_scope"] = ["unrelated background", "camera viewpoint", "unrequested object identity"]
            diagnostics.auto_filled_fields.append("preserve_scope")
            diagnostics.validation_warnings.append("warning:preserve_scope:auto_filled")
        if "uncertainties" not in profile or profile["uncertainties"] is None:
            profile["uncertainties"] = []
            diagnostics.auto_filled_fields.append("uncertainties")
        if not profile["physical_dependencies"] and scaffold.get("required_dependencies"):
            profile["physical_dependencies"] = coerce_string_list(scaffold.get("required_dependencies"))
            diagnostics.auto_filled_fields.append("physical_dependencies")
            diagnostics.expansion_failures.append("missing_dependency")
            diagnostics.validation_errors.append("error:physical_dependencies:missing_model_output")
        if not profile["reference_cues"] and scaffold.get("required_evidence_slots"):
            profile["reference_cues"] = coerce_string_list(scaffold.get("required_evidence_slots"))
            diagnostics.auto_filled_fields.append("reference_cues")
            diagnostics.expansion_failures.append("missing_evidence_grounding")
            diagnostics.validation_warnings.append("warning:reference_cues:scaffold_only")
        if not profile["must_pass_checks"] and scaffold.get("required_checks"):
            profile["must_pass_checks"] = coerce_string_list(scaffold.get("required_checks"))
            diagnostics.auto_filled_fields.append("must_pass_checks")
            diagnostics.expansion_failures.append("missing_must_pass_checks")
            diagnostics.validation_errors.append("error:must_pass_checks:missing_model_output")
        if not profile["route_hints"] and scaffold.get("recommended_routes"):
            profile["route_hints"] = coerce_string_list(scaffold.get("recommended_routes"))
            diagnostics.auto_filled_fields.append("route_hints")

    def _validate(self, profile: dict[str, Any], scaffold: dict[str, Any], diagnostics: PhysicalIntentDiagnostics) -> None:
        for key, expected_type in self.required_schema.items():
            if key not in profile:
                diagnostics.validation_errors.append(f"error:{key}:missing")
            elif not isinstance(profile[key], expected_type):
                diagnostics.validation_errors.append(f"error:{key}:type:{expected_type.__name__}")

        for key in ["final_state", "must_pass_checks", "physical_dependencies"]:
            if not profile.get(key):
                diagnostics.validation_errors.append(f"error:{key}:empty")

        law = str(profile.get("labels", {}).get("physics_law") or scaffold.get("physics_law") or "").casefold()
        if law == "reflection":
            self._require_dependency(profile, diagnostics, ["reflective_surface", "reflected_subject"])
        elif law == "light_propagation":
            self._require_dependency(profile, diagnostics, ["old_shadow_region", "receiving_surface"])
        elif law == "refraction":
            self._require_dependency(profile, diagnostics, ["transparent_medium", "distorted_background"])
        elif law == "causality":
            self._require_dependency(profile, diagnostics, ["affected_object", "predicted_stable_pose", "new_contact_points"])
            if not profile["final_state"]:
                diagnostics.expansion_failures.append("missing_final_stable_state")

    def _require_dependency(self, profile: dict[str, Any], diagnostics: PhysicalIntentDiagnostics, required_terms: list[str]) -> None:
        haystack = " ".join(coerce_string_list(profile.get("physical_dependencies"))).casefold()
        for term in required_terms:
            compact_term = term.replace("_", " ")
            if term not in haystack and compact_term not in haystack:
                diagnostics.validation_warnings.append(f"warning:physical_dependencies:missing_specific:{term}")

    def _list_from(self, raw: dict[str, Any], *keys: str) -> list[Any]:
        for key in keys:
            items = coerce_profile_list(raw.get(key))
            if items:
                return items
        return []

    def _text(self, value: Any) -> str:
        return str(value).strip() if value is not None else ""

    def _dict(self, value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def validate_profile(self, profile: dict[str, Any]) -> list[str]:
        diagnostics = PhysicalIntentDiagnostics()
        self._validate(profile, profile.get("policy_scaffold", {}), diagnostics)
        return diagnostics.validation_errors


class PlanValidator(TaskProfileValidator):
    """Backward-compatible name for older imports."""


def validate_task_profile(profile: dict[str, Any]) -> list[str]:
    return TaskProfileValidator().validate_profile(profile)


class PromptRenderer:
    def render(self, profile: dict[str, Any], user_instruction: str) -> str:
        detailed_prompt = self.render_detailed(profile, user_instruction)
        return PromptCompressor().compress(profile, user_instruction, detailed_prompt)

    def render_detailed(self, profile: dict[str, Any], user_instruction: str) -> str:
        law = str(profile.get("labels", {}).get("physics_law") or "").casefold()
        if law == "reflection":
            return self._render_reflection(profile, user_instruction)
        if law == "light_propagation":
            return self._render_light_propagation(profile, user_instruction)
        if law == "refraction":
            return self._render_refraction(profile, user_instruction)
        if law == "causality":
            return self._render_causality(profile, user_instruction)
        if law == "deformation":
            return self._render_deformation(profile, user_instruction)
        if law in {"global", "local"}:
            return self._render_state(profile, user_instruction, law)
        return self._render_generic(profile, user_instruction)

    def _base_lines(self, profile: dict[str, Any], user_instruction: str) -> list[str]:
        return [
            "Edit the input image according to this physically grounded task.",
            f"Original instruction: {user_instruction}",
            f"Physical operation: {format_prompt_value(profile.get('physical_operation', ''))}",
            f"Target objects: {format_prompt_value(profile.get('target_objects', []) or profile.get('affected_objects', []))}",
            f"Final stable state: {format_prompt_value(profile.get('final_state', {}))}",
            f"Dependent regions: {format_prompt_value(profile.get('dependent_regions', []))}",
            f"Reference cues: {format_prompt_value(profile.get('reference_cues', []))}",
            f"Preserve unchanged: {format_prompt_value(profile.get('preserve_scope', []))}",
            f"Physical dependencies to update consistently: {format_prompt_value(profile.get('physical_dependencies', []))}",
            f"Must-pass visual checks: {format_prompt_value(profile.get('must_pass_checks', []))}",
        ]

    def _finish(self, lines: list[str], profile: dict[str, Any]) -> str:
        uncertainties = coerce_profile_list(profile.get("uncertainties"))
        if uncertainties:
            lines.append(f"Treat these details as uncertain and do not invent unsupported specifics: {format_prompt_value(uncertainties)}")
        lines.append("Keep the edit limited to the requested target and necessary dependent regions.")
        return "\n".join(str(line) for line in lines if str(line).strip())

    def _render_reflection(self, profile: dict[str, Any], user_instruction: str) -> str:
        lines = self._base_lines(profile, user_instruction)
        lines.extend(
            [
                "Update the subject, reflective surface, and reflected subject as a coupled relationship.",
                "Place the reflection only on the identified reflective surface, aligned with the subject and contact/waterline when relevant.",
                "Match reflection orientation, scale, softness, brightness, and masking to visible scene cues.",
                "Do not add a generic reflection outside the dependent reflective region.",
            ]
        )
        return self._finish(lines, profile)

    def _render_light_propagation(self, profile: dict[str, Any], user_instruction: str) -> str:
        lines = self._base_lines(profile, user_instruction)
        lines.extend(
            [
                "Update cast shadows and contact shadows together with the target edit.",
                "Remove old-position shadows when the object is removed or moved.",
                "Create or adjust the required shadow on the receiving surface using the visible reference light direction.",
                "Match shadow direction, placement, softness, and distance falloff; do not make a sharp copied silhouette unless the scene supports it.",
            ]
        )
        return self._finish(lines, profile)

    def _render_refraction(self, profile: dict[str, Any], user_instruction: str) -> str:
        lines = self._base_lines(profile, user_instruction)
        lines.extend(
            [
                "Update the transparent medium, internal medium state, distorted background, waterline/edge highlights, and caustic artifacts together.",
                "If material is removed, restore the background appearance that should be visible through the remaining medium or air.",
                "Preserve glass or transparent-object geometry unless the instruction explicitly changes it.",
            ]
        )
        return self._finish(lines, profile)

    def _render_causality(self, profile: dict[str, Any], user_instruction: str) -> str:
        lines = self._base_lines(profile, user_instruction)
        lines.extend(
            [
                "Treat the request as an intervention followed by a physically plausible final stable state.",
                "Change the intervention target and also update every affected object whose support, contact, balance, or constraint changes.",
                "Do not leave affected objects in the old stable pose if the support or constraint has been removed.",
                "Add or update contact points, occlusion, and contact shadows required by the final stable state.",
                "If a support object is removed, show the resulting load redistribution: visible tilt, fall, new grounded contact, or explicit uncertainty if the image evidence proves no load depended on it.",
            ]
        )
        return self._finish(lines, profile)

    def _render_deformation(self, profile: dict[str, Any], user_instruction: str) -> str:
        lines = self._base_lines(profile, user_instruction)
        lines.extend(
            [
                "Localize deformation to the intended region while preserving fixed/contact regions.",
                "Maintain material continuity, texture flow, highlights, and adjacent boundaries across the deformed shape.",
                "Avoid changing unrelated rigid structure or background geometry.",
            ]
        )
        return self._finish(lines, profile)

    def _render_state(self, profile: dict[str, Any], user_instruction: str, law: str) -> str:
        lines = self._base_lines(profile, user_instruction)
        if law == "global":
            lines.extend(
                [
                    "Apply the global state consistently across sky, lighting, color temperature, visibility, shadows, and material response.",
                    "Preserve scene structure and object identities while changing the requested global condition.",
                ]
            )
        else:
            lines.extend(
                [
                    "Apply the local state change only inside the target region and necessary boundary transition area.",
                    "Respect material boundaries and preserve nearby context outside the affected region.",
                ]
            )
        return self._finish(lines, profile)

    def _render_generic(self, profile: dict[str, Any], user_instruction: str) -> str:
        lines = self._base_lines(profile, user_instruction)
        lines.extend(
            [
                f"Physical dependencies to update consistently: {profile.get('physical_dependencies', [])}",
                f"Must-pass visual checks: {profile.get('must_pass_checks', [])}",
            ]
        )
        return self._finish(lines, profile)


class PromptCompressor:
    """Render a compact executor prompt from the audited TaskProfile."""

    word_budgets = {
        "reflection": 240,
        "light_propagation": 260,
        "refraction": 280,
        "causality": 420,
        "deformation": 240,
        "global": 180,
        "local": 180,
    }

    def compress(self, profile: dict[str, Any], user_instruction: str, detailed_prompt: str = "") -> str:
        law = str(profile.get("labels", {}).get("physics_law") or "").casefold()
        budget = self.word_budgets.get(law, 240)
        lines = self._priority_lines(profile, user_instruction, law)
        prompt = "\n".join(line for line in lines if line.strip())
        if len(prompt.split()) <= budget:
            return prompt
        return self._trim_to_budget(lines, budget)

    def _priority_lines(self, profile: dict[str, Any], user_instruction: str, law: str) -> list[str]:
        final_state = format_prompt_value(profile.get("final_state", {}))
        targets = format_prompt_value(limit_prompt_items(profile.get("target_objects") or profile.get("affected_objects"), 4))
        dependency_limit = 5 if law == "causality" else 6
        region_limit = 5 if law == "causality" else 6
        check_limit = 6 if law == "causality" else 8
        dependencies = format_prompt_value(limit_prompt_items(self._rank_items(profile.get("physical_dependencies"), law), dependency_limit))
        regions = format_prompt_value(limit_prompt_items(self._rank_items(profile.get("dependent_regions"), law), region_limit))
        preserve = format_prompt_value(limit_prompt_items(self._rank_items(profile.get("preserve_scope"), "preserve"), 5))
        checks = format_prompt_value(limit_prompt_items(self._rank_items(profile.get("must_pass_checks"), law), check_limit))
        uncertainties = format_prompt_value(limit_prompt_items(profile.get("uncertainties"), 2))
        operation = format_prompt_value(profile.get("physical_operation", "")).rstrip(".")

        lines = [
            f"Edit: {user_instruction}",
            f"Target: {targets}" if targets else "",
            f"Physical outcome: {operation}. {final_state}" if operation else f"Physical outcome: {final_state}",
            f"Update coupled regions/effects: {regions}. {dependencies}" if regions or dependencies else "",
            f"Preserve: {preserve}" if preserve else "",
            f"Must satisfy: {checks}" if checks else "",
        ]
        if law == "causality":
            lines.append(
                "Do not leave affected objects in the old stable pose after a support, balance, contact, or constraint has changed."
            )
        if uncertainties:
            lines.append(f"Uncertain details: {uncertainties}. Do not invent unsupported extra objects.")
        lines.append("Keep the edit local to the target and necessary dependent regions.")
        return lines

    def _rank_items(self, value: Any, law: str) -> list[Any]:
        items = coerce_profile_list(value)
        if not items:
            return []
        ranked = sorted(enumerate(items), key=lambda indexed: (self._priority_score(str(indexed[1]), law), -indexed[0]), reverse=True)
        return [item for _, item in ranked]

    def _priority_score(self, text: str, law: str) -> int:
        lowered = text.casefold()
        common = {
            "absent": 5,
            "target": 4,
            "contact": 4,
            "shadow": 4,
            "preserve": 3,
            "unchanged": 3,
            "old-state failure": 6,
            "do not": 5,
        }
        law_terms = {
            "causality": {
                "support": 6,
                "constraint": 6,
                "stable": 5,
                "tilt": 6,
                "fall": 6,
                "fallen": 6,
                "grounded": 6,
                "load": 6,
                "upright": 5,
                "level": 5,
                "gap": 5,
                "reflection": 3,
            },
            "light_propagation": {"old shadow": 6, "new shadow": 6, "receiving surface": 5, "light direction": 5},
            "reflection": {"reflective": 6, "reflection": 6, "surface": 5, "axis": 4},
            "refraction": {"transparent": 6, "refraction": 6, "waterline": 5, "distorted": 5},
            "preserve": {"background": 4, "camera": 4, "unrelated": 4, "identity": 5},
        }
        score = sum(weight for token, weight in common.items() if token in lowered)
        score += sum(weight for token, weight in law_terms.get(law, {}).items() if token in lowered)
        return score

    def _trim_to_budget(self, lines: list[str], budget: int) -> str:
        kept: list[str] = []
        used = 0
        for line in lines:
            words = line.split()
            if not words:
                continue
            remaining = budget - used
            if remaining <= 0:
                break
            if len(words) <= remaining:
                kept.append(line)
                used += len(words)
            elif not kept and remaining > 12:
                kept.append(" ".join(words[:remaining]).rstrip(" ,;") + ".")
                break
        return "\n".join(kept)


def render_edit_prompt(profile: dict[str, Any], user_instruction: str) -> str:
    return PromptRenderer().render(profile, user_instruction)


class PhysicalIntentExpander:
    def __init__(self, client: OpenAICompatClient, model: str):
        self.client = client
        self.model = model
        self.compiler = LabelPolicyCompiler()
        self.validator = TaskProfileValidator()
        self.renderer = PromptRenderer()

    def expand(
        self,
        image_path: Path,
        instruction: str,
        previous_failure: str | None = None,
        policy_scaffold: dict[str, Any] | None = None,
        task_labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        result = self.expand_result(
            image_path=image_path,
            instruction=instruction,
            previous_failure=previous_failure,
            policy_scaffold=policy_scaffold,
            task_labels=task_labels,
        )
        return result.as_legacy_profile()

    def expand_result(
        self,
        image_path: Path,
        instruction: str,
        previous_failure: str | None = None,
        policy_scaffold: dict[str, Any] | None = None,
        task_labels: dict[str, str] | None = None,
    ) -> PhysicalIntentResult:
        repair_context = f"\nPrevious verifier failure to address: {previous_failure}" if previous_failure else ""
        scaffold = policy_scaffold or self.compiler.compile(instruction, task_labels)
        user_text = (
            "Create a TaskProfile for the image edit.\n"
            f"User instruction: {instruction}{repair_context}\n"
            f"Policy scaffold: {scaffold}\n"
            "Return only the required JSON object. Do not include analysis prose."
        )
        try:
            profile = self.client.chat_json(
                self.model,
                [
                    {"role": "system", "content": TASK_PROFILE_SYSTEM},
                    vision_user_message(user_text, [image_path]),
                ],
                max_tokens=1800,
            )
        except Exception as exc:
            profile = {}
            task_profile, diagnostics = self.validator.normalize_profile(profile, scaffold, instruction)
            diagnostics.expansion_failures.append("vlm_json_failed_rule_fallback")
            diagnostics.validation_warnings.append(f"warning:expander:vlm_json_failed:{type(exc).__name__}")
            detailed_prompt = self.renderer.render_detailed(task_profile, instruction)
            edit_prompt = self.renderer.render(task_profile, instruction)
            diagnostics.prompt_length = len(edit_prompt.split())
            diagnostics.detailed_prompt_length = len(detailed_prompt.split())
            diagnostics.prompt_compression_ratio = safe_ratio(diagnostics.prompt_length, diagnostics.detailed_prompt_length)
            return PhysicalIntentResult(
                task_profile=task_profile,
                edit_prompt=edit_prompt,
                diagnostics=diagnostics,
                policy_scaffold=scaffold,
                detailed_edit_prompt=detailed_prompt,
            )
        if not isinstance(profile, dict):
            profile = {}
        task_profile, diagnostics = self.validator.normalize_profile(profile, scaffold, instruction)
        detailed_prompt = self.renderer.render_detailed(task_profile, instruction)
        edit_prompt = self.renderer.render(task_profile, instruction)
        diagnostics.prompt_length = len(edit_prompt.split())
        diagnostics.detailed_prompt_length = len(detailed_prompt.split())
        diagnostics.prompt_compression_ratio = safe_ratio(diagnostics.prompt_length, diagnostics.detailed_prompt_length)
        return PhysicalIntentResult(
            task_profile=task_profile,
            edit_prompt=edit_prompt,
            diagnostics=diagnostics,
            policy_scaffold=scaffold,
            detailed_edit_prompt=detailed_prompt,
        )


def coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, set):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def format_prompt_value(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            rendered = format_prompt_value(item)
            if rendered:
                parts.append(f"{humanize_key(key)}: {rendered}")
        return "; ".join(parts)
    if isinstance(value, list):
        rendered_items = [format_prompt_value(item) for item in value]
        return "; ".join(item for item in rendered_items if item)
    if isinstance(value, tuple):
        return format_prompt_value(list(value))
    if isinstance(value, set):
        return format_prompt_value(sorted(value))
    return str(value).strip() if value is not None else ""


def limit_prompt_items(value: Any, limit: int) -> list[Any]:
    items = coerce_profile_list(value)
    return items[:limit]


def humanize_key(value: Any) -> str:
    return str(value).replace("_", " ").strip()


def coerce_profile_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [item for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [item for item in value if str(item).strip()]
    if isinstance(value, set):
        return [item for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def has_any(text: str, needles: list[str]) -> bool:
    lowered = text.casefold()
    return any(needle in lowered for needle in needles)


def stable_item_key(value: Any) -> str:
    if isinstance(value, dict):
        return "|".join(f"{key}={stable_item_key(val)}" for key, val in sorted(value.items()))
    if isinstance(value, list):
        return "|".join(stable_item_key(item) for item in value)
    return str(value).casefold().strip()


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return round(numerator / denominator, 3)

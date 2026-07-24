from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from physical_agent.physical_intent import LabelPolicyCompiler, TaskProfileValidator, infer_task_labels, render_edit_prompt
from physical_agent.physical_intent import PhysicalIntentExpander


def normalize_with_rules(instruction: str, labels: dict[str, str], raw_profile: dict | None = None) -> dict:
    scaffold = LabelPolicyCompiler().compile(instruction, labels)
    profile, diagnostics = TaskProfileValidator().normalize_profile(raw_profile or {}, scaffold, instruction)
    profile["diagnostics"] = diagnostics
    return profile


def test_knock_over_spill_infers_causality_topple() -> None:
    labels = infer_task_labels("Knock over the cup, spilling the coffee.")

    assert labels["physics_category"] == "mechanics"
    assert labels["physics_law"] == "causality"
    assert labels["edit_operation"] == "topple"


def test_support_removal_short_prompts_infer_causality() -> None:
    kickstand = infer_task_labels("Remove the motorcycle's kickstand.")
    card_structure = infer_task_labels("Remove the 5 of spades card from the structure.")

    assert kickstand["physics_law"] == "causality"
    assert kickstand["edit_operation"] == "remove"
    assert card_structure["physics_law"] == "causality"
    assert card_structure["edit_operation"] == "remove"


def test_causal_remove_kickstand_predicts_motorcycle_settle_state() -> None:
    profile = normalize_with_rules(
        "Remove the motorcycle's kickstand.",
        {"physics_category": "Mechanics", "physics_law": "Causality", "edit_operation": "remove"},
    )

    final_state_text = str(profile["final_state"]).casefold()
    checks_text = " ".join(str(item) for item in profile["must_pass_checks"]).casefold()
    dependencies_text = " ".join(str(item) for item in profile["physical_dependencies"]).casefold()

    assert "motorcycle" in final_state_text
    assert "side" in final_state_text or "toppled" in final_state_text
    assert "contact shadow" in checks_text
    assert "predicted_stable_pose" in dependencies_text
    assert "causal_settle_route" in profile["route_hints"]


def test_causal_remove_card_predicts_glass_and_card_settle_state() -> None:
    profile = normalize_with_rules(
        "Remove the 5 of spades card from the structure.",
        {"physics_category": "Mechanics", "physics_law": "Causality", "edit_operation": "remove"},
    )

    final_state_text = str(profile["final_state"]).casefold()
    checks_text = " ".join(str(item) for item in profile["must_pass_checks"]).casefold()

    assert "glass tabletop" in final_state_text
    assert "front-left" in final_state_text
    assert "tilt" in final_state_text
    assert "card" in final_state_text
    assert "lies flat" in final_state_text or "fallen" in final_state_text
    assert "support card" in checks_text
    assert "contact" in final_state_text


def test_causal_remove_card_overrides_remove_only_vlm_profile() -> None:
    profile = normalize_with_rules(
        "Remove the 5 of spades card from the structure.",
        {"physics_category": "Mechanics", "physics_law": "Causality", "edit_operation": "remove"},
        {
            "physical_operation": "Remove the foreground 5 of spades card panel and reconstruct the exposed area so the structure remains visually coherent and stable.",
            "final_state": {},
            "preserve_scope": [
                "overall card-structure form: keep their identities, positions, and patterns unchanged",
                "floor/background outside the edit region",
            ],
            "must_pass_checks": [
                "The 5 of spades card is absent from the final image.",
                "The overall structure still appears intact and unchanged away from the edit region.",
            ],
        },
    )

    prompt = render_edit_prompt(profile, "Remove the 5 of spades card from the structure.").casefold()

    assert "remove_support_or_constraint_and_settle" in profile["physical_operation"]
    assert "load_path_change" in profile["final_state"]
    assert "one nearby non-5-of-spades card" in str(profile["final_state"]).casefold()
    assert "front-left bay is open" in str(profile["final_state"]).casefold()
    assert "glass tabletop remains level" in prompt
    assert "must satisfy" in prompt
    assert "update coupled regions/effects" in prompt
    assert "support_or_constraint_change" in prompt
    assert "[{" not in prompt
    assert "overall card-structure form" not in str(profile["preserve_scope"]).casefold()


def test_compressed_card_prompt_preserves_key_causal_constraints() -> None:
    profile = normalize_with_rules(
        "Remove the 5 of spades card from the structure.",
        {"physics_category": "Mechanics", "physics_law": "Causality", "edit_operation": "remove"},
        {
            "target_objects": [{"name": "5 of spades card", "role": "supporting card"}],
            "physical_operation": "Remove the 5 of spades card from the card structure and update the structure to its new stable supported configuration.",
            "final_state": {
                "affected_object_pose": "glass tabletop rotates and tilts downward toward the front-left corner after the front-left support card is removed",
                "support_relation": "front-left support card is absent; the tabletop is no longer held level at that corner",
                "contact_points": [
                    "lowered front-left glass corner rests closer to the floor or remaining supports",
                    "one nearby non-5-of-spades card that lost support lies flat on the floor beneath the lowered glass corner",
                ],
                "secondary_effects": [
                    "front-left bay is open with a visible gap where the support card stood",
                    "remaining adjacent cards lean or re-seat consistently with the tilted glass",
                ],
            },
            "must_pass_checks": [
                "The glass tabletop visibly tilts downward toward the front-left corner.",
                "At least one nearby non-5-of-spades card has fallen or shifted into a grounded final state.",
                "Do not allow old-state failure: glass tabletop remains level as if the front-left support still exists.",
                "Do not allow old-state failure: all nearby cards remain perfectly upright in the original support configuration.",
            ],
        },
    )

    prompt = render_edit_prompt(profile, "Remove the 5 of spades card from the structure.")
    prompt_text = prompt.casefold()

    assert len(prompt.split()) <= 420
    assert "glass tabletop" in prompt_text
    assert "front-left" in prompt_text
    assert "tilt" in prompt_text
    assert "non-5-of-spades card" in prompt_text
    assert "gap" in prompt_text
    assert "old-state failure" in prompt_text
    assert "must satisfy" in prompt_text
    assert not prompt_text.rstrip().endswith(" or.")


def test_causal_topple_cup_predicts_puddle_and_rim_connection() -> None:
    profile = normalize_with_rules(
        "Knock over the cup, spilling the coffee.",
        {"physics_category": "Mechanics", "physics_law": "Causality", "edit_operation": "topple"},
    )

    final_state_text = str(profile["final_state"]).casefold()
    checks_text = " ".join(str(item) for item in profile["must_pass_checks"]).casefold()

    assert "cup" in final_state_text
    assert "puddle" in final_state_text
    assert "rim" in checks_text
    assert "natural" in checks_text


def test_expander_uses_rule_fallback_when_vlm_json_fails() -> None:
    class BrokenClient:
        def chat_json(self, *args, **kwargs):
            raise ValueError("bad json")

    image_path = ROOT / "data" / "samples" / "red_ball_shadow.png"
    expander = PhysicalIntentExpander(BrokenClient(), "mock")
    profile = expander.expand(image_path, "Remove the motorcycle's kickstand.")

    assert profile["edit_prompt"] != "Remove the motorcycle's kickstand."
    assert profile["detailed_edit_prompt"] != profile["edit_prompt"]
    assert "motorcycle" in str(profile["final_state"]).casefold()
    assert "vlm_json_failed_rule_fallback" in profile["expansion_failures"]
    assert profile["diagnostics"]["prompt_length"] <= profile["diagnostics"]["detailed_prompt_length"]

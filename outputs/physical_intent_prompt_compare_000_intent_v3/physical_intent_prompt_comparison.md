# PhysicalIntent Prompt Comparison

- Input prompt level: `superficial`
- Label mode: `inferred`
- PICABench `explicit_prompt` is shown only as a comparison target, not as runtime input.

## picabench_0000_causality

| Field | Value |
|---|---|
| Physics category | `Mechanics` |
| Physics law | `Causality` |
| Edit operation | `remove` |
| Labels used by component | `{'physics_category': 'mechanics', 'physics_law': 'causality', 'edit_operation': 'remove'}` |
| Generated prompt words | `516` |
| Explicit prompt words | `133` |
| Validation errors | `[]` |
| Validation warnings | `['warning:physical_operation:auto_filled', 'warning:physical_operation:stable_state_predictor:causal_remove_operation', 'warning:final_state:stable_state_predictor:causal_remove_final_state', 'warning:affected_objects:stable_state_predictor:affected_objects', 'warning:physical_dependencies:stable_state_predictor:physical_dependencies', 'warning:dependent_regions:stable_state_predictor:dependent_regions', 'warning:must_pass_checks:stable_state_predictor:must_pass_checks', 'warning:route_hints:stable_state_predictor:route_hints', 'warning:preserve_scope:auto_filled', 'warning:reference_cues:scaffold_only', 'warning:expander:vlm_json_failed:JSONDecodeError']` |
| Expansion failures | `['missing_evidence_grounding', 'vlm_json_failed_rule_fallback']` |

### Input Prompt

```text
Remove the 5 of spades card from the structure.
```

### PhysicalIntent Generated Prompt

```text
Edit the input image according to this physically grounded task.
Original instruction: Remove the 5 of spades card from the structure.
Physical operation: remove_support_or_constraint_and_settle
Target objects: ['glass tabletop', 'remaining card structure', 'nearby unsupported card', 'floor beneath the lowered corner']
Final stable state: {'intervention': 'remove the front-left vertical 5-of-spades support card from the load-bearing card structure', 'affected_object_pose': 'glass tabletop rotates and tilts downward toward the front-left corner after the front-left support card is removed', 'support_relation': 'front-left support card is absent; the tabletop is no longer held level at that corner and remains supported only by the remaining card stacks', 'load_path_change': 'load previously carried by the removed front-left card is redistributed to the remaining card stacks, so the local corner cannot stay in the old level pose', 'contact_points': ['lowered front-left glass corner rests closer to the floor or remaining supports', 'one nearby non-5-of-spades card that lost support lies flat on the floor beneath the lowered glass corner'], 'secondary_effects': ['front-left bay is open with a visible gap where the support card stood', 'remaining adjacent cards lean or re-seat consistently with the tilted glass', 'new contact shadows and glass reflections match the lowered front-left corner']}
Dependent regions: ['removed support-card bay', 'front-left glass corner', 'floor below the lowered corner', 'adjacent card contacts']
Reference cues: ['support', 'contact points', 'gravity direction', 'stable pose', 'occlusion from changed pose', 'current support/contact', 'object stability reason', 'affected object', 'receiving surface']
Preserve unchanged: ['unrelated background', 'camera viewpoint', 'unrequested object identity']
Physical dependencies to update consistently: ['intervention_target: removed support or constraint', 'affected_object: object whose balance or load path changes', 'support_or_constraint_change: old support relation is invalid after removal', 'predicted_stable_pose: affected object must settle into a new stable pose', 'new_contact_points: final pose must create grounded contacts and contact shadows']
Must-pass visual checks: ['The removed support card is absent.', 'The glass tabletop visibly tilts downward toward the front-left corner.', 'At least one nearby non-5-of-spades card has fallen or shifted into a grounded final state.', 'Remaining adjacent cards do not all stay perfectly upright in the old support configuration.', 'New contacts, shadows, and reflections match the tilted glass and fallen-card configuration.', 'Do not allow old-state failure: glass tabletop remains level as if the front-left support still exists.', 'Do not allow old-state failure: all nearby cards remain perfectly upright in the original support configuration.', 'Do not allow old-state failure: removed 5-of-spades card reappears elsewhere on the structure or floor.', 'Do not allow old-state failure: front-left bay is filled in as a flat visual repair without a support gap.']
Treat the request as an intervention followed by a physically plausible final stable state.
Change the intervention target and also update every affected object whose support, contact, balance, or constraint changes.
Do not leave affected objects in the old stable pose if the support or constraint has been removed.
Add or update contact points, occlusion, and contact shadows required by the final stable state.
If a support object is removed, show the resulting load redistribution: visible tilt, fall, new grounded contact, or explicit uncertainty if the image evidence proves no load depended on it.
Keep the edit limited to the requested target and necessary dependent regions.
```

### PICABench Explicit Prompt

```text
Remove the front-left vertical support card—the 5 of spades—from the card structure beneath the glass tabletop. After its removal, show the final stable outcome: the front-left bay is open with a visible gap where that card used to stand; no 5-of-spades appears anywhere in the structure or on the floor. The glass tabletop has rotated and now rests tilted downward toward the front-left corner, still supported by the remaining card stacks. One nearby card that lost support (not a 5 of spades—use a clubs card face or a card back) has fallen out and now lies flat on the floor in the front-left foreground beneath the lowered glass corner. Ensure all cards and the glass have natural contact points, correct perspective, and updated shadows/reflections consistent with the new tilted glass and collapsed corner.
```

### Generated TaskProfile Summary

```json
{
  "physical_operation": "remove_support_or_constraint_and_settle",
  "target_objects": [],
  "affected_objects": [
    "glass tabletop",
    "remaining card structure",
    "nearby unsupported card",
    "floor beneath the lowered corner"
  ],
  "physical_dependencies": [
    "intervention_target: removed support or constraint",
    "affected_object: object whose balance or load path changes",
    "support_or_constraint_change: old support relation is invalid after removal",
    "predicted_stable_pose: affected object must settle into a new stable pose",
    "new_contact_points: final pose must create grounded contacts and contact shadows"
  ],
  "dependent_regions": [
    "removed support-card bay",
    "front-left glass corner",
    "floor below the lowered corner",
    "adjacent card contacts"
  ],
  "preserve_scope": [
    "unrelated background",
    "camera viewpoint",
    "unrequested object identity"
  ],
  "reference_cues": [
    "support",
    "contact points",
    "gravity direction",
    "stable pose",
    "occlusion from changed pose",
    "current support/contact",
    "object stability reason",
    "affected object",
    "receiving surface"
  ],
  "uncertainties": [],
  "must_pass_checks": [
    "The removed support card is absent.",
    "The glass tabletop visibly tilts downward toward the front-left corner.",
    "At least one nearby non-5-of-spades card has fallen or shifted into a grounded final state.",
    "Remaining adjacent cards do not all stay perfectly upright in the old support configuration.",
    "New contacts, shadows, and reflections match the tilted glass and fallen-card configuration.",
    "Do not allow old-state failure: glass tabletop remains level as if the front-left support still exists.",
    "Do not allow old-state failure: all nearby cards remain perfectly upright in the original support configuration.",
    "Do not allow old-state failure: removed 5-of-spades card reappears elsewhere on the structure or floor.",
    "Do not allow old-state failure: front-left bay is filled in as a flat visual repair without a support gap."
  ],
  "route_hints": [
    "causal_settle_route"
  ]
}
```

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
| Generated prompt words | `705` |
| Explicit prompt words | `133` |
| Validation errors | `[]` |
| Validation warnings | `['warning:final_state:stable_state_predictor:causal_remove_final_state', 'warning:affected_objects:stable_state_predictor:affected_objects', 'warning:physical_dependencies:stable_state_predictor:physical_dependencies', 'warning:dependent_regions:stable_state_predictor:dependent_regions', 'warning:must_pass_checks:stable_state_predictor:must_pass_checks']` |
| Expansion failures | `[]` |

### Input Prompt

```text
Remove the 5 of spades card from the structure.
```

### PhysicalIntent Generated Prompt

```text
Edit the input image according to this physically grounded task.
Original instruction: Remove the 5 of spades card from the structure.
Physical operation: Remove the 5 of spades card from the card structure, causing the supported section that depended on it to settle into a new stable configuration.
Target objects: ['5 of spades card']
Final stable state: {'affected_object_pose': 'glass tabletop rotates and tilts downward toward the front-left corner after the front-left support card is removed', 'support_relation': 'Any section that was relying on the 5 of spades must no longer appear artificially supported by it; the remaining cards should either retain balance via other contacts or shift to a new stable pose.', 'contact_points': 'New or remaining contact points among the cards and floor must be consistent with the revised support path.', 'secondary_effects': 'Update nearby occlusion and any shadows at the former location of the 5 of spades; preserve the rest of the scene geometry and perspective.', 'intervention': 'remove the front-left vertical 5-of-spades support card from the load-bearing card structure', 'load_path_change': 'load previously carried by the removed front-left card is redistributed to the remaining card stacks, so the local corner cannot stay in the old level pose'}
Dependent regions: ['lower-left foreground card-contact area', 'junction where the 5 of spades meets the adjacent cards', 'small floor region beneath the removed card', 'nearby shadowed/occluded edge contours', 'removed support-card bay', 'front-left glass corner', 'floor below the lowered corner', 'adjacent card contacts']
Reference cues: ['The card house is built on a flat floor.', 'The 5 of spades is clearly visible in the lower-left foreground and is angled upward into the structure.', 'The scene lighting is soft and comes from above/left enough to create mild shadows and edge shading.', 'The card surfaces are matte and white with printed suit markings.']
Preserve unchanged: ['all unrelated cards in the structure', 'background floor and wall', 'camera perspective', 'lighting direction', 'material appearance of remaining cards']
Physical dependencies to update consistently: ['support loss', 'load redistribution', 'contact change', 'occlusion change', 'contact shadow update', 'intervention_target: removed support or constraint', 'affected_object: object whose balance or load path changes', 'support_or_constraint_change: old support relation is invalid after removal', 'predicted_stable_pose: affected object must settle into a new stable pose', 'new_contact_points: final pose must create grounded contacts and contact shadows']
Must-pass visual checks: ['The 5 of spades card is absent from the structure.', 'The remaining cards do not retain an impossible unsupported pose where the removed card used to hold them.', 'Any changed contacts are physically plausible for a stable card arrangement.', 'Local shadow and occlusion near the removed card are updated consistently with its absence.', 'The removed support card is absent.', 'The glass tabletop visibly tilts downward toward the front-left corner.', 'At least one nearby non-5-of-spades card has fallen or shifted into a grounded final state.', 'Remaining adjacent cards do not all stay perfectly upright in the old support configuration.', 'New contacts, shadows, and reflections match the tilted glass and fallen-card configuration.', 'Do not allow old-state failure: glass tabletop remains level as if the front-left support still exists.', 'Do not allow old-state failure: all nearby cards remain perfectly upright in the original support configuration.', 'Do not allow old-state failure: removed 5-of-spades card reappears elsewhere on the structure or floor.', 'Do not allow old-state failure: front-left bay is filled in as a flat visual repair without a support gap.']
Treat the request as an intervention followed by a physically plausible final stable state.
Change the intervention target and also update every affected object whose support, contact, balance, or constraint changes.
Do not leave affected objects in the old stable pose if the support or constraint has been removed.
Add or update contact points, occlusion, and contact shadows required by the final stable state.
If a support object is removed, show the resulting load redistribution: visible tilt, fall, new grounded contact, or explicit uncertainty if the image evidence proves no load depended on it.
Treat these details as uncertain and do not invent unsupported specifics: ['The exact load-bearing role of the 5 of spades cannot be fully verified from the single view.', 'The precise final pose of neighboring cards after removal is not fully determinable; only a plausible stable settlement can be asserted.']
Keep the edit limited to the requested target and necessary dependent regions.
```

### PICABench Explicit Prompt

```text
Remove the front-left vertical support card—the 5 of spades—from the card structure beneath the glass tabletop. After its removal, show the final stable outcome: the front-left bay is open with a visible gap where that card used to stand; no 5-of-spades appears anywhere in the structure or on the floor. The glass tabletop has rotated and now rests tilted downward toward the front-left corner, still supported by the remaining card stacks. One nearby card that lost support (not a 5 of spades—use a clubs card face or a card back) has fallen out and now lies flat on the floor in the front-left foreground beneath the lowered glass corner. Ensure all cards and the glass have natural contact points, correct perspective, and updated shadows/reflections consistent with the new tilted glass and collapsed corner.
```

### Generated TaskProfile Summary

```json
{
  "physical_operation": "Remove the 5 of spades card from the card structure, causing the supported section that depended on it to settle into a new stable configuration.",
  "target_objects": [
    "5 of spades card"
  ],
  "affected_objects": [
    "5 of spades card",
    "adjacent supporting cards in the structure",
    "local floor-contact region",
    "local occlusion and shadow region",
    "glass tabletop",
    "remaining card structure",
    "nearby unsupported card",
    "floor beneath the lowered corner"
  ],
  "physical_dependencies": [
    "support loss",
    "load redistribution",
    "contact change",
    "occlusion change",
    "contact shadow update",
    "intervention_target: removed support or constraint",
    "affected_object: object whose balance or load path changes",
    "support_or_constraint_change: old support relation is invalid after removal",
    "predicted_stable_pose: affected object must settle into a new stable pose",
    "new_contact_points: final pose must create grounded contacts and contact shadows"
  ],
  "dependent_regions": [
    "lower-left foreground card-contact area",
    "junction where the 5 of spades meets the adjacent cards",
    "small floor region beneath the removed card",
    "nearby shadowed/occluded edge contours",
    "removed support-card bay",
    "front-left glass corner",
    "floor below the lowered corner",
    "adjacent card contacts"
  ],
  "preserve_scope": [
    "all unrelated cards in the structure",
    "background floor and wall",
    "camera perspective",
    "lighting direction",
    "material appearance of remaining cards"
  ],
  "reference_cues": [
    "The card house is built on a flat floor.",
    "The 5 of spades is clearly visible in the lower-left foreground and is angled upward into the structure.",
    "The scene lighting is soft and comes from above/left enough to create mild shadows and edge shading.",
    "The card surfaces are matte and white with printed suit markings."
  ],
  "uncertainties": [
    "The exact load-bearing role of the 5 of spades cannot be fully verified from the single view.",
    "The precise final pose of neighboring cards after removal is not fully determinable; only a plausible stable settlement can be asserted."
  ],
  "must_pass_checks": [
    "The 5 of spades card is absent from the structure.",
    "The remaining cards do not retain an impossible unsupported pose where the removed card used to hold them.",
    "Any changed contacts are physically plausible for a stable card arrangement.",
    "Local shadow and occlusion near the removed card are updated consistently with its absence.",
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
    "causal_settle_route",
    "direct_edit",
    "support_path_update",
    "shadow_and_occlusion_repair"
  ]
}
```

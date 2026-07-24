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
| Labels used by component | `{'physics_category': 'unknown', 'physics_law': 'unknown', 'edit_operation': 'remove'}` |
| Generated prompt words | `407` |
| Explicit prompt words | `133` |
| Validation errors | `['error:final_state:empty']` |
| Validation warnings | `[]` |
| Expansion failures | `[]` |

### Input Prompt

```text
Remove the 5 of spades card from the structure.
```

### PhysicalIntent Generated Prompt

```text
Edit the input image according to this physically grounded task.
Original instruction: Remove the 5 of spades card from the structure.
Physical operation: Remove the foreground 5 of spades card panel from the card-structure assembly and reconstruct the exposed area so the structure remains visually coherent and stable.
Target objects: [{'name': '5 of spades card', 'visual_role': 'foreground structural card panel', 'visibility': 'fully visible'}]
Final stable state: {}
Dependent regions: [{'region': 'lower-left foreground card panel area occupied by the 5 of spades'}, {'region': 'adjacent seam where the 5 of spades meets the rest of the structure'}, {'region': 'nearby floor/background area if briefly occluded by the removed card'}]
Reference cues: [{'cue': 'The removed card is a standard playing card with a white face and black spade symbols labeled 5.'}, {'cue': 'The structure is lit by soft diffuse light from the same direction as the rest of the scene, with no strong cast shadows.'}, {'cue': 'Nearby cards provide matching perspective, edge thickness, and surface texture for reconstruction.'}]
Preserve unchanged: [{'name': 'all other playing cards', 'detail': 'Keep their identities, positions, and patterns unchanged unless needed for seamless repair near the removal site.'}, {'name': 'overall card-structure form', 'detail': 'Preserve the rest of the assembly and camera perspective.'}, {'name': 'floor/background', 'detail': 'Do not alter the environment outside the local repair area.'}]
Physical dependencies to update consistently: [{'type': 'occlusion', 'detail': 'Neighboring cards may need edge cleanup where the removed card previously overlapped them.'}, {'type': 'support', 'detail': 'If the removed card contributed visible structural support, the remaining arrangement must still read as stable.'}, {'type': 'contact', 'detail': 'Contact edges and seams near the removal site must be redrawn coherently.'}, {'type': 'shadow', 'detail': 'Any small shadow cast by the removed card should disappear or be reduced in the exposed region.'}]
Must-pass visual checks: [{'check': 'The 5 of spades card is absent from the final image.'}, {'check': 'No obvious remnants of the removed card remain at the foreground removal site.'}, {'check': 'Adjacent card edges and overlaps look continuous and physically plausible.'}, {'check': 'The overall structure still appears intact and unchanged away from the edit region.'}]
Treat these details as uncertain and do not invent unsupported specifics: ["{'item': 'Whether the card is fully structural or partly decorative cannot be confirmed from the image alone.'}", "{'item': 'The exact hidden geometry behind the removed card is not fully visible, so the repair path must be inferred from adjacent cards.'}"]
Keep the edit limited to the requested target and necessary dependent regions.
```

### PICABench Explicit Prompt

```text
Remove the front-left vertical support card—the 5 of spades—from the card structure beneath the glass tabletop. After its removal, show the final stable outcome: the front-left bay is open with a visible gap where that card used to stand; no 5-of-spades appears anywhere in the structure or on the floor. The glass tabletop has rotated and now rests tilted downward toward the front-left corner, still supported by the remaining card stacks. One nearby card that lost support (not a 5 of spades—use a clubs card face or a card back) has fallen out and now lies flat on the floor in the front-left foreground beneath the lowered glass corner. Ensure all cards and the glass have natural contact points, correct perspective, and updated shadows/reflections consistent with the new tilted glass and collapsed corner.
```

### Generated TaskProfile Summary

```json
{
  "physical_operation": "Remove the foreground 5 of spades card panel from the card-structure assembly and reconstruct the exposed area so the structure remains visually coherent and stable.",
  "target_objects": [
    {
      "name": "5 of spades card",
      "visual_role": "foreground structural card panel",
      "visibility": "fully visible"
    }
  ],
  "affected_objects": [
    {
      "name": "5 of spades card",
      "change": "removed"
    },
    {
      "name": "adjacent supporting cards",
      "change": "may need slight re-occlusion/reconstruction"
    },
    {
      "name": "local contact/gap region",
      "change": "repaired"
    }
  ],
  "physical_dependencies": [
    {
      "type": "occlusion",
      "detail": "Neighboring cards may need edge cleanup where the removed card previously overlapped them."
    },
    {
      "type": "support",
      "detail": "If the removed card contributed visible structural support, the remaining arrangement must still read as stable."
    },
    {
      "type": "contact",
      "detail": "Contact edges and seams near the removal site must be redrawn coherently."
    },
    {
      "type": "shadow",
      "detail": "Any small shadow cast by the removed card should disappear or be reduced in the exposed region."
    }
  ],
  "dependent_regions": [
    {
      "region": "lower-left foreground card panel area occupied by the 5 of spades"
    },
    {
      "region": "adjacent seam where the 5 of spades meets the rest of the structure"
    },
    {
      "region": "nearby floor/background area if briefly occluded by the removed card"
    }
  ],
  "preserve_scope": [
    {
      "name": "all other playing cards",
      "detail": "Keep their identities, positions, and patterns unchanged unless needed for seamless repair near the removal site."
    },
    {
      "name": "overall card-structure form",
      "detail": "Preserve the rest of the assembly and camera perspective."
    },
    {
      "name": "floor/background",
      "detail": "Do not alter the environment outside the local repair area."
    }
  ],
  "reference_cues": [
    {
      "cue": "The removed card is a standard playing card with a white face and black spade symbols labeled 5."
    },
    {
      "cue": "The structure is lit by soft diffuse light from the same direction as the rest of the scene, with no strong cast shadows."
    },
    {
      "cue": "Nearby cards provide matching perspective, edge thickness, and surface texture for reconstruction."
    }
  ],
  "uncertainties": [
    {
      "item": "Whether the card is fully structural or partly decorative cannot be confirmed from the image alone."
    },
    {
      "item": "The exact hidden geometry behind the removed card is not fully visible, so the repair path must be inferred from adjacent cards."
    }
  ],
  "must_pass_checks": [
    {
      "check": "The 5 of spades card is absent from the final image."
    },
    {
      "check": "No obvious remnants of the removed card remain at the foreground removal site."
    },
    {
      "check": "Adjacent card edges and overlaps look continuous and physically plausible."
    },
    {
      "check": "The overall structure still appears intact and unchanged away from the edit region."
    }
  ],
  "route_hints": [
    {
      "hint": "Use local object removal with edge reconstruction guided by adjacent card contours."
    },
    {
      "hint": "Preserve the existing light direction and material texture while patching the occluded seam."
    },
    {
      "hint": "Maintain the surrounding geometry by re-occluding or blending only the minimal necessary region."
    }
  ]
}
```

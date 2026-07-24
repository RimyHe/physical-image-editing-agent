# PhysicalIntent Prompt Comparison

- Input prompt level: `superficial`
- Label mode: `gold`
- PICABench `explicit_prompt` is shown only as a comparison target, not as runtime input.

## picabench_0000_causality

| Field | Value |
|---|---|
| Physics category | `Mechanics` |
| Physics law | `Causality` |
| Edit operation | `remove` |
| Labels used by component | `None` |
| Generated prompt words | `0` |
| Explicit prompt words | `133` |
| Validation errors | `[]` |
| Validation warnings | `[]` |
| Expansion failures | `['expander_call_failed']` |

### Input Prompt

```text
Remove the 5 of spades card from the structure.
```

### PhysicalIntent Generated Prompt

```text

```

### PICABench Explicit Prompt

```text
Remove the front-left vertical support card—the 5 of spades—from the card structure beneath the glass tabletop. After its removal, show the final stable outcome: the front-left bay is open with a visible gap where that card used to stand; no 5-of-spades appears anywhere in the structure or on the floor. The glass tabletop has rotated and now rests tilted downward toward the front-left corner, still supported by the remaining card stacks. One nearby card that lost support (not a 5 of spades—use a clubs card face or a card back) has fallen out and now lies flat on the floor in the front-left foreground beneath the lowered glass corner. Ensure all cards and the glass have natural contact points, correct perspective, and updated shadows/reflections consistent with the new tilted glass and collapsed corner.
```

### Generated TaskProfile Summary

```json
{}
```

---
id: idea-sideboard-degenerate-board-guard
created: 2026-08-04
tags: [advisory, sideboard, honesty]
---

`advise sideboard` can return a board that is obviously unusable while reporting no
failure. Observed 2026-08-04 for a W/B Energy deck against
`decks/local-field-current.txt` (`--since 2025-08-01`):

```
=== Sideboard Recommendation (solver=ilp, field_source=custom) ===
  Budget: 15  |  Reserved: 0
  Covered weight: 0.4299
  4x Defense Grid
  4x Leyline of the Void
  // Defense Grid: ~0% of field
  // Leyline of the Void: ~12% of field
  // board coverage diagnostic: ~12% of field addressed by this board
```

Three things wrong at once, none of them flagged as a problem:

1. **It filled 8 of 15 slots and stopped.** Seven slots silently unallocated.
2. **It spent 4 slots on a card the same output says addresses ~0% of the field** —
   Defense Grid is already a known scorer-only artifact (18/26 archetypes in the
   `advise sweep` validation), so this is the tracked symmetric-self-cost gap surfacing
   again, but here it consumed a quarter of the board.
3. **~12% board coverage against an 86%-covered field is a non-answer**, and the run
   presents it in the same shape as a good recommendation.

The camp's own observed sideboard pool (Deafening Silence 86% of lists, Surgical
Extraction 69%, Disruptor Flute 66%, Stony Silence 66%, Static Prison 43%, Faerie
Macabre 40%, Containment Priest 37%) is far more useful than what the solver returned,
which is the tell that the solver had nothing to work with — plausibly downstream of
`bug-card-dimension-localized-and-new-card-gaps` (several of those staples are exactly
the cards the hoser catalog reports unknown attribution for).

Wanted: a degenerate-output guard consistent with the honest-degrade-marker pattern —
if the solver leaves slots unfilled, or board coverage falls below some fraction of
field coverage, or any selected card's own field relevance rounds to 0%, say so loudly
and name the reason rather than printing the list as if it were an answer.

```
// ⚠ DEGENERATE BOARD: 8/15 slots filled; 12% board coverage vs 86% field coverage;
// 1 selected card at ~0% field relevance (Defense Grid) — treat as no recommendation
```

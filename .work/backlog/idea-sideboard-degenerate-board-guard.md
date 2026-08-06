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

## Two more reproductions, 2026-08-05 — it is not archetype- or field-specific

Both hit while building deck deliverables, and in both cases the shipped list ignored the
advisor entirely in favour of the observed field distribution. The operator's own summary:
*"the sideboard advisor always seems to throw some recommendation that 0% of the field plays,
so we seem to always override it and just go with a well-performing recent list example."*

**(a) `advise refresh --deck <oops> --archetype "Oops! All Spells" --venues online`** — returned
a **6-card** sideboard, and its own outlier check contradicted its own picks in the same output:

```
Sideboard (15):
  4 Defense Grid
  2 Surgical Extraction
Card-count outliers (vs field modal):
  [side] Defense Grid: you run 4, field modal is 0 (94% of field at modal count)
  [side] Surgical Extraction: you run 2, field modal is 0 (82% of field at modal count)
```

Note this is the **documented generation path** for `decks/generated/` (its README step 3 says
"replace its sideboard with the refresh's recommended current-online 15") — so the documented
path for producing deck packages is currently broken, not just an advisory nit.

**(b) `advise sideboard --deck <doomsday flow-car> --archetype "Doomsday"`**, `field_source=global`
(so this is NOT a custom-field artifact) — spent **4 of 15 slots** on a card its own diagnostic
prints as irrelevant:

```
  4x Carpet of Flowers
  // Carpet of Flowers: ~0% of field
```

`Veil of Summer` (also `~0% of field`) appears in the Considering list. Meanwhile the camp's
actual consensus board — unanimous across 17/17 in-window decks — is 4 Force of Vigor /
4 Leyline of Sanctity / 3 Thoughtseize / 2 Disciple / 1 Stormbrood / 1 Foundation Breaker.

**What (b) adds to the diagnosis.** The run's own footer already states the mechanism:

> Swing magnitudes (`_SWING_DEDICATED=0.20`, `_SWING_SOFT=0.10`) are curated heuristic constants,
> NOT empirically derived from before/after-sideboard win-rate data. The coverage structure ...
> is data-driven; the per-tag swing magnitude is an estimate.

So the objective is `tag-coverage × curated-swing`, and **field relevance is only ever a printed
diagnostic — never a term in the objective**. A card that answers a tag nothing in the field
actually plays can therefore win slots on a tag-coverage technicality. The guard proposed above
is the honest-degrade half; the other half is a scoring question: should a card whose field
relevance rounds to 0% be *eligible* at all, or should relevance multiply into the objective
rather than being reported beside it?

Related: `bug-card-dimension-localized-and-new-card-gaps` (unknown attribution starves the solver
of the real staples, which is plausibly why it reaches for these cards in the first place).

---
id: idea-landbase-comparison-table
created: 2026-08-05
updated: 2026-08-05
tags: []
---

Generate a landbase comparison table modeled on the **strategic plans** peer table on the
Best Deck / Best Call ranking page — but comparing **landbases** rather than strategic plans.

Progression the user asked for:

1. all **mono-color** landbases against each other
2. all **two-color** pairs against each other
3. all **three-color** combinations against each other

...and represent **all combinations therein** — the full lattice of color-identity landbase
groupings, not just the ones carrying heavy field share.

Same shape as the plans table: peer rows with adjusted field WR, floor, agency, coverage,
grounding strata, and an expandable cell-by-cell ledger.

## Context carried over

- The plans table is the working model to copy: five curated plans, mutually exclusive primary
  assignment, match-level aggregation (not averages of rendered archetype percentages), the
  page's `n>=8` measured gate, and a structural same-plan 50% diagonal that never sets the floor.
  See `docs/analysis/best-call-ranking.md` and `scripts/refresh_best_call_ranking.py`.
- **Known data constraint:** `cards.colors` is a VARCHAR queried with `LIKE`, and there is no
  `color_identity` column (same gap recorded in the camp-discovery-misses-color-splits finding).
  Deriving landbase color identity therefore needs a real derivation step, not a column read.

## The fetchland trap (checked against the card dimension, 2026-08-05)

Do not classify a manabase by summing `produced_mana`. The dimension supports this work but has
one hole that would silently wreck a Legacy landbase table.

What is actually there: `cards.is_land` exists, there are **1,436 land cards**, and
`produced_mana` is populated for **96%** of them. `cards.colors` is *empty* for lands (correct —
lands are colorless objects), so the "no color_identity column" note above applies to spells;
for manabases `produced_mana` is the right column.

The hole is fetchlands:

```
Underground Sea    produced_mana = 'BU'      Land — Island Swamp
Undercity Sewers   produced_mana = 'BU'      Land — Island Swamp
Cavern of Souls    produced_mana = 'BCGRUW'  Land
Ancient Tomb       produced_mana = 'C'       Land
Wasteland          produced_mana = 'C'       Land
Polluted Delta     produced_mana = ''        Land        <-- produces nothing
```

A fetchland produces no mana; it searches. So a naive classifier scores **Polluted Delta as
colorless** and reads a fetch-heavy Legacy manabase as mostly-colorless — precisely inverting the
thing the table is meant to compare. In this format that is not an edge case: the decks with the
most interesting landbases are the most fetch-dense.

Resolving a fetch to the colors it can *reach* means reading its oracle text ("Search your library
for an **Island or Swamp** card...") and mapping those subtypes to colors — which is a small slice
of the `epic-card-semantics-ir` rules layer. Two consequences worth deciding up front:

1. This idea has a **real dependency** on card-semantics work, or else on a hand-maintained fetch →
   fetchable-types table (a `curated-json-resource-loader` shaped file). Pick deliberately; the
   hand-rolled table is the kind of thing that rots quietly as sets print new fetches.
2. Whatever resolves fetches should be **shared** with `idea-discovery-color-identity-feature` and
   `idea-color-variant-conditioned-matchup-cells` — all three want a color dimension, and this is
   the piece with the actual difficulty in it. Build it once.

Also note the correct denominator question this raises: is a deck's "landbase color identity" the
colors its lands *produce*, the colors they can *fetch into*, or the colors its spells *demand*?
Those three give different answers for exactly the decks (Lands, Tron, 4c piles) most worth a row.

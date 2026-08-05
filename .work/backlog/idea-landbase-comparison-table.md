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

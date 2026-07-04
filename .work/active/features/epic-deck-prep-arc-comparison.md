---
id: epic-deck-prep-arc-comparison
kind: feature
stage: drafting
tags: [advisory, analysis, dogfooding]
parent: epic-deck-prep-arc
depends_on: [epic-deck-prep-arc-dimir-boards, epic-deck-prep-arc-doomsday-tempo]
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# Dimir Tempo vs Doomsday Tempo — cross-meta comparison

## Brief

Head-to-head analysis of the two optimized decks (from dimir-boards and doomsday-tempo)
across BOTH metas: adaptive matchup matrix vs each field, positioning (Ū best-deck / S
best-call lenses), coverage/uncovered-tail from the board packages, head-to-head matchup
cell, and cost/collection deltas. Every claim gated per [[analysis-statistical-context-gates]]
(regime-currency, sample tier, CI separation, confounds) — the 2026-06-27 finding (Dimir
0.483 vs Doomsday 0.501 on the regime-clean local field, both leans) is the prior to
re-test with current data, not assume. Deliverable: comparison doc in `decks/` (+
`advise compare` / viz surfaces where they exist).

## Epic context

- Parent epic: `epic-deck-prep-arc`
- Position: joins the two deck strides; feeds the reflection feature.

## Inherited design decisions

- Compare across both metas (local field file + online provenance field); divergences
  between metas are first-class output (venue-divergence pattern), never blended.

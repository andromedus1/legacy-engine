---
id: epic-deck-prep-arc-comparison
kind: feature
stage: done
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

## Results (2026-07-04, single-stride)

Venue divergence IS the finding: the local meta → Dimir (EV 50.9 vs 49.6, P(A>B)=0.56; blue-heavy
room hits Dimir's best cells), online → Doomsday (50.4 vs 48.5, P=0.37; D&T/Lands/Tron mass
+ Doomsday #1 in online positioning). Reverses the 2026-06-27 lean on 3× corpus. Head-to-head:
Dimir 54% (thin). Caveats: archetype-level cells (variant-conditioned cells parked as
idea-variant-conditioned-matchup-cells), online imputation mass, ±10pt CIs. Practical:
Dimir fully owned; Doomsday gated on a ~$1k main. Bottom line: stay Dimir for the local meta;
Doomsday is the online/field-drift option with a concrete composition trigger.
Deliverable: decks/dimir-vs-doomsday-tempo-comparison.md.

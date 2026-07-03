---
id: feature-sb-field-weighted-scorer-wiring
kind: story
stage: implementing
tags: [advisory]
parent: feature-sb-field-weighted-scorer
depends_on: [feature-sb-field-weighted-scorer-impact]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Wire impact into the coverage model + draw-prob copy-shaping in the ILP

## Brief

Replace `advise sideboard`'s scoring-core inputs in place: element weight becomes
`field_share × swing × impact(best hoser | my deck, that opp)`, and the per-copy marginal
(`_u_redundancy`/`_redundancy_penalty`) becomes draw-probability-driven so the ILP tapers copies.
Keep the ILP/greedy/τ/hedge machinery unchanged. Preserve a byte-identical path when impact
inputs are absent (honest-degrade + no-collection contract).

## Implementation

Covers parent feature **Units B3 + B4** — see `feature-sb-field-weighted-scorer` § Implementation
Units. File: `src/legacy_engine/advisory/sideboard.py` (`_build_coverage_model` element weights +
the copy-shaping). Tests: extend `tests/test_sideboard.py` (impact-modulated weights, copy taper,
byte-identical no-impact regression guard); re-baseline `tests/test_recommendation_coverage.py`.

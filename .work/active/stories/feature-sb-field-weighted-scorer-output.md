---
id: feature-sb-field-weighted-scorer-output
kind: story
stage: implementing
tags: [advisory]
parent: feature-sb-field-weighted-scorer
depends_on: [feature-sb-field-weighted-scorer-wiring]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Explainable breakdown + coverage% diagnostic + field-share uncertainty

## Brief

Make the score auditable and honest: surface each recommended card's `ImpactBreakdown`
(centrality/symmetry/castability/draw-prob) in the `advise sideboard` output; render coverage% as a
labeled DIAGNOSTIC line (not the objective); apply Dirichlet field-share uncertainty (reuse
`advise positioning`'s machinery) to shrink tiny-share matchup weights and annotate confidence
tier; keep thin/uncovered field honest-degrade-labeled.

## Implementation

Covers parent feature **Unit B5** — see `feature-sb-field-weighted-scorer` § Implementation Units.
Files: `src/legacy_engine/advisory/sideboard.py` + the `advise sideboard` CLI render in
`src/legacy_engine/cli.py`. Tests: explainable-breakdown presence + coverage% diagnostic render in
`tests/test_sideboard.py`; uncertainty shrink/annotate behavior.

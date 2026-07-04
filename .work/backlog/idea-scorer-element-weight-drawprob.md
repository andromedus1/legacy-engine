---
id: idea-scorer-element-weight-drawprob
created: 2026-07-03
tags: [advisory, sideboard]
---

# Scorer refinement: drop draw-prob from the element-weight impact multiplier

Surfaced as a nit in the Feature B (`feature-sb-field-weighted-scorer`) deep review (2026-07-03).

In `_build_coverage_model` the impact-modulated element weight uses
`impact(best_hoser, opp, copies=1).score()`, which includes a `draw_probability(1) ≈ 0.4`
factor. Since it's constant across all elements it doesn't change the argmax (which cards win),
but it uniformly deflates absolute `weight·g` magnitudes by ~0.4 — and the natural-budget τ stop
reads absolute magnitudes, so the impact-ON path may commit a slightly different dedicated-core
size than intended.

The draw dimension is *already* owned by the per-copy shaping (Unit B4's draw-prob redundancy
curve). Including `draw_prob(1)` in the element weight too arguably double-counts the draw axis.

**Fix direction**: compute the element-weight impact multiplier from `centrality × symmetry ×
castability` only (the "does this tag have a good, castable, non-self-hosing answer at all"
question), leaving the draw-probability dimension entirely to the copy-shaping. Then re-check the
τ natural-budget stop calibration under the impact-ON path. Low-risk, ranking-preserving; verify
no dedicated-core-size regression on the existing coverage tests.

Also noted (lower value): `castability_factor` accepts `opp_archetype` but doesn't branch on it
yet (signature parity for a future archetype-keyed `cast_requires`) — fine as-is.

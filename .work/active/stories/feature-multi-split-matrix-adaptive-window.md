---
id: feature-multi-split-matrix-adaptive-window
kind: story
stage: implementing
tags: [advisory]
parent: feature-multi-split-matrix
depends_on: [feature-multi-split-matrix-core-tally]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Adaptive multi-split builder + window entry point

## Brief

The era-aware half (trickiest unit): `build_multi_split_adaptive` mirrors
`build_adaptive_matrix`'s skeleton (one maximal scan per distinct horizon, per-window pooled
hierarchy buckets, cross-era prior overrides via cached pre-boundary scans), with camp horizons
resolved exact -> parent -> ban-only through the new explicit `camp_parent` param on
`era_horizons` (no prefix parsing for multi-parent). Plus the thin composition layer:
`build_multi_split_inputs` in `advisory/window.py` (same `WindowResolution` mode dispatch +
audit lines; `build_advisory_inputs` and the ~15 spine call sites get ZERO edits) and
`staged_split_parents()` in `archetype/discovered.py`. Ships the adaptive half of the parity
test including `cell_windows`, `horizon_meta`, and cross-era `prior_source` label parity.

## Implementation

Parent feature `feature-multi-split-matrix` — Units 3 and 4 of `## Implementation Units`
(exact signatures, notes, and acceptance criteria there). Tests: the adaptive-parity part of
`tests/test_matchup_multi_split.py` + `tests/test_advisory_window_multi_split.py`. Hermetic
DBs only — never the default DB; use the explicit `horizons=` hook to pin windows
deterministically where era rows would be noisy.

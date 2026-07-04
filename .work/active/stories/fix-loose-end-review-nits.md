---
id: fix-loose-end-review-nits
kind: story
stage: done
tags: [analytics, viz, testing]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: null
created: 2026-06-14
updated: 2026-06-15
---

Low/non-blocking nits from the reviews of the two loose-end features (both approved → done):
- (Low) `analytics/trends.py::biggest_movers` iterates a set, so equal-|delta| ties select
  nondeterministically — add a secondary sort key (e.g. archetype name) for stable output.
- (Low) coverage-consumers Fix-4 test (`test_positioning_s_none_at_zero_coverage`) is non-exercising
  (archetype not in matrix → takes the early branch, never hits the new s_computable guard); tighten it
  to actually exercise the guard.
- (Low) coverage-consumers: `viz/specs.py::spec_positioning` bar-fade still keys off `ranking.low_coverage`
  (min_coverage, default 0) rather than the new `coverage_caveated` set — the design intended the
  threshold-consistent fade. Visual cue only (no two-S contract impact).
- (Low) wrw-windowed test asserts only `<=` on windowed deck counts; a strict-less-than with a known
  fixture would be stronger.

## Resolution (2026-06-15)
All four fixed:
- **trends tie-sort**: `biggest_movers` now sorts by `(-abs(delta), archetype)` — |delta| desc with
  name asc as a deterministic tiebreak (was iterating a set). Docstring updated.
- **positioning test**: rewrote `test_positioning_s_none_at_zero_coverage` to use `make_rounds_corpus`
  (Control vs Combo, n=30 → Control in matrix) scored against a field of archetypes it has no covered
  cell against → genuinely hits `s_computable=False`/NaN and asserts the guard maps it to None. The old
  version scored an absent archetype and took the early no-match branch.
- **viz fade**: `spec_positioning` opacity now keys off `coverage_caveated` (the 0.85 `S*` threshold),
  not `low_coverage` (min_coverage, default 0). Field renamed `coverage_caveated`; added a regression
  test that a caveated-but-not-low_coverage deck still fades.
- **wrw assert**: `test_wrw_windowed_uses_window_deck_counts` now pins exact counts (full=4, window=2)
  and asserts strict `<`.

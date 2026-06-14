---
id: idea-loose-end-review-nits
created: 2026-06-14
tags: [analytics, viz, testing]
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

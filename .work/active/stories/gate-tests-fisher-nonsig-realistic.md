---
id: gate-tests-fisher-nonsig-realistic
kind: story
stage: done
tags: [testing]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: tests
created: 2026-07-04
updated: 2026-07-04
---

# Non-significant Fisher case tested with degenerate 0.0-diff split

## Priority
High

## Spec reference
Item: `epic-sb-config-evaluation-matchup-slot-test` (Unit 1). AC: 'significant is False for a constructed non-significant split (e.g. 38% n=71 vs 46% n=67 -> p~0.33).'

## Gap type
Near-vacuous test — test_near_5050_not_significant uses 1/2 vs 1/2 (diff exactly 0.0); the Null-Rod cautionary case (sizeable non-zero diff, NOT significant) is untested.

## Suggested test
Construct cohorts ~38% (n~71) vs ~46% (n~67); assert diff materially non-zero AND significant is False with p in a sane band.

## Test location
`tests/analytics/test_slot_test.py::TestStats`

## Resolution
Replaced `test_near_5050_not_significant` (1/2 vs 1/2, diff exactly 0.0) with
`test_sizeable_nonzero_diff_not_significant`: WITH cohort 27/71 (38.0%), WITHOUT cohort 31/67
(46.3%) — the exact split named in the AC, matching the module docstring's "Null Rod vs Blue
Artifacts" cautionary example. Asserts `abs(diff) > 0.05` (material, not the degenerate 0.0 case),
`0.05 < p_value < 0.6` (non-significant, sane band — actual p≈0.389), and `significant is False`.

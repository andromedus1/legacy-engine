---
id: gate-tests-lift-lower-clamp
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

# Negative lift lower clamp (floor 0.0) untested

## Priority
Medium

## Spec reference
Item: `epic-sb-config-evaluation-config-comparator` (Unit 1). AC: 'Lifts ... clamped to [0,1].'

## Gap type
Boundary untested — only the <=1.0 clamp has a test.

## Suggested test
Negative lift larger than base WR; assert wr_a_adj == 0.0 and EV finite/sane.

## Test location
`tests/advisory/test_compare.py::TestPointEngine`

## Resolution
Added `test_lift_clamped_to_zero` — a -0.95 lift on a 0.6 base WR; asserts `wr_a_adj == 0.0`
(floors, doesn't go negative) and `ev_a_adj` is finite and within `[0, 1]`.

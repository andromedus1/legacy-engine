---
id: gate-tests-lift-lower-clamp
kind: story
stage: drafting
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

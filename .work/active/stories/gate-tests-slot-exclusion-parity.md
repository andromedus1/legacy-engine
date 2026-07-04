---
id: gate-tests-slot-exclusion-parity
kind: story
stage: implementing
tags: [testing]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: tests
created: 2026-07-04
updated: 2026-07-04
---

# Slot-test exclusion parity: byes + unmatched untested

## Priority
High

## Spec reference
Item: `epic-sb-config-evaluation-matchup-slot-test` (Unit 1). AC: 'Mirrors / byes / draws / ambiguous / unmatched are excluded identically to compute_match_results.'

## Gap type
Boundary partitions untested — bye rows (empty p2) and unmatched (archetype None) uncovered; no totals-parity check vs compute_match_results.

## Suggested test
Extend the hermetic _build_slot_db corpus with a bye + an unmatched row; assert cell n's unchanged (optionally equal compute_match_results decisive count).

## Test location
`tests/analytics/test_slot_test.py::TestBuckets`

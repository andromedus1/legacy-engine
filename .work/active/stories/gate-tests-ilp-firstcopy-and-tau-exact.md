---
id: gate-tests-ilp-firstcopy-and-tau-exact
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

# ILP option-value first-copy-only + tau exact-stop weaker than greedy

## Priority
Medium

## Spec reference
Items: `feature-sfv-option-value` (first-copy-only verified only for greedy/considering-pool) + `dedicated-core` ('ILP same' — test asserts only sum<4, not exactly-2).

## Gap type
Valid partition untested on one solver of a two-solver contract.

## Suggested test
ILP solve, budget=2, one bonused multi-copy card; assert bonus credited once (compare greedy traced gains). Strengthen test_ilp_stops_at_tau to the exact stop count.

## Test location
`tests/test_sideboard.py::TestOptionValueSolverWiring`, `::TestNaturalBudgetTau`

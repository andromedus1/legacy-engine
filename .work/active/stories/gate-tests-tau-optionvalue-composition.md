---
id: gate-tests-tau-optionvalue-composition
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

# Pin + document the tau-stop x option-value-bonus composition

## Priority
High

## Spec reference
Seam: `epic-sideboard-core-and-hedge-dedicated-core` ('stop when marginal fails to clear tau') x `feature-sfv-option-value` (first-copy additive bonus). In _greedy_solve the bonus is added to gain BEFORE the best_gain <= tau comparison, so a bonus can resurrect a sub-tau card past the natural-budget floor. Unspecified + untested.

## Gap type
Spec silence at a seam + no test combines tau>0 with an active option_value_bonus in any solver.

## Suggested test
DECISION (recorded here for the implementer): bonus-resurrection past tau is INTENDED — option-value is insurance-like and deliberately additive (matches the accepted 6->9 board-growth behavior from the option-value review). Write the test pinning that: a card whose coverage marginal is just below tau and whose bonus pushes it just above IS selected; mirror expectation for ILP; and document the intent in the tau + bonus docstrings (one sentence each, present-tense).

## Test location
`tests/test_sideboard.py` new `TestTauOptionValueComposition`

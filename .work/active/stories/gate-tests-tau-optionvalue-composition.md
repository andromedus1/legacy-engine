---
id: gate-tests-tau-optionvalue-composition
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

## Resolution
Added `TestTauOptionValueComposition` (tests/test_sideboard.py) with 4 tests on a single-card,
single-element model (base first-copy gain 0.05, τ=0.06 — base gain does NOT clear τ):
- `test_greedy_without_bonus_natural_stop_excludes_card` / `test_ilp_without_bonus_natural_stop_excludes_card`
  pin the baseline (no bonus → natural-budget stop fires, card excluded) so the resurrection
  tests below are non-vacuous.
- `test_greedy_bonus_resurrects_card_past_tau` / `test_ilp_bonus_resurrects_card_past_tau` add
  a bonus (0.02) that lifts the combined gain to 0.07 (> τ) and assert the card IS selected in
  both solvers — pinning the DECISION that bonus-resurrection past τ is intended.
Added the two authorized present-tense sentences to `src/legacy_engine/advisory/sideboard.py`:
one in `_greedy_solve`'s `option_value_bonus` docstring paragraph (bonus is added before the τ
comparison, can resurrect a card), and one in the natural-budget-stop inline comment (a
bonus-resurrected pick is intended, not a bug). No other src changes.
All new tests pass; full suite green (see gate-cruft-test-helper-duplication resolution for the
final count).

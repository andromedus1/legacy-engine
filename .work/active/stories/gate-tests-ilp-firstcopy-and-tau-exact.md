---
id: gate-tests-ilp-firstcopy-and-tau-exact
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

## Resolution
Added `test_ilp_first_copy_only_bonus_credited_once_not_per_copy` to `TestOptionValueSolverWiring`:
card A (max_copies=2, bonused) + card B (max_copies=1, no bonus, strict alternative), budget=2,
numbers chosen so crediting the bonus ONCE (correct) picks A+B (total 0.145) while a per-copy-credited
bonus (the encoding bug this guards against) would instead pick AA (0.175 > 0.145 in the buggy
case, vs. 0.125 < 0.145 correctly). Verified empirically that both greedy and the real ILP (PuLP/CBC)
agree on A+B — **the ILP first-copy test PASSED, validating the `p_c` presence-indicator encoding
credits the option-value bonus exactly once per card, not per copy.** No production bug found here.
Strengthened `test_ilp_stops_at_tau` (`TestNaturalBudgetTau`) from `sum(cards.values()) < 4` to the
exact stop count `cards.get("Top", 0) == 2`, mirroring greedy's already-exact
`test_greedy_stops_at_tau`. Full suite green.

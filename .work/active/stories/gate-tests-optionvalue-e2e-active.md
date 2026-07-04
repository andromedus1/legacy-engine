---
id: gate-tests-optionvalue-e2e-active
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

# Option value never runs ACTIVE end-to-end through recommend_sideboard

## Priority
High

## Spec reference
Item: `feature-sfv-option-value` (integration) + seam with hedge-allocator/output-contract. Every integration test uses a counts-less field so the bonus path no-ops; natural_budget_count-excludes-insurance only tested with option-value OFF.

## Gap type
E2E seam untested with real conditions.

## Suggested test
One hermetic corpus test with a counts-backed FieldDistribution, smart=True, hedge='expected', default alpha: assert output differs from alpha=1.0; natural_budget_count still equals pre-hedge core; insurance is a subset of cards; total <= budget.

## Test location
`tests/test_sideboard.py::TestOptionValueRecommendSideboardIntegration`

## Resolution
Added `test_option_value_active_e2e_with_counts_backed_field`. Uses
`TestHedgeIntegrationNonVacuous._two_tag_corpus()` with a counts-backed
`build_custom_field({"Reanimator": 0.85, "BigMana": 0.15}, counts={"Reanimator": 85, "BigMana": 15})`
through the real `HOSER_CATALOG`, `smart=True`, `hedge="expected"`. Empirically verified (before
writing assertions) that with the real catalog the final card SETS coincide between default alpha
and alpha=1.0 on this corpus, so "differs from alpha=1.0" is asserted on the greedy trace's
marginal gains (which DO differ — the bonus is added to the gain at every step, and even
same-final-pick paths show a different trace) rather than on `.cards`, which is not guaranteed to
differ and would have made the test flaky/corpus-dependent if asserted directly. Also asserts:
`natural_budget_count` equals an independently-computed `hedge="off"` run's total (8 == 8, verified
empirically), `insurance_cards <= set(cards)`, and `sum(cards.values()) <= budget`. Full suite green.

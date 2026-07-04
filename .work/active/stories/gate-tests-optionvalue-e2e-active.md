---
id: gate-tests-optionvalue-e2e-active
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

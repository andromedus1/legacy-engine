---
id: feature-ranking-honesty-guards-ranking-evidence-contract
kind: story
stage: done
tags: [advisory, analytics]
parent: feature-ranking-honesty-guards
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Explicit ranking evidence contract

## Brief

Repair the false-zero P(best) coverage path by making the matchup sample gate explicit at the shared
ranking boundary, while preserving the generic engine's current n>=30 default. Carry complementary
measured/imputed field-share evidence and pin the multi-split camp regression under deterministic MC.

## Implementation

Implement Unit 1 in the parent feature's `## Implementation Units` section. Do not change page
presentation or regime-currency behavior in this story.

## Implementation notes

- Execution capability: inherited frontier model at high effort; this repairs a statistically
  consequential shared ranking contract.
- Review weight: standard (caller).
- Files changed: `advisory/positioning.py` and `tests/test_positioning.py`.
- Tests added/removed: added explicit n=7/8/29/30 gates, invalid-gate fail-fast, complementary
  imputation shares, camp-label coverage, deterministic shared-budget, and empty-result tests; no
  tests removed.
- Simplification: the existing covered-cell predicate remains the SSOT and now accepts an optional
  gate; generic callers retain the display-gate path.
- Discrepancies from design: the camp regression is hermetic over the same rectangular ranking view
  contract using a synthetic camp label, avoiding a redundant database fixture already covered by
  the multi-split matrix parity suite.
- Adjacent issues parked: none.
- Verification: `tests/test_positioning.py tests/test_matchup_multi_split.py` — 151 passed.

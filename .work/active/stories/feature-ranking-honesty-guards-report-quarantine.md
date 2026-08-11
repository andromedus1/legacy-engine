---
id: feature-ranking-honesty-guards-report-quarantine
kind: story
stage: implementing
tags: [advisory, analytics]
parent: feature-ranking-honesty-guards
depends_on: [feature-ranking-honesty-guards-ranking-evidence-contract]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Best Call candidacy and imputation quarantine

## Brief

Consume the repaired ranking evidence contract in the Best Call generator and candidate-list CLI.
Assert displayed/ranking coverage parity, exclude inactive camps from headline probability mass,
make genuine zero-cell degradation loud, and add the fixed default label plus opt-in evidence strata.

## Implementation

Implement Unit 2 in the parent feature's `## Implementation Units` section after
`feature-ranking-honesty-guards-ranking-evidence-contract` is done.

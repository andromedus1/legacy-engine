---
id: epic-recurrent-stable-era-evidence-future-validation-common-case-scoring
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-future-validation
depends_on: [epic-recurrent-stable-era-evidence-future-validation-origin-refit]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Score identical future cases and coverage

## Brief

Build one estimator-independent future-case manifest and evaluate every frozen method on identical
decisive non-mirror matches with proper scores, calibration, interval behavior, coverage,
concentration, imputation, exclusions, and honest support censoring.

## Implementation

Implement Unit 3, **Common-case proper scores, calibration, intervals, and coverage**, from the
parent feature. Service/refusal affects policy coverage only and never removes a row from all-case
predictive comparison.

## Acceptance

Satisfy every Unit 3 acceptance criterion in the parent feature, including identical denominators,
deterministic proper/calibration/interval metrics, typed censoring, and candidate-independent
exclusions.

## Tests

Implement the scoring and future-case suites named by Unit 3 with hand-computed metrics, outcome
swaps, refusal attacks, event-block predictive intervals, novel labels, and thin-support cases.

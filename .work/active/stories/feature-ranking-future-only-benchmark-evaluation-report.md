---
id: feature-ranking-future-only-benchmark-evaluation-report
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: feature-ranking-future-only-benchmark
depends_on: [feature-ranking-future-only-benchmark-prediction-freeze]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Future-only evaluation, external comparators, and operator report

## Brief

Score immutable forecasts against later event-grouped outcomes, report proper/calibration/rank/regret
evidence and all support/censoring states, accept optional dated external snapshots, and expose the
two-phase benchmark through a hermetic CLI and generated report.

## Implementation

Implement Unit 3 in the parent feature's `## Implementation Units` section after prediction freeze
is complete. Evaluation must remain read-only with respect to estimator choice and production state.

---
id: epic-recurrent-stable-era-evidence-future-validation-decision-regret
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

# Replay the shared decision policy and event-block regret

## Brief

Apply every estimator to one frozen action/field/policy contract, charge abstention through the
current-only fallback, and compute paired whole-event decision regret with honest support, practical-
tie, oracle-stability, missing-action, and joint-draw censoring.

## Implementation

Implement Unit 4, **Frozen decision policy and paired event-block regret**, from the parent feature.
Prediction quality and decision quality remain independent required evidence surfaces.

## Acceptance

Satisfy every Unit 4 acceptance criterion in the parent feature: common actions/field/oracle,
current-only fallback cost, whole-event dependence, exhaustive censors, and independent predictive
versus decision conclusions.

## Tests

Implement `tests/advisory/test_recurrent_validation_decision.py` with stable ties, mirrors, refusals,
duplicate-event rows, missing actions, unstable oracles, invalid joint draws, and score/regret
divergence.

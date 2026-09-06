---
id: epic-recurrent-stable-era-evidence-future-validation-common-case-scoring
kind: story
stage: done
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

## Implementation notes

- Added estimator-independent future-case manifests with stable match/event/deck and field-mass
  digests.
- Added all-case log-loss/Brier evaluation that treats missing candidate probabilities as invalid
  rather than deleting difficult cases, while keeping served coverage separate.

## Verification evidence

- `PYTHONPATH=. .venv/bin/pytest -q tests/advisory/test_recurrent_validation_scoring.py` — 2 passed.
- `uv run ruff check src/legacy_engine/advisory/recurrent_validation.py tests/advisory/test_recurrent_validation_scoring.py` — passed.

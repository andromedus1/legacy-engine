---
id: epic-recurrent-stable-era-evidence-certification-family-equivalence
kind: story
stage: done
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-certification
depends_on: [epic-recurrent-stable-era-evidence-certification-guards-support]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Positive equivalence and whole-family error control

## Brief

Implement Unit 3 from the parent feature: recompute component and omnibus discrepancies on untouched
certification events, form one normalized whole-event bootstrap band across the frozen candidate
family, and emit auditable certified/rejected/inconclusive statistical decisions without treating
non-significance as equivalence.

## Implementation

See `epic-recurrent-stable-era-evidence-certification` Unit 3 and its exact interfaces,
implementation notes, and acceptance criteria. Candidate calibration profiles may expose statistical
diagnostics but cannot emit final certified authority.

Review weight remains `standard` at the parent feature boundary.

## Acceptance

- Certification requires every simultaneous upper bound inside its margin; lower-bound failures
  reject; straddling/underpowered evidence abstains.
- Adding family members cannot narrow existing bands, and input order/outcomes cannot change results.
- Outcome-blind positive and false-reunion controls exercise every named channel.

## Tests

Run focused equivalence/control tests plus all prerequisite story tests, Ruff on touched files, and
compileall as specified by the parent feature.

## Implementation notes

- Execution capability: inline standard implementation; all candidates enter one canonical family
  and one pure whole-event bootstrap path.
- Review weight: standard (parent/caller default).
- Files changed: `src/legacy_engine/analytics/eras/certification.py` and
  `tests/analytics/eras/test_certification_controls.py`.
- Tests added/removed: stable positive equivalence, named component shift, semantic veto ordering,
  candidate-profile authority cap, family-growth monotonicity, and input-order determinism.
- Simplification: component and omnibus channels share one normalized max-statistic band; no
  equality-test or candidate-specific threshold path exists.
- Discrepancies from design: the v1 bootstrap is a conservative event-resampling implementation
  with fixed RBF MMD² and deterministic per-candidate seeds; checked-in control evidence remains
  represented by the profile digest and is not tuned from outcomes.
- Adjacent issues parked: none.

## Verification evidence

- `.venv/bin/pytest -q tests/analytics/eras/test_certification_controls.py` — 6 passed.

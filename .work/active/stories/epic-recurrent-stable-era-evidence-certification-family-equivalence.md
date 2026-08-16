---
id: epic-recurrent-stable-era-evidence-certification-family-equivalence
kind: story
stage: implementing
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

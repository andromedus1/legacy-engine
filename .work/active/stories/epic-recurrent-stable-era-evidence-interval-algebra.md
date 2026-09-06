---
id: epic-recurrent-stable-era-evidence-interval-algebra
kind: story
stage: done
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-interval-consumption
depends_on: [epic-recurrent-stable-era-evidence-certification]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Normalized interval algebra and certificate adapter

## Brief

Implement Unit 1 from the parent feature: canonical disjoint half-open atoms, exact-run certificate
validation, independent analysis clocks, current-reference assembly, and scalar current-only/camp
fallback through the same interval authority.

## Implementation

See `epic-recurrent-stable-era-evidence-interval-consumption` Unit 1 for exact interfaces, decisions,
notes, and acceptance criteria. Preserve the certification dependency's immutable ids, final-status
authority, exact-id-only read, explicit current reference, and parent-not-camp contract. Require a
separate knowledge-availability timestamp for as-known-then expansion; do not reinterpret
`certification_as_of` as artifact availability.

## Acceptance

- Interval normalization/intersection is deterministic, gap-preserving, half-open, and provenance-
  preserving.
- Only exact promoted certified components expand one explicitly retained current reference.
- Future/unproven knowledge abstains, and camps remain scalar current-only.

## Tests

Run focused interval/certificate-adapter tests, existing certification/era tests, Ruff on touched
files, and compileall as specified by the parent feature.

## Implementation notes

- Added `AnalysisClock`, `EligibilitySourceRef`, `EligibilityAtom`, and `EntityEligibility` to the
  shared era consumption seam.
- Implemented deterministic endpoint sweep normalization and commutative provenance-preserving
  intersection with exclusive `data_until` clipping.
- Implemented exact certification-run lookup with immutable availability enforcement, as-known-then
  source-date validation, retrospective labeling, explicit current reference, and camp current-only
  fallback. Scalar horizons compile through the same atom authority.

## Verification evidence

- Interval normalization/intersection smoke fixtures passed.
- `PYTHONPATH=. .venv/bin/pytest -q tests/analytics/eras/test_certification_run.py tests/analytics/eras/test_consume.py` — 26 passed.
- `PYTHONPATH=. .venv/bin/python -m compileall -q src/legacy_engine/analytics/eras/consume.py` — passed.

## Simplifications/deviations

- The new public interval authority is additive; legacy scalar callers remain unchanged until the
  selection checkpoint routes them through it.

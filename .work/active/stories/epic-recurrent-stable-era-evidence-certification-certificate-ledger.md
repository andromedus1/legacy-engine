---
id: epic-recurrent-stable-era-evidence-certification-certificate-ledger
kind: story
stage: done
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-certification
depends_on: [epic-recurrent-stable-era-evidence-certification-family-equivalence]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Immutable certificate run and exact-id ledger

## Brief

Implement Unit 4 from the parent feature: compose the exact discovery/partition/guard/equivalence
pipeline, persist immutable versioned certificates and explicit no-candidate entities, and expose
canonical exact-id reads as the only downstream handoff.

## Implementation

See `epic-recurrent-stable-era-evidence-certification` Unit 4 and its exact interfaces,
implementation notes, and acceptance criteria. Only certificates with final status `certified` may
become historical interval inputs; this story does not implement matchup consumption.

Review weight remains `standard` at the parent feature boundary.

## Acceptance

- Every admitted/refused/abstained interval and every no-candidate entity round-trips with complete
  partition, semantic, support, context, equivalence, configuration, and hash evidence.
- Exact retries are idempotent, divergent collisions fail, and no latest/substitute read exists.
- Rejected/inconclusive/camp/gap evidence cannot be consumed as a certified historical component.

## Tests

Run focused run/store integration tests, all certification/discovery/era tests, Ruff on touched
files, and compileall as specified by the parent feature.

## Implementation notes

- Execution capability: inline standard implementation; composition and storage are one exact-id
  boundary and remain outcome-free.
- Review weight: standard (parent/caller default).
- Files changed: `src/legacy_engine/analytics/eras/certification_run.py`,
  `src/legacy_engine/analytics/eras/certificate_store.py`,
  `src/legacy_engine/analytics/eras/__init__.py`, and
  `tests/analytics/eras/test_certification_run.py`.
- Tests added/removed: no-candidate/degraded entity persistence, exact retry round-trip, absent
  ledger honesty, and immutable payload refusal.
- Simplification: one canonical JSON row is the derived DuckDB cache; exact IDs are the only read
  path and there is no latest/status substitute.
- Discrepancies from design: the run composes semantic facts into source boundaries only when the
  discovery manifest recorded a non-empty boundary catalog; independent pending monitor facts do
  not mutate an otherwise empty discovery source identity.
- Adjacent issues parked: none.

## Verification evidence

- `.venv/bin/pytest -q tests/analytics/eras/test_certification_run.py` — 3 passed.

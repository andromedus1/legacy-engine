---
id: epic-recurrent-stable-era-evidence-certification-partition-contract
kind: story
stage: done
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-certification
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Deterministic event partition and certification corpus

## Brief

Implement Unit 1 from the parent feature: repair the discovery handoff so nomination uses only a
deterministic whole-event discovery partition, construct the disjoint certification corpus, bind
both roles into immutable manifests, and reject any legacy/full-corpus or digest-mismatched run
before certification.

## Implementation

See `epic-recurrent-stable-era-evidence-certification` Unit 1 and its exact interfaces,
implementation notes, and acceptance criteria. This story owns the cross-item discovery-manifest
correction required for valid certification; it does not implement statistical gates.

Review weight remains `standard` at the parent feature boundary.

## Acceptance

- Event roles are atomic, disjoint, exhaustive, cutoff-safe, and deterministic.
- Discovery candidates cannot depend on certification-role facts, outcome relations, or future rows.
- Only an exact partition-marked discovery run can open the certification boundary.

## Tests

Run focused partition/source/discovery-run tests, the existing discovery suite, Ruff on touched
files, and compileall as specified by the parent feature.

## Implementation notes

- Execution capability: inline standard implementation; the partition boundary is cohesive with
  discovery composition and has no independent ownership surface.
- Review weight: standard (parent/caller default).
- Files changed: `src/legacy_engine/analytics/eras/certification.py`,
  `src/legacy_engine/analytics/eras/certification_source.py`,
  `src/legacy_engine/analytics/eras/discovery_run.py`, `src/legacy_engine/config.py`,
  `src/legacy_engine/data/eras/certification-v1.json`, and
  `tests/analytics/eras/test_certification_source.py`.
- Tests added/removed: deterministic whole-event partition, atomicity, exhaustive/disjoint role
  coverage, empty-role digests, and closed-plan validation.
- Simplification: discovery now has one pure corpus composition path; the DB wrapper only projects,
  partitions, persists, and never exposes a full corpus to nomination.
- Discrepancies from design: the shipped profile is a candidate profile with checked-in control
  digest placeholder until Unit 3 supplies the control fixture; source reconstruction is exposed
  through the exact-id adapter and validates all manifest identity fields before returning the
  certification half.
- Adjacent issues parked: none.

## Verification evidence

- `.venv/bin/pytest -q tests/analytics/eras/test_discovery_run.py` — 3 passed.
- `.venv/bin/pytest -q tests/analytics/eras/test_certification_source.py` — passed.

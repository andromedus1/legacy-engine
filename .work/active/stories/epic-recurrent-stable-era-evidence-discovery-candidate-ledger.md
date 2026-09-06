---
id: epic-recurrent-stable-era-evidence-discovery-candidate-ledger
kind: story
stage: done
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-discovery
depends_on: [epic-recurrent-stable-era-evidence-discovery-segments-fingerprints]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Content-addressed recurrent discovery candidate ledger

## Brief

Implement Unit 3 from the parent feature: compose the cutoff adapter and pure discovery engine into
an immutable content-addressed run, persist the complete manifest/candidate/rejection evidence in
the derived DuckDB ledger, and expose exact-id reads as the only certification handoff.

## Implementation

See `epic-recurrent-stable-era-evidence-discovery` Unit 3 and its acceptance criteria.

Review weight remains `standard` at the parent feature boundary.

## Implementation notes

- Execution capability: delegated standard implementation owner; composition, content-addressed
  identity, immutable DuckDB persistence, and exact-id reads were implemented directly after the
  pure discovery checkpoint.
- Review weight: standard from the parent feature/project default; child checkpoints close directly.
- Files changed: `src/legacy_engine/analytics/eras/discovery_run.py`,
  `src/legacy_engine/analytics/eras/discovery_store.py`,
  `src/legacy_engine/analytics/eras/__init__.py`,
  `tests/analytics/eras/test_discovery_run.py`, plus cutoff/digest validation hardening in
  `src/legacy_engine/analytics/eras/discovery.py`.
- Tests added/removed: immutable retry/collision surface, exact-id round trip, multiple cutoffs,
  and explicit empty-fleet degradation.
- Simplification: one canonical JSON representation feeds both manifest/result hashes and the
  stored rows; no mutable latest-run convenience path was introduced.
- Discrepancies from design: source-level cutoff filtering now drops semantic boundaries effective
  after `as_of`, ensuring future configuration facts cannot perturb an earlier digest; this is a
  tightening of the stated cutoff contract, not a new evidence channel.
- Adjacent issues parked: none.

## Completion evidence

- Focused verification: `.venv/bin/pytest -q tests/analytics/eras/test_discovery*.py` — 11 passed;
  compileall passed for `src/legacy_engine/analytics/eras`.

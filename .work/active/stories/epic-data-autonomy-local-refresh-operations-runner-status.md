---
id: epic-data-autonomy-local-refresh-operations-runner-status
kind: story
stage: done
tags: [ingestion, infra]
parent: epic-data-autonomy-local-refresh-operations
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Durable scheduled-refresh runner and status

## Brief

Build the typed status repository and the exclusive scheduled runner around the existing composed
decision-data refresh. The runner must prevent overlapping mutations, preserve last-good ranking
attribution, and leave atomic canonical plus immutable per-attempt evidence for success, degradation,
failure, and overlap.

## Implementation

Implements Units 1 and 2 in the parent feature's `## Implementation Units`: typed status/health
models, atomic JSON persistence, `fcntl` locking, workflow-result mapping, artifact identity,
pending-action projection, and focused deterministic tests.

## Implementation notes

- Added constants-only operational paths plus a typed `legacy_engine.ops` package.
- Canonical and immutable attempt status use same-directory `fsync` + atomic replacement; readers
  distinguish healthy, degraded, failed, active, stale, missing, and invalid evidence.
- The scheduled runner owns a non-blocking kernel lock across the existing decision-refresh
  composition and terminal status publication. Overlap records evidence without touching canonical
  owner state, and retained last-good rankings are never attributed to failed attempts.
- Ranking identity is SHA-256-bound only after the composed workflow reports a successful ranking
  write. Era alarms remain explicit pending actions for the operator surface.

## Verification

- `.venv/bin/pytest -q tests/test_ops_status.py tests/test_scheduled_refresh.py tests/test_decision_refresh.py`
  — 24 passed.
- Ruff is not installed in the project virtual environment (`.venv/bin/ruff` absent); the repository
  pytest and later full-suite checks remain authoritative.

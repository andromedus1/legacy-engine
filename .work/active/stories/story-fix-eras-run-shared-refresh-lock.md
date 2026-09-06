---
id: story-fix-eras-run-shared-refresh-lock
kind: story
stage: done
tags: [bug, analytics, infra]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Make `eras run` honor the decision-refresh execution lock

## Symptom

A live `eras run` held the production DuckDB while `ops scheduler run-now` independently acquired
the decision-refresh file lock, then failed at DuckDB open. The database lock prevented corruption
but proved supported production mutation entrypoints did not share one authoritative lock.

## Root cause

`ops scheduled-refresh` derives its kernel lock from the resolved database and default ranking
artifact, while `eras run` opened and mutated the database directly without consulting that lock.
Read-only `eras list` and `eras explain` use the same connection helper but do not mutate state.

## Fix approach

Resolve `eras run`'s database and the production ranking artifact exactly as scheduled refresh does,
derive the same lock path, and hold `exclusive_file_lock` across connect, recompute, persistence, and
connection close. Convert contention into a clean Click error. Keep DuckDB's own lock as defense in
depth and leave read-only era commands unchanged.

## Regression test

`tests/test_cli_eras.py::TestErasRun::test_refuses_when_decision_refresh_owns_same_artifact_lock`
holds the hermetic scheduled-refresh lock and reproduces the bypass: before the fix, `eras run`
succeeds instead of refusing contention. Complementary coverage proves an executing `eras run`
blocks a second acquisition of that identity and read-only `eras list` does not acquire it.

## Implementation notes

Execution capability: direct focused repair. The bug is a single missing guard around an existing
mutation command and reuses the established lock API without a new coordination abstraction.

Changed `src/legacy_engine/cli.py` and `tests/test_cli_eras.py`; promoted and removed the originating
backlog record. `eras run` now resolves its database, derives the same database-plus-default-ranking
identity as the production decision refresh, and holds `exclusive_file_lock` through database open,
freshness projection, recompute/persistence, and close. `LockUnavailable` becomes a clean Click
error. DuckDB still supplies its independent process lock.

Regression-first evidence: before the fix, `eras run` exited 0 while the hermetic decision-refresh
lock was held. Afterward, scheduled-owner→eras contention rejects the run, and a fake recompute
proves eras-owner→scheduled acquisition also raises `LockUnavailable`. `eras list` remains unlocked.
Verification so far: `tests/test_cli_eras.py` is `20 passed`; the broader eras/scheduler/decision/ops
slice is `216 passed`; changed-test and existing lock-module Ruff is clean. No live database,
scheduler, status, ranking, or adjacent command was touched.

## Review (2026-08-12)

**Verdict**: Approve

**Blockers**: none

**Important**: none

**Nits**: none

**Rejected**: none

**Notes**: Bounded inline standalone-story review of commit `525222d`; no independent reviewer was
used. The resolved database path, `decks/best-deck-best-call-ranking.html`, and configured lock
directory exactly match the production default decision-refresh identity. Lock lifetime covers every
database mutation and close; it intentionally ends before human-readable output. Contention fails
before DuckDB open with a clean Click error, while DuckDB's own lock remains unchanged as defense in
depth. Bidirectional contention tests exercise the real kernel-backed lock, and `eras list` proves
read-only behavior remains unlocked. No public schema, scheduler lifecycle, status, ranking, or
other era command changed. Final verification: focused slice `216 passed`; full suite `3820 passed,
1 skipped`.

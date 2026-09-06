---
id: epic-data-autonomy-local-refresh-operations-review-safety
kind: story
stage: done
tags: [ingestion, infra, bug]
parent: epic-data-autonomy-local-refresh-operations
depends_on: [epic-data-autonomy-local-refresh-operations-launchd-controls]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close local refresh lifecycle safety gaps

## Brief

Resolve the standard-review blockers by giving every production mutation entrypoint one lock
identity derived from the protected database/ranking pair, refusing LaunchAgent bootout while that
lock is held, terminalizing SIGTERM best-effort, and restoring the previous agent across every
post-bootout failure. Keep all lifecycle tests hermetic; do not touch the live LaunchAgent.

## Acceptance criteria

- [x] Scheduled and manual refreshes targeting the same artifacts contend on the same lock even
      when status directories differ.
- [x] Install/reconfigure and uninstall refuse to boot out an active refresh.
- [x] SIGTERM writes failed canonical and attempt status before exiting when persistence remains
      available.
- [x] Any exception after a successful bootout restores the previous plist and reloads it when
      possible, with injected regression coverage.

## Implementation

- Added one artifact-derived lock identity shared by scheduled and manual refresh entrypoints;
  status-directory overrides no longer change concurrency protection.
- Made LaunchAgent install/reconfigure/uninstall acquire that lock, so an active refresh is never
  booted out. Added best-effort SIGTERM-to-terminal-status handling inside the lock-owning runner.
- Expanded reconfiguration rollback across candidate writes, log-directory preparation, bootstrap
  return failures, and raised process-adapter failures.
- Updated the operator runbook and architecture assertions. Regenerated the knowledge index with
  48 documents, 0 errors, and 11 pre-existing warnings. No live LaunchAgent was touched.

## Verification

- `PYTHONPATH=. .venv/bin/pytest -q tests/test_launchd.py tests/test_ops_cli.py tests/test_ops_status.py tests/test_scheduled_refresh.py tests/test_refresh_decision_script.py tests/test_decision_refresh.py tests/test_cli.py` — 134 passed.
- `.venv/bin/python -m compileall -q src/legacy_engine/ops src/legacy_engine/cli.py scripts/refresh_decision_data.py scripts/session_ops_status.py` — passed.
- `PYTHONPATH=. .venv/bin/pytest -q` — 3,769 passed, 1 skipped.
- `git diff --check` — passed.

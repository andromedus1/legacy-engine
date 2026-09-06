---
id: epic-data-autonomy-local-refresh-operations-launchd-controls
kind: story
stage: done
tags: [ingestion, infra]
parent: epic-data-autonomy-local-refresh-operations
depends_on: [epic-data-autonomy-local-refresh-operations-operator-cli]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Reversible local launchd controls

## Brief

Generate, install, inspect, trigger, and uninstall the maintainer's daily 07:30 user LaunchAgent
through typed, hermetically testable adapters. Preserve the previous configuration on failed reload,
keep live LaunchAgent paths out of tests, and document the complete operator lifecycle.

## Implementation

Implements Units 4 and 5 in the parent feature's `## Implementation Units`: validated plistlib
rendering, injected launchctl process boundary, idempotent/reversible controls, nested scheduler CLI,
current architecture/runbook updates, and knowledge-index regeneration after documentation changes.

## Implementation notes

- Added a `plistlib`-generated user LaunchAgent with absolute venv/repository/log paths, daily 07:30
  `StartCalendarInterval`, and no `RunAtLoad`, `KeepAlive`, or interval respawn behavior.
- Added an injected, no-shell `launchctl` boundary and reversible lifecycle controls. Identical
  installs no-op; changed installs boot out only the pinned agent; bootstrap failure restores and
  attempts to reload the previous plist; failed bootout preserves the installed file.
- Added nested scheduler CLI leaves plus operator-facing schedule/path/state audit lines. No command
  was invoked against the live LaunchAgent during implementation or verification.
- Updated README and architecture with install/inspect/run-now/status/log/uninstall behavior and
  explicit exclusions. Regenerated all three knowledge-index layers using the canonical plugin
  generator (48 indexed docs, 0 errors, 11 pre-existing warnings).
- Full-suite collection exposed pre-existing mixed import styles in the test tree; verification used
  the repository-root `PYTHONPATH` explicitly without changing unrelated ranking tests.

## Verification

- `.venv/bin/python -m compileall -q src/legacy_engine/ops src/legacy_engine/cli.py scripts/session_ops_status.py`
  — passed.
- `.venv/bin/pytest -q tests/test_launchd.py tests/test_ops_cli.py tests/test_ops_status.py tests/test_scheduled_refresh.py tests/test_decision_refresh.py tests/test_cli.py`
  — 125 passed.
- `PYTHONPATH=. .venv/bin/pytest -q` — 3,757 passed, 1 skipped.

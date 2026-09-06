---
id: epic-data-autonomy-local-refresh-operations-operator-cli
kind: story
stage: done
tags: [ingestion, infra]
parent: epic-data-autonomy-local-refresh-operations
depends_on: [epic-data-autonomy-local-refresh-operations-runner-status]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Operator CLI and session refresh status

## Brief

Expose the scheduled runner and typed health view through the established Click/audit-line surface,
and make the same concise local-only projection available at agent session start without duplicating
refresh or status semantics.

## Implementation

Implements Unit 3 in the parent feature's `## Implementation Units`: `ops scheduled-refresh`,
`ops status`, the portable session-status script/instruction, shared exit/audit projection, and
hermetic CLI coverage using explicit temporary paths.

## Implementation notes

- Added `legacy-engine ops scheduled-refresh` with explicit hermetic path overrides and stable exit
  semantics: success/degraded = 0, required failure = 1, overlap = 75.
- Added `legacy-engine ops status [--brief]` and a no-network `scripts/session_ops_status.py` that
  share the typed reader/formatter; missing and unhealthy status remain visible without breaking
  session startup.
- Added the empty `ops scheduler` group as the dependency-stable CLI seam for the next story.
- Updated project session orientation to surface local status without triggering refresh work.

## Verification

- `.venv/bin/pytest -q tests/test_ops_cli.py tests/test_ops_status.py tests/test_scheduled_refresh.py tests/test_decision_refresh.py tests/test_cli.py`
  — 111 passed.

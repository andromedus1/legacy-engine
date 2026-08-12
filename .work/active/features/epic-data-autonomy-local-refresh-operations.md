---
id: epic-data-autonomy-local-refresh-operations
kind: feature
stage: drafting
tags: [ingestion, infra]
parent: epic-data-autonomy
depends_on: [feature-decision-data-currency]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Local scheduled decision-data refresh and operator status

## Brief

Turn the existing composed decision-data refresh into a reliable local operation on the
maintainer's Mac. Use launchd at the already-decided daily 07:30 local schedule, with no
`RunAtLoad`, and execute against the repository's local data and DuckDB through absolute paths.

The feature must preserve the composed refresh's fail-closed/degraded contracts, prevent
overlapping runs, and atomically write a typed status record on both success and failure. Provide
repeatable install, inspect, run-now, and uninstall controls plus concise log and session/CLI
visibility. Do not add cloud state, a second database, or a second-format deployment.

## Acceptance boundary

- The scheduler invokes the existing production composition instead of duplicating refresh logic.
- Concurrent invocations cannot corrupt or race decision artifacts.
- Every attempted run leaves attributable timestamps, outcome, phase/reason, and artifact identity.
- Installation and removal are explicit and reversible; tests use hermetic temporary paths rather
  than touching the operator's live LaunchAgent.

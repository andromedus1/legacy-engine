---
id: epic-data-autonomy-local-refresh-operations-operator-cli
kind: story
stage: implementing
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

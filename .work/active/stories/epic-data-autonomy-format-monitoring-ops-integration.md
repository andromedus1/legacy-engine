---
id: epic-data-autonomy-format-monitoring-ops-integration
kind: story
stage: implementing
tags: [ingestion, infra]
parent: epic-data-autonomy-format-monitoring
depends_on: [epic-data-autonomy-format-monitoring-attribution-release]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Format-monitor operator integration

## Brief

Run monitoring under the existing scheduled-refresh lock, project its typed state into the shared
operator/session surface, add exact evidence acknowledgement, and document the human-confirmation
loop without adding a scheduler or automation authority.

## Implementation

Implements Unit 4 in the parent feature's `## Implementation Units`.

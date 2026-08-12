---
id: epic-data-autonomy-format-monitoring-ops-integration
kind: story
stage: done
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

Completed the format monitor inside the existing scheduled-refresh lock and reused its typed source
observation, release records, status writer, and pending-action projection. Monitor outages now
degrade an otherwise successful job without discarding the newly written ranking. Added the
`ops monitor acknowledge` exact-candidate command; acknowledgement records the current evidence hash
and never mutates the curated B&R ledger. Production adapters remain injectable, tests do not call
providers or launchd, and no second daemon or live LaunchAgent was installed.

Documented the detection-only operator loop and architecture boundaries. Focused integration
verification: `59 passed` across monitor, scheduler, status, CLI, and decision-refresh tests.

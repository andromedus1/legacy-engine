---
id: epic-data-autonomy-local-refresh-operations-runner-status
kind: story
stage: implementing
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

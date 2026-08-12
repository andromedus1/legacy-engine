---
id: epic-data-autonomy-local-refresh-operations-launchd-controls
kind: story
stage: implementing
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

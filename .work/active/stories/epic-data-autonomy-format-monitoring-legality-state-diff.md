---
id: epic-data-autonomy-format-monitoring-legality-state-diff
kind: story
stage: implementing
tags: [ingestion, infra]
parent: epic-data-autonomy-format-monitoring
depends_on: [epic-data-autonomy-format-monitoring-scryfall-jsonl-contract]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Durable legality observation and candidate state

## Brief

Build the typed, atomically persisted last-good legality baseline and pure candidate transition
logic, including stable identities, evidence-hash acknowledgement, confirmed retirement, and loud
unsupported reversal handling.

## Implementation

Implements Unit 2 in the parent feature's `## Implementation Units`.

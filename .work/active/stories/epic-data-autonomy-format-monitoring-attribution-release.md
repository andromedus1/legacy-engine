---
id: epic-data-autonomy-format-monitoring-attribution-release
kind: story
stage: implementing
tags: [ingestion, infra]
parent: epic-data-autonomy-format-monitoring
depends_on: [epic-data-autonomy-format-monitoring-legality-state-diff]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Attributable B&R and release monitoring composition

## Brief

Add strict hermetic WotC Legacy-announcement parsing and merge it with Scryfall detection plus the
existing release/card-diff signals. Preserve per-signal clear, pending, not-due, and unavailable
states without writing accepted format truth.

## Implementation

Implements Unit 3 in the parent feature's `## Implementation Units`.

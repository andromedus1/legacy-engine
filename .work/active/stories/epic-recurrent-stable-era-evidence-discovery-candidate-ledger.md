---
id: epic-recurrent-stable-era-evidence-discovery-candidate-ledger
kind: story
stage: implementing
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-discovery
depends_on: [epic-recurrent-stable-era-evidence-discovery-segments-fingerprints]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Content-addressed recurrent discovery candidate ledger

## Brief

Implement Unit 3 from the parent feature: compose the cutoff adapter and pure discovery engine into
an immutable content-addressed run, persist the complete manifest/candidate/rejection evidence in
the derived DuckDB ledger, and expose exact-id reads as the only certification handoff.

## Implementation

See `epic-recurrent-stable-era-evidence-discovery` Unit 3 and its acceptance criteria.

Review weight remains `standard` at the parent feature boundary.

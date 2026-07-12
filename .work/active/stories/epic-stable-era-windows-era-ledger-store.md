---
id: epic-stable-era-windows-era-ledger-store
kind: story
stage: implementing
tags: [analytics, ingestion]
parent: epic-stable-era-windows-era-ledger
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# BAN_EVENTS curated-JSON migration + entity_eras store

## Brief
Units A+B of the parent feature: banlist events JSON loader (module API unchanged, append path for the confirm loop) and the rebuildable entity_eras DuckDB store with stable_since_map() as the consumption entry point.

## Implementation
Parent feature `epic-stable-era-windows-era-ledger` — exact contracts + acceptance criteria there.

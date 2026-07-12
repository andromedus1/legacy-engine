---
id: epic-stable-era-windows-detection-series
kind: story
stage: implementing
tags: [analytics]
parent: epic-stable-era-windows-detection
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Entity series builder (analytics/eras/series.py)

## Brief
One batched DuckDB scan → per-entity density-adaptive bucketed series (share, W/L, flex-band
inclusion), plain frozen dataclasses, partial-trailing-bucket flag, camp entities from
decks.variant. Objective-search-split: everything downstream is pure.

## Implementation
Parent feature `epic-stable-era-windows-detection` — Unit 1 (exact signatures + acceptance
criteria there).

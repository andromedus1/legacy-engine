---
id: feature-empirical-sideboard-swings
kind: feature
stage: drafting
tags: [advisory]
parent: epic-bigmana-coverage-sideboard-fidelity
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Empirical sideboard swing magnitudes where data supports

## Brief
The recommender's per-tag swing magnitudes (`_SWING_DEDICATED=0.20`, `_SWING_SOFT=0.10`) are curated
heuristic constants, not derived from before/after-sideboard win-rate data — they drive solver ordering.
Where the data supports it (sufficient n on the relevant matchup/tag), derive empirical swings from
actual sideboarded-game win-rate deltas; keep the curated constant + its honest caveat where the data is
thin. Must stay honest (confidence-tier the empirical swings; never present a thin-data swing as
established). Gated-additive: thin tags keep the curated constant + caveat.

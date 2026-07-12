---
id: epic-stable-era-windows-detection-ensemble
kind: story
stage: implementing
tags: [analytics, methodology]
parent: epic-stable-era-windows-detection
depends_on: [epic-stable-era-windows-detection-detectors, epic-stable-era-windows-detection-bocpd]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Ensemble + FDR + floors + stable_since, ruptures dep, calibration fixtures (analytics/eras/ensemble.py)

## Brief
Merge candidates across signals (±2-bucket tolerance), fleet-wide Benjamini–Hochberg FDR at
α=0.05, ≥30-decks-in-new-era floor, camp parent-inheritance, per-entity stable_since derivation.
Adds ruptures to core deps; freezes the ledger calibration fixtures (Tron cliff, Flow State ×3,
stable non-event, seeded null fleet) that pin the operating point.

## Implementation
Parent feature `epic-stable-era-windows-detection` — Units 4+5 (exact signatures + acceptance
criteria there).

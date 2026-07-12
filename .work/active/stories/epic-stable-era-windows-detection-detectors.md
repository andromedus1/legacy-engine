---
id: epic-stable-era-windows-detection-detectors
kind: story
stage: implementing
tags: [analytics, methodology]
parent: epic-stable-era-windows-detection
depends_on: [epic-stable-era-windows-detection-series]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Signal detectors S1-S4 (analytics/eras/detect.py)

## Brief
Presence cliff/ramp rules (exact two-proportion tests, trigger card named), composition CPD
(ruptures PELT/KernelCPD cosine + segment-permutation p-values), share-shift detection, win-rate
corroboration. Closed-vocabulary signal enum, deterministic given seed. Trickiest unit — the S2
permutation significance scheme; build it first against the frozen ground-truth fixtures.

## Implementation
Parent feature `epic-stable-era-windows-detection` — Unit 3 (exact signatures + acceptance
criteria there).

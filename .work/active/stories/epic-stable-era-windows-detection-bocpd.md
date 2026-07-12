---
id: epic-stable-era-windows-detection-bocpd
kind: story
stage: implementing
tags: [analytics, methodology]
parent: epic-stable-era-windows-detection
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Beta-Binomial BOCPD recursion (analytics/eras/bocpd.py)

## Brief
In-project Adams–MacKay Bayesian online change-point recursion with a Beta–Binomial predictive
(no Python package covers count/proportion likelihoods — verified in the brief). Pure
numpy/scipy, deterministic, zero-trial-safe. Consumed later by the era-ledger drift alarm.

## Implementation
Parent feature `epic-stable-era-windows-detection` — Unit 2 (exact signatures + acceptance
criteria there).

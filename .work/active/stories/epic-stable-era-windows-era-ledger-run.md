---
id: epic-stable-era-windows-era-ledger-run
kind: story
stage: implementing
tags: [analytics, methodology]
parent: epic-stable-era-windows-era-ledger
depends_on: [epic-stable-era-windows-era-ledger-store]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Attribution + eras run pass + drift alarm

## Brief
Units C+D: boundary attribution (ban/release/unattributed, ±14d tolerance, affectedness-threshold check), the run_eras offline pass wiring series→detectors→ensemble→attribution→store, and the BOCPD tail drift alarm for high-share entities.

## Implementation
Parent feature `epic-stable-era-windows-era-ledger` — exact contracts + acceptance criteria there.

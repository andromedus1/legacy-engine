---
id: feature-ranking-measurement-integrity-ranking-ledger
kind: story
stage: implementing
tags: [analytics, advisory, honesty]
parent: feature-ranking-measurement-integrity
depends_on: [feature-ranking-measurement-integrity-evidence-contracts]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Shared selected-cell ledger and row reconciliation

## Brief

Replace page-local source selection and row formulas with a typed package contract that proves
serialized parity, exposes a strict-common-era diagnostic, and quantifies observable matchup floor.

## Implementation

Implements Unit 2 of the parent feature's `## Implementation Units`: selected-cell truth table,
row measurement, Cradle-shaped reconciliation, and floor-observability contracts.

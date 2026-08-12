---
id: feature-ranking-benchmark-residual-quarantine-corpus-boundaries
kind: story
stage: implementing
tags: [analytics, advisory, testing, data-quality]
parent: feature-ranking-benchmark-residual-quarantine
depends_on: [feature-ranking-benchmark-residual-quarantine-policy-ledger]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Symmetric snapshot and held-out quarantine boundaries

## Brief

Implement Unit 2 from the parent feature: consume the same pre-outcome ledger in training snapshots
and held-out classification/scoring, with separate raw/retained hashes and denominators.

## Implementation

See `feature-ranking-benchmark-residual-quarantine` Unit 2 and its acceptance criteria.

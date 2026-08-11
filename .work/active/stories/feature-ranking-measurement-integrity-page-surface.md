---
id: feature-ranking-measurement-integrity-page-surface
kind: story
stage: implementing
tags: [analytics, advisory, honesty]
parent: feature-ranking-measurement-integrity
depends_on: [feature-ranking-measurement-integrity-ranking-ledger]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Ranking-page honesty surface and rolling documentation

## Brief

Migrate the Best Call generator and template to the shared measurement ledger and render estimator
divergence, concentration, and camp floor observability without changing the page's current gate.

## Implementation

Implements Unit 3 of the parent feature's `## Implementation Units`: typed payload integration,
honest-null rendering, deterministic page tests, and the updated refresh runbook.

---
id: feature-ranking-measurement-integrity
kind: feature
stage: drafting
tags: [analytics, advisory, honesty]
parent: epic-best-deck-decision-trust
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Ranking measurement integrity — reconcile windows, rates, and observable floors

## Brief

Resolve the measurement disagreements that can reverse a best-deck conclusion before adding new
ranking views. Reproduce and explain the independent adjusted-field-WR divergence, clamp
build/camp comparisons to both the subject and opponent stable eras, surface event/month
concentration when one cluster dominates a cell, and state how much of every camp's matchup floor
is actually observable.

This feature absorbs the actionable scope of backlog items
`idea-adj-field-wr-recompute-divergence`, `idea-clamp-split-comparisons-to-opponent-era`, and
`feature-camp-floor-observability-banner`. Their original backlog files remain as evidence until
feature design maps each finding to an implementation checkpoint.

## Strategic decisions

- The page-used adaptive measure remains the headline only if the recomputation proves its window
  selection is unbiased and reproducible; divergence is surfaced, not averaged away.
- A comparison may narrow for either entity's era but may never widen past an opponent disturbance
  merely to buy sample size.
- Missing bad matchups are missing evidence, never a high floor.

## Simplification opportunity

Extract or reuse one typed row/cell measurement primitive across refresh, display, and benchmark
code. Delete hand-rolled duplicate formulas once parity is proven.

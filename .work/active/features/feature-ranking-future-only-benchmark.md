---
id: feature-ranking-future-only-benchmark
kind: feature
stage: drafting
tags: [analytics, advisory, testing]
parent: epic-best-deck-decision-trust
depends_on: [feature-ranking-measurement-integrity, feature-ranking-honesty-guards, feature-agency-page-methodology]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Future-only ranking benchmark — test whether today's call predicts tomorrow

## Brief

Build a chronological walk-forward harness that freezes every ranking input at cutoff T, evaluates
against events after T, and compares legacy-engine with deliberately simple baselines. Report
match-probability calibration and loss, ranking quality, top-k usefulness, and decision regret
across multiple cutoffs and ban regimes. Prevent leakage from future era boundaries, taxonomy
promotions, player ratings, field composition, or card availability.

Support operator-supplied dated external ranking/matchup snapshots as an independent comparison
surface. External data is labeled by source and date and is not required for the core benchmark;
the feature must not depend on an unapproved scraper or silently treat external consensus as truth.

## Strategic decisions

- Primary evidence is match-level Brier/log loss and calibration; rank correlation and regret are
  decision-facing secondary metrics.
- Every derived feature is computed strictly from information available before the evaluated
  match/event.
- The benchmark compares against recent raw WR, field share, top-finish/conversion, and simple
  shrinkage baselines.
- A future “best deck” headline may claim predictive validation only after repeated windows beat
  the simple baselines; otherwise results remain descriptive positioning estimates.

## Simplification opportunity

Persist a small typed frozen-prediction artifact and reuse production ranking code. Do not create a
parallel benchmark-only ranking engine.

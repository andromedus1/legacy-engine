---
id: feature-player-effect-diagnostic-future-evaluation
kind: story
stage: implementing
tags: [analytics, players, experimental]
parent: feature-player-effect-diagnostic
depends_on: [feature-player-effect-diagnostic-frozen-model]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Future-only player-effect evaluation and stop/go report

## Brief

Score the frozen experimental forecasts on the benchmark's identical future cases, expose
event-heldout, cold-start/player-support, and venue diagnostics, apply the preregistered
proper-score/calibration/regret stop-go conjunction, and add the hermetic CLI and aggregate-only
runbook surface without changing production ranking.

## Implementation

Implement Unit 3 in the parent feature's `## Implementation Units` after frozen player predictions
exist. The strongest successful output is a candidate for a separate promotion study, never an
automatic estimator or Best Call change.

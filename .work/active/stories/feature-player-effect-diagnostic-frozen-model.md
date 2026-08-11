---
id: feature-player-effect-diagnostic-frozen-model
kind: story
stage: implementing
tags: [analytics, players, experimental]
parent: feature-player-effect-diagnostic
depends_on: [feature-player-effect-diagnostic-coverage-stickiness]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Partially pooled player model and frozen forecasts

## Brief

Fit the preregistered deck-residual control and cross-classified player/familiarity sensitivities
strictly from each origin prefix, then freeze neutral deck and outcome-blind participant forecasts
without persisting player identities or individual coefficient tables.

## Implementation

Implement Unit 2 in the parent feature's `## Implementation Units` after the accessibility ledger is
complete. Preserve the production estimator registry and fail closed on temporal selection, fit,
identity, schedule, or hash defects.

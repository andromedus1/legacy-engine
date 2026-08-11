---
id: feature-player-effect-diagnostic-frozen-model
kind: story
stage: done
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

## Implementation notes

- Execution capability: inherited frontier worker at high effort because temporal selection,
  cross-classified terms, and privacy-safe serialization are statistically consequential.
- Review weight: standard (autopilot/default feature review).
- Files changed: new `analytics/players/effect.py`, the player-effect workflow adapter, and focused
  effect/workflow regressions.
- Tests added: crossed repeat-player signal, reciprocal probabilities, deterministic repeated fits,
  shrinkage for deck/player/familiarity terms, cold-start versus below-floor support, three-origin
  selection gate, frozen artifact privacy/registry isolation, and result-only schedule invariance.
- Simplification: one compact deterministic coefficient layout serves all three preregistered
  experimental estimators; neutral forecasts reuse the same fit with participant terms set to zero.
- Discrepancies from design: `freeze_player_effect_predictions` accepts the already-built inner
  folds as an explicit keyword so the filesystem adapter remains outside the pure analytics core.
  Contemporaneous scheduled taxonomy replay remains fail-closed until the caller supplies a fully
  frozen classification adapter in the evaluation story.
- Verification: 10 focused player tests passed; focused Ruff and diff checks passed.
- Adjacent issues parked: none.

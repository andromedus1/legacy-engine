---
id: feature-player-effect-diagnostic-future-evaluation
kind: story
stage: done
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

## Implementation notes

- Execution capability: inherited frontier worker at high effort because future-only evaluation,
  privacy boundaries, and candidate gating are statistically consequential.
- Review weight: standard (autopilot/default feature review).
- Files changed: player-effect analytics/workflow adapters, the nested advisory CLI, focused
  analytics/CLI regressions, and the current methodology/runbook/foundation descriptions.
- Tests added: immutable outcome-open separation, exact benchmark/fold/protocol hash checks,
  event-heldout player-aware/masked/neutral estimands, known/cold and online/paper strata,
  conservative proper-score/calibration/regret gates, aggregate-only reporting, explicit database
  requirements, and `evaluate`/`run` parity.
- Simplification: evaluation reuses the benchmark calibration, regret, and content-hash contracts;
  the CLI composes the same plan/freeze/evaluate functions instead of maintaining a second path.
- Discrepancies from design: `PlayerEffectOutcome` includes a stable `match_id` because the shared
  benchmark heldout row intentionally omits source match identity. Scheduled replay also records
  subject orientation explicitly, so outcome joins never infer sides from player identity. The
  final workflow accepts a frozen taxonomy snapshot and classifies schedules at their benchmark
  origin, superseding the prior checkpoint's temporary fail-closed limitation.
- Verification: 13 focused player tests and 102 affected player/benchmark tests passed; owned Ruff,
  compile, diff, and knowledge-index lint checks passed with zero index errors.
- Adjacent issues parked: none.

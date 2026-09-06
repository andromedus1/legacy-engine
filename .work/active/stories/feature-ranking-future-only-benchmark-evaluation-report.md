---
id: feature-ranking-future-only-benchmark-evaluation-report
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: feature-ranking-future-only-benchmark
depends_on: [feature-ranking-future-only-benchmark-prediction-freeze]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Future-only evaluation, external comparators, and operator report

## Brief

Score immutable forecasts against later event-grouped outcomes, report proper/calibration/rank/regret
evidence and all support/censoring states, accept optional dated external snapshots, and expose the
two-phase benchmark through a hermetic CLI and generated report.

## Implementation

Implement Unit 3 in the parent feature's `## Implementation Units` section after prediction freeze
is complete. Evaluation must remain read-only with respect to estimator choice and production state.

## Implementation notes

- Execution capability: inherited frontier model at high effort because this checkpoint owns proper
  scoring, dependence-aware uncertainty, claim gating, external evidence, CLI orchestration, and
  rolling foundation truth.
- Review weight: standard from the active autopilot run; the feature advances to independent review
  only after integrated/full verification.
- Files changed: benchmark domain/workflow modules, nested CLI, benchmark tests, the Best Call
  runbook, SPEC, ARCHITECTURE, and generated knowledge indexes.
- Tests added: future-outcome reversal without prediction mutation; identical common-case scoring
  with typed exclusions; deterministic event-block and player-component sensitivity; honest thin
  support; dated partial external snapshots; contemporaneous same-rules training/holdout labeling;
  frozen/evaluation taxonomy-identity mismatch rejection; both-coefficient calibration gating;
  explicit-DB CLI plan/freeze/evaluate/run parity; and checksum tamper rejection.
- Simplification: evaluation consumes only the immutable prediction model plus typed held-out rows;
  the historical `run` command composes the same freeze and evaluate functions, and Markdown is a
  view over the canonical JSON summary rather than another result store.
- Discrepancies from design: `freeze_origin_predictions` and held-out DB extraction remain workflow
  adapters rather than advisory-domain functions. Event-level paired intervals are retained on each
  fold and aggregated across folds; the aggregate interval therefore respects both event blocks and
  the preregistered non-overlapping fold boundary. The optional player sensitivity reports a
  connected-player-component bootstrap only when normalized identity coverage reaches 80%.
- Adjacent issues parked: none.
- Documentation review: the first fresh audit exposed missing frozen/evaluation taxonomy-identity
  binding and incomplete aggregate calibration gating. Both received behavioral regressions and
  fixes; the required post-fix full re-audit reported 0 Critical/High/Medium/Low findings and
  independently reran the 18 benchmark tests green.
- Verification: focused benchmark/ranking/era/CLI suite — 232 passed in 16.53s; focused Ruff and
  compilation checks passed. Knowledge-index regeneration reported 0 errors and 11 existing
  warnings. Full repository verification is recorded on the parent feature.

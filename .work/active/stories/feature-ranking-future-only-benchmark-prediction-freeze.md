---
id: feature-ranking-future-only-benchmark-prediction-freeze
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: feature-ranking-future-only-benchmark
depends_on: [feature-ranking-future-only-benchmark-protocol-snapshot]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Shared ranking handoff and immutable prediction freeze

## Brief

Extract the archetype ranking handoff shared by the production page and benchmark, issue every
preregistered production/baseline forecast from the frozen origin, and persist deterministic
prediction artifacts containing no future evidence.

## Implementation

Implement Unit 2 in the parent feature's `## Implementation Units` section. Preserve the current
Best Call gated/P(best) authority and exact refresh-page behavior.

## Implementation notes

- Execution capability: inherited frontier model at high effort because immutable prediction bytes
  combine production ranking semantics, five baselines, and an audit hash boundary.
- Review weight: standard from the active autopilot run; this child checkpoint closes directly on
  green verification.
- Files changed: benchmark domain/workflow modules and benchmark unit/snapshot tests. The production
  page generator was intentionally left byte-for-byte unchanged.
- Tests added: explicit `0.5 + imputed + unserved` unresolved production projection; deterministic
  all-estimator freeze and canonical artifact hash; post-cutoff label exclusion; and direct parity
  between frozen CI-gated probability and the shared typed selected-cell ledger.
- Simplification: production variants reuse `RankingCellMeasurement`, the four fixed methodology
  specs, `measure_variant_row`, `measure_lean_agency`, and `measure_ranking_row`; baseline-only
  calculations stay in the benchmark adapter and do not create another production ranking engine.
- Discrepancies from design: no page assembly extraction was necessary. The shipped page already
  serializes the package-owned typed ledger and methodology contracts; the benchmark assembles that
  same contract from its frozen DB while the unchanged page parity suite guards its authority.
  `freeze_origin_predictions` lives in the workflow adapter because opening DuckDB is
  infrastructure; immutable models/projection/writer remain in the advisory domain module.
- Adjacent issues parked: none.
- Verification: focused benchmark/ranking/page suite — 75 passed in 5.43s; Ruff and compilation
  passed.

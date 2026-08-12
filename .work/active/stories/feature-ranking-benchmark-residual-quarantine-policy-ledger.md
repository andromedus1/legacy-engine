---
id: feature-ranking-benchmark-residual-quarantine-policy-ledger
kind: story
stage: done
tags: [analytics, advisory, testing, data-quality]
parent: feature-ranking-benchmark-residual-quarantine
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Protocol-bound quarantine policy and evidence ledger

## Brief

Implement Unit 1 from the parent feature: additive protocol fields, validated support ceilings, and
the deterministic outcome-blind card-metadata quarantine planner with complete evidence.

## Implementation

See `feature-ranking-benchmark-residual-quarantine` Unit 1 and its acceptance criteria.

## Implementation notes
- Execution capability: inline standard implementation; the policy and planner are a cohesive pure-contract unit.
- Review weight: standard (orchestrator default).
- Files changed: `src/legacy_engine/advisory/ranking_benchmark.py`, `src/legacy_engine/workflows/ranking_benchmark.py`, `tests/test_ranking_benchmark.py`.
- Tests added/removed: policy validation, posthoc descriptive ceiling, whole-deck ledger planning, and result-blind digest invariance.
- Simplification: one typed planner now owns unresolved-card evidence and support-ceiling calculations.
- Discrepancies from design: planner returns a ledger with `within_ceiling=false`; snapshot builders reject it before writing, preserving a complete audit record.
- Adjacent issues parked: none.
- Verification: 26 focused benchmark/snapshot/CLI tests passed; compileall passed.

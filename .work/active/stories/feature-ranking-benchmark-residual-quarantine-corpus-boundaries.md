---
id: feature-ranking-benchmark-residual-quarantine-corpus-boundaries
kind: story
stage: done
tags: [analytics, advisory, testing, data-quality]
parent: feature-ranking-benchmark-residual-quarantine
depends_on: [feature-ranking-benchmark-residual-quarantine-policy-ledger]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Symmetric snapshot and held-out quarantine boundaries

## Brief

Implement Unit 2 from the parent feature: consume the same pre-outcome ledger in training snapshots
and held-out classification/scoring, with separate raw/retained hashes and denominators.

## Implementation

See `feature-ranking-benchmark-residual-quarantine` Unit 2 and its acceptance criteria.

## Implementation notes
- Execution capability: inline standard implementation; snapshot and held-out adapters share the same planner.
- Review weight: standard (orchestrator default).
- Files changed: `src/legacy_engine/advisory/ranking_benchmark.py`, `src/legacy_engine/workflows/ranking_benchmark.py`, `tests/test_ranking_benchmark_snapshot.py`.
- Tests added/removed: file-backed quarantine snapshot proves whole-deck removal before taxonomy and retained closure.
- Simplification: one ledger is carried on both `SnapshotManifest` and `HeldoutOutcomes`; no second exclusion engine was introduced.
- Discrepancies from design: retained-facts hashes are populated after adapter filtering and ledger digests remain derived from canonical typed evidence.
- Adjacent issues parked: none.
- Verification: 27 focused benchmark/snapshot/CLI tests passed.

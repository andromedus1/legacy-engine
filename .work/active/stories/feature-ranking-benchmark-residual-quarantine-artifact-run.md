---
id: feature-ranking-benchmark-residual-quarantine-artifact-run
kind: story
stage: done
tags: [analytics, advisory, testing, data-quality]
parent: feature-ranking-benchmark-residual-quarantine
depends_on: [feature-ranking-benchmark-residual-quarantine-corpus-boundaries]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Operator controls and historical sensitivity artifact

## Brief

Implement Unit 3 from the parent feature: strict-default CLI controls, descriptive claim ceiling,
complete report evidence, documentation, and an immutable historical sensitivity replay distinct
from v1. Refresh the Best Call page only with the exact resulting benchmark status and identity.

## Implementation

See `feature-ranking-benchmark-residual-quarantine` Unit 3 and its acceptance criteria.

## Implementation notes
- Execution capability: inline standard implementation; operator controls, claim cap, report evidence, and docs share one protocol surface.
- Review weight: standard (orchestrator default).
- Files changed: `src/legacy_engine/cli.py`, `src/legacy_engine/advisory/ranking_benchmark.py`, benchmark tests, `docs/analysis/best-call-ranking.md`, `docs/ARCHITECTURE.md`.
- Tests added/removed: CLI option serialization and descriptive claim-ceiling/report assertions; no tests removed.
- Simplification: report and audit output read the typed ledger directly rather than reconstructing exclusion counts.
- Discrepancies from design: the empirical historical replay is executed after this controls commit and recorded below; page refresh remains gated on an exact resulting summary identity.
- Adjacent issues parked: none.
- Verification: focused benchmark/snapshot/CLI tests and Ruff checks passed.

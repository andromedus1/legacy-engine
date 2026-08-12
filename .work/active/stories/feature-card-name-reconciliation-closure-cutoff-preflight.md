---
id: feature-card-name-reconciliation-closure-cutoff-preflight
kind: story
stage: done
tags: [ingestion, data-quality, benchmark]
parent: feature-card-name-reconciliation-closure
depends_on: [feature-card-name-reconciliation-closure-provider-serialization]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Report all benchmark-relevant card metadata gaps

## Brief

Implement Unit 2 from the parent design: a typed cutoff-aware residual ledger and explicit-DB CLI
preflight that prints every cohort and fails only for gaps entering a planned training cutoff.

## Acceptance criteria

- The parent Unit 2 acceptance criteria are green.
- Protocol parsing and date-boundary behavior have hermetic regressions.
- Output is complete, machine-scannable, and retains fail-closed gap names.

## Implementation notes

- Execution capability: direct cohesive implementation; the typed ledger, schedule parser, and CLI
  adapter share one small ingestion boundary.
- Review weight: standard, inherited from the parent feature/default project policy.
- Files changed: `src/legacy_engine/models/card.py`,
  `src/legacy_engine/ingestion/card_coverage.py`, `src/legacy_engine/cli.py`, and
  `tests/test_card_coverage_cli.py`.
- Tests added: strict cutoff-boundary grouping, complete multi-cohort output, blocking exit,
  nonblocking post-last-cutoff disclosure, zero-gap success, and invalid ordered-schedule rejection.
- Simplification: one complete preflight replaces serial one-name benchmark discoveries without
  importing benchmark estimators into ingestion.
- Discrepancies from design: none.
- Protocol boundary: parsing consumes only non-empty ordered unique `planned_folds[*].cutoff` and a
  later `final_evaluation_until`; it never derives mutable dates from the corpus.
- Verification: card coverage plus reconciliation suites pass (`28 passed`).
- Adjacent issues parked: none.

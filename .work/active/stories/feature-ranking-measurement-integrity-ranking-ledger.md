---
id: feature-ranking-measurement-integrity-ranking-ledger
kind: story
stage: done
tags: [analytics, advisory, honesty]
parent: feature-ranking-measurement-integrity
depends_on: [feature-ranking-measurement-integrity-evidence-contracts]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Shared selected-cell ledger and row reconciliation

## Brief

Replace page-local source selection and row formulas with a typed package contract that proves
serialized parity, exposes a strict-common-era diagnostic, and quantifies observable matchup floor.

## Implementation

Implements Unit 2 of the parent feature's `## Implementation Units`: selected-cell truth table,
row measurement, Cradle-shaped reconciliation, and floor-observability contracts.

## Implementation notes

- Execution capability: inherited frontier model at high effort; source-selection and estimator
  reconciliation are statistically consequential shared contracts.
- Review weight: standard (caller).
- Files changed: added `advisory/ranking_measurement.py` and its focused tests; migrated the refresh
  generator's source selection and row formulas to the typed ledger.
- Tests added/removed: added truth-table, missing-source, invalid-gate, weighting, strict-common
  divergence, serialized parity, grounding, and floor-observability regressions; no tests removed.
- Simplification: `make_cells` now delegates source choice and `row_stats` delegates every metric to
  the package-owned ledger; the duplicated script formulas were removed.
- Discrepancies from design: the serialized parity check re-validates a full JSON-mode projection of
  each typed cell rather than a second hand-built report dict, which is both stricter and smaller.
- Adjacent issues parked: none.
- Verification: the designed measurement/refresh tests plus the broad matchup contract tests — 224
  passed.

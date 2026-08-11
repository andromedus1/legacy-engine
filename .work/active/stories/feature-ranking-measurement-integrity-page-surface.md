---
id: feature-ranking-measurement-integrity-page-surface
kind: story
stage: done
tags: [analytics, advisory, honesty]
parent: feature-ranking-measurement-integrity
depends_on: [feature-ranking-measurement-integrity-ranking-ledger]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Ranking-page honesty surface and rolling documentation

## Brief

Migrate the Best Call generator and template to the shared measurement ledger and render estimator
divergence, concentration, and camp floor observability without changing the page's current gate.

## Implementation

Implements Unit 3 of the parent feature's `## Implementation Units`: typed payload integration,
honest-null rendering, deterministic page tests, and the updated refresh runbook.

## Implementation notes

- Execution capability: inherited frontier model at high effort; this is the user-facing honesty
  boundary for statistically consequential ranking evidence.
- Review weight: standard (caller).
- Files changed: refresh generator, tracked HTML template, refresh integration tests, and the Best
  Call runbook.
- Tests added/removed: added typed payload, serialized parity, honest unobserved-floor, and template
  surface regressions; no tests removed.
- Simplification: report projection now has one `ranking_row_payload` adapter over the package model;
  the template renders typed reconciliation/observability fields directly.
- Discrepancies from design: concentration evidence renders inline in each affected exact-cell row
  rather than a separate warning panel, retaining the selected window next to the warning.
- Adjacent issues parked: none.
- Verification: `tests/test_ranking_measurement.py tests/test_refresh_best_call_ranking.py` — 29
  passed, including deterministic file-backed whole-page generation.

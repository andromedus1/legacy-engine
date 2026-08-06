---
id: feature-strategic-plan-best-call-viz-data-contract
kind: story
stage: done
tags: [analytics, viz, ui]
parent: feature-strategic-plan-best-call-viz
depends_on: []
release_binding: v0.4.0
gate_origin: null
created: 2026-08-02
updated: 2026-08-02
---

# Strategic-plan registry, aggregation, and payload contract

## Brief

Create the validated five-plan curated registry, recompute plan-versus-plan results from underlying
decisive matches, and expose the reusable typed result plus report payload with structural same-plan
semantics and external-only floor coverage.

## Implementation

Implement Units 1–3 from the parent feature's `## Implementation Units` section.

## Implementation notes

- Execution capability: high; taxonomy validation, match-level accounting, and generated payload semantics carry cross-layer contract risk.
- Review weight: standard (caller/default).
- Files changed: `src/legacy_engine/analytics/strategy_plan.py`, `src/legacy_engine/data/strategy_plans/legacy.json`, `scripts/refresh_best_call_ranking.py`, `tests/test_strategy_plan.py`.
- Tests added/removed: added deterministic registry-validation and aggregation tests covering complementarity, same-plan accounting, omitted matches, null cells, gate boundaries, and provenance; none removed.
- Simplification: primary-plan aggregation is isolated from composition-family pooling and rendered percentages; no generic taxonomy framework was introduced.
- Discrepancies from design: package registry includes stable synthetic fixture labels used by the report's file-backed contract tests in addition to production labels; no behavioral discrepancy.
- Adjacent issues parked: none.
- Verification: `pytest tests/test_strategy_plan.py -q` — 12 passed. Ruff is not installed in the project virtualenv, so lint was deferred to the repository's available checks.

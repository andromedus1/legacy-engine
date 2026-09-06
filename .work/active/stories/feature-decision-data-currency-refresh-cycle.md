---
id: feature-decision-data-currency-refresh-cycle
kind: story
stage: done
tags: [ingestion, infra, analytics]
parent: feature-decision-data-currency
depends_on:
  - feature-decision-data-currency-runtime-alignment
  - feature-decision-data-currency-card-coverage
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Compose the decision-data refresh cycle

## Brief

Provide one typed, repository-local refresh composition for tournament/rules/cards refresh, card
coverage reconciliation, labeling, all staged camp applications, era detection, and final ranking
generation. Surface release scans, the registered B&R ledger, era alarms, step failures, and the
ranking output without shell orchestration, cloud state, commits, or pushes.

## Implementation

Implement Unit 4 in the parent feature's `## Implementation Units` section after both dependency
stories complete. Preserve the existing individual CLI/script surfaces and make the tracked ranking
writer the final step only.

## Implementation notes

- Execution capability: frontier/high; this composition mutates several rebuildable caches and must
  preserve last-good ranking output across external and analytical failures.
- Review weight: standard (caller).
- Files changed: `src/legacy_engine/workflows/__init__.py`,
  `src/legacy_engine/workflows/decision_refresh.py`, `scripts/refresh_decision_data.py`,
  `scripts/refresh_best_call_ranking.py`, `tests/test_decision_refresh.py`,
  `tests/test_refresh_best_call_ranking.py`, and `docs/analysis/best-call-ranking.md`.
- Tests added: injected-port order/failure/degrade coverage plus a file-backed byte-parity regression
  between `generate_ranking` and the existing CLI adapter, plus a transport-gzip regression that
  proves the all-cards mirror remains parseable after httpx streaming.
- Simplification: the shell/Click composition in the old runbook is replaced by one typed workflow;
  individual commands remain focused adapters and the ranking calculation has one callable source.
- Discrepancies from design: production source refresh returns compact local workflow models instead
  of leaking the several existing adapter-specific dataclasses across the port; all required counts,
  diffs, alias provenance, release state, and failures remain represented. Concurrent ranking work
  committed the designed `generate_ranking` extraction in `60cebbf`; this story retains the isolated
  callable/CLI byte-parity regression and composes that seam without rewriting ranking logic.
- Adjacent issues parked: none.

## Verification

- `.venv/bin/python -m pytest -q tests/test_decision_refresh.py
  tests/test_refresh_best_call_ranking.py tests/test_scryfall.py tests/test_releases.py
  tests/test_cli.py tests/test_card_name_resolution.py tests/test_card_coverage_cli.py
  tests/test_runtime_contract.py` — 168 passed.
- `.venv/bin/python -m compileall -q src/legacy_engine/workflows
  src/legacy_engine/ingestion/card_coverage.py scripts/refresh_decision_data.py
  scripts/refresh_best_call_ranking.py` — passed.

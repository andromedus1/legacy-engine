---
id: feature-decision-data-currency-review-fixes
kind: story
stage: done
tags: [ingestion, infra, analytics, bug, tests]
parent: feature-decision-data-currency
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close decision-data currency review findings

Implement the receiver-confirmed findings from the feature's one standard review pass without
expanding the refresh scope or mutating raw provider data.

## Acceptance criteria

- [ ] Manifest-present plus release-scan failure keeps last-good aliases and marks the coverage
      report degraded with a reason naming currency uncertainty.
- [ ] Ranking generation uses a same-directory temporary file and atomic replacement; injected
      write failure leaves an existing ranking output byte-identical.
- [ ] B&R audit data is independent of source-refresh success and never labels `unknown` as
      operator-confirmed.
- [ ] Empty arrays, top-level error objects, missing required provenance, and implausibly incomplete
      all-cards candidates are rejected before last-good download or alias-state replacement.
- [ ] Focused regressions cover each failure path; the integrated feature and full repository suites
      are green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.

## Implementation notes

- Execution capability: frontier/high; the fixes protect externally sourced evidence, the last-good
  ranking artifact, and the truthfulness of operator audit output.
- Review weight: standard (caller); this named fix set closes the existing pass without re-review.
- Files changed: `src/legacy_engine/workflows/decision_refresh.py`,
  `src/legacy_engine/ingestion/scryfall.py`, `src/legacy_engine/ingestion/store.py`,
  `scripts/refresh_best_call_ranking.py`, `tests/test_decision_refresh.py`,
  `tests/test_card_name_resolution.py`, and `tests/test_refresh_best_call_ranking.py`.
- Tests added: manifest-present release-scan uncertainty, source-independent B&R audit, sibling-temp
  atomic-write failure, invalid all-cards shapes/provenance/completeness, and last-good alias-state
  preservation.
- Simplification: orchestration owns one alias-currency uncertainty propagation rule; the provider
  iterator owns one shared row/provenance parser for validation and alias extraction.
- Discrepancies from design: none; every receiver-confirmed finding was fixed in its designed seam.
- Adjacent issues parked: none.

## Verification

- `.venv/bin/python -m pytest -q tests/test_decision_refresh.py
  tests/test_card_name_resolution.py tests/test_refresh_best_call_ranking.py
  tests/test_card_coverage_cli.py tests/test_scryfall.py tests/test_releases.py
  tests/test_runtime_contract.py` — 99 passed.
- Bytecode compilation of every changed production module — passed.
- `.venv/bin/python -m pytest -q` — 3,634 passed, 1 expected optional-stack skip in
  212.94s.

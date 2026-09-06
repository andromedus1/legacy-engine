---
id: feature-ranking-honesty-guards-report-quarantine
kind: story
stage: done
tags: [advisory, analytics]
parent: feature-ranking-honesty-guards
depends_on: [feature-ranking-honesty-guards-ranking-evidence-contract]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Best Call candidacy and imputation quarantine

## Brief

Consume the repaired ranking evidence contract in the Best Call generator and candidate-list CLI.
Assert displayed/ranking coverage parity, exclude inactive camps from headline probability mass,
make genuine zero-cell degradation loud, and add the fixed default label plus opt-in evidence strata.

## Implementation

Implement Unit 2 in the parent feature's `## Implementation Units` section after
`feature-ranking-honesty-guards-ranking-evidence-contract` is done.

## Implementation notes

- Execution capability: inherited frontier model at high effort; the candidate budget and honesty
  presentation directly affect the project's headline recommendation.
- Review weight: standard (caller).
- Files changed: shared positioning evidence classifier, refresh generator/template, candidate-list
  CLI, and their focused tests.
- Tests added/removed: added stratum precedence/complements, historical inactive camp, genuine
  zero-cell warning, page/ranker coverage parity, shared-budget conservation, accessible grouping,
  imputation labels, and invalid CLI option-combination regressions; no tests removed.
- Simplification: page and CLI both consume `ranking_evidence_payload`; only eligible candidates
  enter one `rank_decks` call, and browser grouping reuses serialized rows without recalculation.
- Discrepancies from design: CLI uses the existing `--candidates` option name (the design's
  `--candidates-file` referred to the same option's Python parameter); its generic grounding label
  uses 80% coverage because the CLI has no page top-k contract.
- Adjacent issues parked: none.
- Verification: `tests/test_refresh_best_call_ranking.py tests/test_advise_report.py
  tests/test_positioning.py` — 191 passed.

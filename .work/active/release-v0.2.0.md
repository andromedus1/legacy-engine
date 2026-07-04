---
id: release-v0.2.0
kind: release
stage: quality-gate
tags: []
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# Release v0.2.0

The sideboard-intelligence release: the decomposed scoring model + its flexibility-valuation
repair, the backtest validation surface, the two-mode comparator arc, and the core-and-hedge
solver rework — everything shipped to main between v0.1.0 and PR #27.

## Bound items
- `epic-scorer-flexibility-valuation` (epic)
- `epic-sideboard-core-and-hedge` (epic)
- `epic-sideboard-scoring-model` (epic)
- `epic-sb-config-evaluation-config-comparator` (feature)
- `epic-sb-config-evaluation-matchup-slot-test` (feature)
- `epic-sideboard-core-and-hedge-concave-value` (feature)
- `epic-sideboard-core-and-hedge-dedicated-core` (feature)
- `epic-sideboard-core-and-hedge-gating` (feature)
- `epic-sideboard-core-and-hedge-hedge-allocator` (feature)
- `epic-sideboard-core-and-hedge-output-contract` (feature)
- `feature-sb-board-backtest` (feature)
- `feature-sb-effect-tagging-model` (feature)
- `feature-sb-field-weighted-scorer` (feature)
- `feature-sb-maindeck-aware-coverage` (feature)
- `feature-sb-slot-roi-punt` (feature)
- `feature-sfv-attachments` (feature)
- `feature-sfv-backtest-scoped` (feature)
- `feature-sfv-breadth-objective` (feature)
- `feature-sfv-colorless-axis` (feature)
- `feature-sfv-option-value` (feature)
- `feature-sfv-weights` (feature)
- `document-curated-json-resource-loader-pattern` (story)
- `epic-sb-config-evaluation-config-comparator-cli` (story)
- `epic-sb-config-evaluation-config-comparator-engine` (story)
- `feature-sb-board-backtest-compute` (story)
- `feature-sb-effect-tagging-model-linchpin` (story)
- `feature-sb-effect-tagging-model-vocab-catalog` (story)
- `feature-sb-field-weighted-scorer-impact` (story)
- `feature-sb-field-weighted-scorer-output` (story)
- `feature-sb-field-weighted-scorer-wiring` (story)
- `feature-sb-maindeck-aware-coverage-discount` (story)
- `feature-sb-slot-roi-punt-roi` (story)
- `fix-decklist-parser-skip-comments` (story)
- `fix-loose-end-review-nits` (story)
- `fix-tests-batch2` (story)
- `gate-cruft-import-inventory-merge-param` (story)
- `gate-cruft-parse-decklist-stale-docstring` (story)
- `gate-tests-banlist-exact-boundary` (story)
- `gate-tests-thin-banner-named-reason` (story)
- `test-gaps-coverage-exclusion-e2e` (story)


## Gate runs
- **gate-tests** (2026-07-04) — 18 findings (3 critical, 6 high, 6 medium, 3 low→backlog); 5 vacuous tests flagged; strongest gaps: comparator CLI honesty banners, option-value×τ seam, e2e option-value-active
- **gate-cruft** (2026-07-04) — 5 findings (3 high, 1 medium, 1 low→backlog); zero production-source cruft; all test-file dead code + helper duplication
- **gate-docs** (2026-07-04) — 6 findings (4 foundation-doc-assertion, 1 readme, 1 pattern-anchors); post-epic-2 drift only (mid-bundle doc-review had cleared epic-1); resolved idea-docs-align backlog item deleted
- **gate-patterns** — pending (runs after the finding drain)

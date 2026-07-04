---
id: release-v0.2.0
kind: release
stage: released
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


## Ship record

- Shipped: 2026-07-04 · mapping: tag-based (PR to main, CI green, tag v0.2.0 on the merge commit)
- Items shipped: 66 (40 bound at planning + 26 gate-produced)
- Gate findings: tests 18 (15 drained + 3 low->backlog) · cruft 5 (4 drained + 1 low->backlog) · docs 6 (drained) · patterns 3 extracted (+2 unbound refactor stories for the next cycle)
- Suite at ship: 2578 passing + 1 documented xfail (bug-re-graveyard-their-template)

## Gate runs
- **gate-tests** (2026-07-04) — 18 findings (3 critical, 6 high, 6 medium, 3 low→backlog); 5 vacuous tests flagged; strongest gaps: comparator CLI honesty banners, option-value×τ seam, e2e option-value-active
- **gate-cruft** (2026-07-04) — 5 findings (3 high, 1 medium, 1 low→backlog); zero production-source cruft; all test-file dead code + helper duplication
- **gate-docs** (2026-07-04) — 6 findings (4 foundation-doc-assertion, 1 readme, 1 pattern-anchors); post-epic-2 drift only (mid-bundle doc-review had cleared epic-1); resolved idea-docs-align backlog item deleted
- **gate-patterns** — pending (runs after the finding drain)

## Shipped items

Bodies live in git history — read with `git show 3db5822:<path>`.

| id | title | kind | archived_atop | git ref |
|----|-------|------|---------------|---------|
| epic-scorer-flexibility-valuation | Scorer flexibility valuation — model breadth from first principles | epic | — | 3db5822 (.work/active/epics/epic-scorer-flexibility-valuation.md) |
| epic-sideboard-core-and-hedge | Sideboard solver: two-stage core + hedge | epic | — | 3db5822 (.work/active/epics/epic-sideboard-core-and-hedge.md) |
| epic-sideboard-scoring-model | Sideboard scoring model | epic | — | 3db5822 (.work/active/epics/epic-sideboard-scoring-model.md) |
| epic-sb-config-evaluation-config-comparator | Configuration / transform comparator (general engine, transform-first) | feature | — | 3db5822 (.work/active/features/epic-sb-config-evaluation-config-comparator.md) |
| epic-sb-config-evaluation-matchup-slot-test | Matchup-conditioned sideboard-slot test | feature | — | 3db5822 (.work/active/features/epic-sb-config-evaluation-matchup-slot-test.md) |
| epic-sideboard-core-and-hedge-concave-value | Concave per-copy value model | feature | — | 3db5822 (.work/active/features/epic-sideboard-core-and-hedge-concave-value.md) |
| epic-sideboard-core-and-hedge-dedicated-core | Stage-1 dedicated-core solver + natural-budget τ | feature | — | 3db5822 (.work/active/features/epic-sideboard-core-and-hedge-dedicated-core.md) |
| epic-sideboard-core-and-hedge-gating | Gating + operator controls (core wave) | feature | — | 3db5822 (.work/active/features/epic-sideboard-core-and-hedge-gating.md) |
| epic-sideboard-core-and-hedge-hedge-allocator | Stage-2 hedge allocator (FAST-FOLLOW) | feature | — | 3db5822 (.work/active/features/epic-sideboard-core-and-hedge-hedge-allocator.md) |
| epic-sideboard-core-and-hedge-output-contract | Output contract: <15 return, labels, marginal-coverage curve, uncovere | feature | — | 3db5822 (.work/active/features/epic-sideboard-core-and-hedge-output-contract.md) |
| feature-sb-board-backtest | Backtest recommended boards vs top-finisher boards | feature | — | 3db5822 (.work/active/features/feature-sb-board-backtest.md) |
| feature-sb-effect-tagging-model | Effect-tagging + hoser catalog: linchpin, symmetry, color-contingent,  | feature | — | 3db5822 (.work/active/features/feature-sb-effect-tagging-model.md) |
| feature-sb-field-weighted-scorer | Field-weighted card scorer (coverage diagnostic + decomposed impact) | feature | — | 3db5822 (.work/active/features/feature-sb-field-weighted-scorer.md) |
| feature-sb-maindeck-aware-coverage | Maindeck-aware coverage (stop double-counting axes the deck already an | feature | — | 3db5822 (.work/active/features/feature-sb-maindeck-aware-coverage.md) |
| feature-sb-slot-roi-punt | Sideboard slot ROI / punt detection | feature | — | 3db5822 (.work/active/features/feature-sb-slot-roi-punt.md) |
| feature-sfv-attachments | Attachments: plays-<color> as opponent vulnerability + broad-interacti | feature | — | 3db5822 (.work/active/features/feature-sfv-attachments.md) |
| feature-sfv-backtest-scoped | Field/window-scoped backtest as the acceptance harness | feature | — | 3db5822 (.work/active/features/feature-sfv-backtest-scoped.md) |
| feature-sfv-breadth-objective | Breadth aggregation: reformulate the coverage objective to true submod | feature | — | 3db5822 (.work/active/features/feature-sfv-breadth-objective.md) |
| feature-sfv-colorless-axis | Colorless/trigger vulnerability axis — close the Consign acceptance cr | feature | — | 3db5822 (.work/active/features/feature-sfv-colorless-axis.md) |
| feature-sfv-option-value | Option value: CVaR tail-robustness over the Dirichlet field | feature | — | 3db5822 (.work/active/features/feature-sfv-option-value.md) |
| feature-sfv-weights | Element-weight repair: remove draw-prob deflation; make _hate self-pro | feature | — | 3db5822 (.work/active/features/feature-sfv-weights.md) |
| document-curated-json-resource-loader-pattern | Document `curated-json-resource-loader` pattern (gate-patterns) | story | — | 3db5822 (.work/active/stories/document-curated-json-resource-loader-pattern.md) |
| epic-sb-config-evaluation-config-comparator-cli | `advise compare` CLI leaf + rendering | story | — | 3db5822 (.work/active/stories/epic-sb-config-evaluation-config-comparator-cli.md) |
| epic-sb-config-evaluation-config-comparator-engine | Config comparator engine (model + point EV + MC base + slot-lift pull) | story | — | 3db5822 (.work/active/stories/epic-sb-config-evaluation-config-comparator-engine.md) |
| feature-sb-board-backtest-compute | Backtest recommended boards vs top-finisher boards + CLI | story | — | 3db5822 (.work/active/stories/feature-sb-board-backtest-compute.md) |
| feature-sb-effect-tagging-model-linchpin | Linchpin hybrid model (derive + curated overrides) | story | — | 3db5822 (.work/active/stories/feature-sb-effect-tagging-model-linchpin.md) |
| feature-sb-effect-tagging-model-vocab-catalog | Vocabulary replace + HoserCard model + catalog rewrite + wire into cur | story | — | 3db5822 (.work/active/stories/feature-sb-effect-tagging-model-vocab-catalog.md) |
| feature-sb-field-weighted-scorer-impact | Impact factors + hoser→linchpin capability bridge | story | — | 3db5822 (.work/active/stories/feature-sb-field-weighted-scorer-impact.md) |
| feature-sb-field-weighted-scorer-output | Explainable breakdown + coverage% diagnostic + field-share uncertainty | story | — | 3db5822 (.work/active/stories/feature-sb-field-weighted-scorer-output.md) |
| feature-sb-field-weighted-scorer-wiring | Wire impact into the coverage model + draw-prob copy-shaping in the IL | story | — | 3db5822 (.work/active/stories/feature-sb-field-weighted-scorer-wiring.md) |
| feature-sb-maindeck-aware-coverage-discount | Maindeck-coverage discount on SB element weights | story | — | 3db5822 (.work/active/stories/feature-sb-maindeck-aware-coverage-discount.md) |
| feature-sb-slot-roi-punt-roi | Slot-ROI table + punt detection + render | story | — | 3db5822 (.work/active/stories/feature-sb-slot-roi-punt-roi.md) |
| fix-decklist-parser-skip-comments |  | story | — | 3db5822 (.work/active/stories/fix-decklist-parser-skip-comments.md) |
| fix-loose-end-review-nits |  | story | — | 3db5822 (.work/active/stories/fix-loose-end-review-nits.md) |
| fix-tests-batch2 | Test-coverage gaps: batch 2 (gate-tests, Medium/Low) | story | — | 3db5822 (.work/active/stories/fix-tests-batch2.md) |
| gate-cruft-import-inventory-merge-param | `merge` parameter on `import_inventory` is documentary-only — never re | story | — | 3db5822 (.work/active/stories/gate-cruft-import-inventory-merge-param.md) |
| gate-cruft-parse-decklist-stale-docstring | Stale "previously said" migration prose in `_parse_decklist` docstring | story | — | 3db5822 (.work/active/stories/gate-cruft-parse-decklist-stale-docstring.md) |
| gate-cruft-test-dup-import | Drop duplicate _build_coverage_model import (F811) in test_sideboard.p | story | — | 3db5822 (.work/active/stories/gate-cruft-test-dup-import.md) |
| gate-cruft-test-helper-duplication | Promote duplicated _con/_make_field/_make_card test helpers to conftes | story | — | 3db5822 (.work/active/stories/gate-cruft-test-helper-duplication.md) |
| gate-cruft-test-unused-imports | Remove 17 unused imports (F401) across bundle test files | story | — | 3db5822 (.work/active/stories/gate-cruft-test-unused-imports.md) |
| gate-cruft-test-unused-locals | Remove 5 unused locals (F841) in test files; verify one lost assertion | story | — | 3db5822 (.work/active/stories/gate-cruft-test-unused-locals.md) |
| gate-docs-arch-score-without-drawprob | ARCHITECTURE sideboard.py row cites .score() for element weights (draw | story | — | 3db5822 (.work/active/stories/gate-docs-arch-score-without-drawprob.md) |
| gate-docs-backtest-field-scope | advise backtest --field-scope flag undocumented | story | — | 3db5822 (.work/active/stories/gate-docs-backtest-field-scope.md) |
| gate-docs-pattern-anchors | Pattern-skill file:line anchors into sideboard.py shifted | story | — | 3db5822 (.work/active/stories/gate-docs-pattern-anchors.md) |
| gate-docs-readme-test-count | README test count stale (2464 -> current) | story | — | 3db5822 (.work/active/stories/gate-docs-readme-test-count.md) |
| gate-docs-spec-element-weight-drawprob | SPEC pillar-4 says element weight includes draw-probability | story | — | 3db5822 (.work/active/stories/gate-docs-spec-element-weight-drawprob.md) |
| gate-docs-vocab-12-tags | Vulnerability-tag vocabulary omits noncreature-reliant + colorless-rel | story | — | 3db5822 (.work/active/stories/gate-docs-vocab-12-tags.md) |
| gate-patterns-v0.2.0 | Patterns extracted for v0.2.0 | story | — | 3db5822 (.work/active/stories/gate-patterns-v0.2.0.md) |
| gate-tests-banlist-exact-boundary | As-of-date legality: pin the exact ban-date boundary (legal day-before | story | — | 3db5822 (.work/active/stories/gate-tests-banlist-exact-boundary.md) |
| gate-tests-catalog-blast-rows | Shipped catalog blast rows not directly asserted | story | — | 3db5822 (.work/active/stories/gate-tests-catalog-blast-rows.md) |
| gate-tests-cli-honesty-renders | CLI honesty renders weak: thin-n banner untested; lift-slot test branc | story | — | 3db5822 (.work/active/stories/gate-tests-cli-honesty-renders.md) |
| gate-tests-compare-honesty-banners | advise compare mandatory honesty banners have no test | story | — | 3db5822 (.work/active/stories/gate-tests-compare-honesty-banners.md) |
| gate-tests-contrast-custom-window | CLI custom single-window branch for --contrast untested | story | — | 3db5822 (.work/active/stories/gate-tests-contrast-custom-window.md) |
| gate-tests-fisher-nonsig-realistic | Non-significant Fisher case tested with degenerate 0.0-diff split | story | — | 3db5822 (.work/active/stories/gate-tests-fisher-nonsig-realistic.md) |
| gate-tests-ilp-firstcopy-and-tau-exact | ILP option-value first-copy-only + tau exact-stop weaker than greedy | story | — | 3db5822 (.work/active/stories/gate-tests-ilp-firstcopy-and-tau-exact.md) |
| gate-tests-lift-lower-clamp | Negative lift lower clamp (floor 0.0) untested | story | — | 3db5822 (.work/active/stories/gate-tests-lift-lower-clamp.md) |
| gate-tests-mc-base-lift-invariance | MC base layer lift-invariance contract untested | story | — | 3db5822 (.work/active/stories/gate-tests-mc-base-lift-invariance.md) |
| gate-tests-optionvalue-e2e-active | Option value never runs ACTIVE end-to-end through recommend_sideboard | story | — | 3db5822 (.work/active/stories/gate-tests-optionvalue-e2e-active.md) |
| gate-tests-pair-adaptive-later-since | Adaptive pair-window later-of-two valid_since path untested | story | — | 3db5822 (.work/active/stories/gate-tests-pair-adaptive-later-since.md) |
| gate-tests-slot-exclusion-parity | Slot-test exclusion parity: byes + unmatched untested | story | — | 3db5822 (.work/active/stories/gate-tests-slot-exclusion-parity.md) |
| gate-tests-symmetry-color-axis | plays-<color> axis never exercised through symmetry_factor | story | — | 3db5822 (.work/active/stories/gate-tests-symmetry-color-axis.md) |
| gate-tests-tau-optionvalue-composition | Pin + document the tau-stop x option-value-bonus composition | story | — | 3db5822 (.work/active/stories/gate-tests-tau-optionvalue-composition.md) |
| gate-tests-thin-banner-named-reason | Thin-regime banner: assert the named reason (round count + floor), not | story | — | 3db5822 (.work/active/stories/gate-tests-thin-banner-named-reason.md) |
| gate-tests-transform-mode-render | Transform chosen-mode rendering tested vacuously | story | — | 3db5822 (.work/active/stories/gate-tests-transform-mode-render.md) |
| gate-tests-uncovered-tail-content | uncovered_tail content never verified (vacuous type-only test) | story | — | 3db5822 (.work/active/stories/gate-tests-uncovered-tail-content.md) |
| test-gaps-coverage-exclusion-e2e |  | story | — | 3db5822 (.work/active/stories/test-gaps-coverage-exclusion-e2e.md) |

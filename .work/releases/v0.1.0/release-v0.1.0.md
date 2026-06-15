---
id: release-v0.1.0
kind: release
stage: released
tags: []
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Release v0.1.0

Maiden release. Binds the full MVP: foundations & card data, tournament ingestion, archetype
classifier, meta & performance analytics, the advisory pillar (positioning, sideboard, what-to-play,
field-read report) with output-honesty and regime-aware windowing, deck generation, gap discovery,
the deck-viz platform, plus all peer-review correctness fixes and gate-produced cruft/docs/test items.

Deferred (unbound): goldfish-simulation, local-meta geo dimension, web interface.

## Bound items

116 items shipped (the full MVP + 9 gate-produced findings drained to done). Full list in the Shipped-items table below.

## Gate runs

- **gate-tests** (2026-06-14) — 3 findings (1 Critical, 2 Low). Critical: ingestion resilience NFR
  unhonored + untested (one bad deck/event aborts the batch) -> gate-tests-ingestion-bad-deck-resilience
  (implementing). 2 Low -> backlog (thin-banner named-reason, ban-date boundary). Coverage otherwise
  strong; 2 candidate gaps confirmed false-positive. 3 prior gate-tests findings already done.
- **gate-cruft** (2026-06-14) — 6 findings (1 High, 3 Medium, 2 Low). High: 9 unused imports (ruff
  F401) -> gate-cruft-unused-imports. Medium -> deck-load --format ignored, report new-cards --db
  ignored, overprice_factor dead param. 2 Low -> backlog. No new dead funcs/shims (2 prior sweeps).
- **gate-docs** (2026-06-14) — 6 findings, all High (3 items). report new-cards mischaracterized as
  forecaster in SPEC+README -> gate-docs-new-cards-mischaracterized; report variants mislabeled in
  README -> gate-docs-variants-readme; stale cli.py line anchors in 3 pattern skills ->
  gate-docs-pattern-skill-cli-anchors. ARCHITECTURE clean; module-relative refs all resolve.
- **gate-patterns** (2026-06-14) — 2 new patterns, 0 inconsistencies. viz-spec-render-write-tail,
  file-backed-cli-test-db-builder. SKILL.md index regenerated (was stale at 5/12); digest updated.
  Tracking item gate-patterns-v0.1.0 (done).


## Ship
- Date shipped: 2026-06-14
- Mapping: tag-based (git tag `v0.1.0` on the merge commit; all work flows through `main` via PR, CI green before merge)
- Total items shipped: 116 (107 MVP done items + 9 gate-produced findings)
- Gate finding totals: tests 3 (1 critical + 2 low-backlog), cruft 6 (1 high + 3 med + 2 low-backlog), docs 6 (all high), patterns 2 new (0 inconsistencies)

## Shipped items

Bodies live in git history — read with `git show <git ref>:<path>`.

| id | title | kind | archived_atop | git ref |
|----|-------|------|---------------|---------|
| epic-advisory-hardening | Advisory Pillar Hardening | epic | — | ae9265f |
| epic-advisory-output-honesty | Advisory Output Honesty | epic | — | ae9265f |
| epic-advisory | Meta Attack / Advisory | epic | — | ae9265f |
| epic-archetype-classifier | Archetype Classifier | epic | — | ae9265f |
| epic-bigmana-coverage-sideboard-fidelity | Big-Mana Coverage & Sideboard Fidelity | epic | — | ae9265f |
| epic-deck-generation | Deck Generation (deferred pillar) | epic | — | ae9265f |
| epic-deck-viz-platform | Deck Visualization Platform | epic | — | ae9265f |
| epic-foundations-card-data | Foundations & Card Data | epic | — | ae9265f |
| epic-gap-discovery | Gap Discovery (deck generation mode 3) | epic | — | ae9265f |
| epic-meta-analytics | Meta & Performance Analytics | epic | — | ae9265f |
| epic-regime-aware-advisory | Regime-Aware Advisory | epic | — | ae9265f |
| epic-tournament-ingestion | Tournament Ingestion | epic | — | ae9265f |
| epic-advisory-field-model | Field Distribution Model (global + custom field) | feature | — | ae9265f |
| epic-advisory-output-honesty-coverage-consumers | Coverage Honesty Across the Remaining Positioning Consumers | feature | — | ae9265f |
| epic-advisory-output-honesty-field-consistency | Field & Regime Consistency | feature | — | ae9265f |
| epic-advisory-output-honesty-positioning-coverage | Positioning Coverage & Confidence | feature | — | ae9265f |
| epic-advisory-output-honesty-transparency | Output Transparency Labeling | feature | — | ae9265f |
| epic-advisory-output-honesty-whattoplay-honesty | Honest "What to Play" Output | feature | — | ae9265f |
| epic-advisory-positioning | Meta-Positioning Score (Bayesian Monte-Carlo) | feature | — | ae9265f |
| epic-advisory-report | Field Read & Deck Recommendation Report (advise CLI surface) | feature | — | ae9265f |
| epic-advisory-sideboard | Sideboard Recommender (weighted max-coverage: ILP + greedy) | feature | — | ae9265f |
| epic-advisory-whattoplay | What-to-Play Advisor (proactivity · vulnerability · hate-equity) | feature | — | ae9265f |
| epic-archetype-classifier-labeler | Labeler + `legacy label` CLI | feature | — | ae9265f |
| epic-archetype-classifier-matcher | Matcher Port + Golden Tests (fixtures) | feature | — | ae9265f |
| epic-archetype-classifier-rules-loader | Rules Vendoring + Typed Rule Loader | feature | — | ae9265f |
| epic-deck-generation-consensus | Consensus baseline deck generation | feature | — | ae9265f |
| epic-deck-generation-export | Portable decklist export (Moxfield-as-import + multi-target) | feature | — | ae9265f |
| epic-deck-generation-per-card-value | Per-card win-rate (overall + per-card×matchup) | feature | — | ae9265f |
| epic-deck-generation-sideboard-maindeck | Maindeck-aware sideboard (per-matchup OUT/IN plan) | feature | — | ae9265f |
| epic-deck-generation-tuning | Field-tuning (optimize a shell against the field) | feature | — | ae9265f |
| epic-deck-viz-platform-charts-migration | charts.py Migration — Vega-Lite builders replace matplotlib | feature | — | ae9265f |
| epic-deck-viz-platform-dashboard | Per-Deck Dashboard + viz CLI | feature | — | ae9265f |
| epic-deck-viz-platform-foundation | viz/ Foundation — theme, strip-and-inject, render, validation | feature | — | ae9265f |
| epic-foundations-card-data-banlist-snapshots | Ban-List Snapshots & Legality Validation | feature | — | ae9265f |
| epic-foundations-card-data-card-derivations | Card Derivations: Deck-Color Helper & Legacy Tags | feature | — | ae9265f |
| epic-foundations-card-data-card-model-scryfall | Card Model & Scryfall Ingestion | feature | — | ae9265f |
| epic-foundations-card-data-duckdb-store | DuckDB Analytical Store | feature | — | ae9265f |
| epic-foundations-card-data-package-skeleton | Package Skeleton, Config & Shared Model Base | feature | — | ae9265f |
| epic-gap-discovery-adjacency | Card-Adjacency Model (candidate nomination) | feature | — | ae9265f |
| epic-gap-discovery-archetype-gaps | Archetype-Gap Finder (`report gaps`) | feature | — | ae9265f |
| epic-gap-discovery-discovery-tuning | Discovery Tuning (value transfer + gated suggestion surface) | feature | — | ae9265f |
| epic-meta-analytics-charts | Analytics Charts (tier list · meta share · matchup heatmap · trends) | feature | — | ae9265f |
| epic-meta-analytics-match-results | Match-Outcome Extraction (rounds → archetype win/loss) | feature | — | ae9265f |
| epic-meta-analytics-matchup-matrix | Matchup Matrix (Wilson + Beta-Binomial shrinkage + tiers) | feature | — | ae9265f |
| epic-meta-analytics-metashare | Meta-Share Computation (three labeled definitions) | feature | — | ae9265f |
| epic-meta-analytics-trends | Meta Trends Across Ban-List Regimes (version-stamped) | feature | — | ae9265f |
| epic-regime-aware-advisory-adaptive | Adaptive Per-Cell Windowing (v2) | feature | — | ae9265f |
| epic-regime-aware-advisory-cli-surface | CLI Surface + Thin-Regime Degrade (v1 UX) | feature | — | ae9265f |
| epic-regime-aware-advisory-windowing-core | Windowing Core (v1 plumbing) | feature | — | ae9265f |
| epic-tournament-ingestion-cache-mirror | Cache Mirror + `seed cache` Wiring | feature | — | ae9265f |
| epic-tournament-ingestion-cache-parser | Cache Parser: Models + CacheItem Parsing + Provenance | feature | — | ae9265f |
| epic-tournament-ingestion-duckdb-tables | DuckDB Tournament Tables + Load | feature | — | ae9265f |
| feature-advise-provenance-flag | Thread `--provenance` through the advise commands | feature | — | ae9265f |
| feature-analytics-reporting-completeness | Analytics Reporting Completeness | feature | — | ae9265f |
| feature-archetype-empirical-recommendations | feature-archetype-empirical-recommendations | feature | — | ae9265f |
| feature-bigmana-ramp-tag | `ramp`/`big-mana` vulnerability tag + hoser mappings | feature | — | ae9265f |
| feature-card-count-outlier-advisor | feature-card-count-outlier-advisor | feature | — | ae9265f |
| feature-collection-aware-engine | advisory/collection.py | feature | — | ae9265f |
| feature-considering-cards-pool | Emit a ~30-card "considering" pool, not just the final 15 | feature | — | ae9265f |
| feature-curated-price-source | ingestion/prices.py | feature | — | ae9265f |
| feature-custom-field-counts-normalization | Custom fields carry counts + tightened normalization | feature | — | ae9265f |
| feature-deck-tuning-refresh-workflow | feature-deck-tuning-refresh-workflow | feature | — | ae9265f |
| feature-empirical-sideboard-swings | Empirical sideboard swing magnitudes where data supports | feature | — | ae9265f |
| feature-hoser-catalog-expansion | Expand HOSER_CATALOG + move to an editable data file | feature | — | ae9265f |
| feature-list-granular-positioning | feature-list-granular-positioning | feature | — | ae9265f |
| feature-new-set-ingestion-and-speculation | store.py — new | feature | — | ae9265f |
| feature-oracle-text-interaction-tags | feature-oracle-text-interaction-tags | feature | — | ae9265f |
| feature-personal-inventory-and-decks | models/collection.py | feature | — | ae9265f |
| feature-regime-windowing-consistency | feature-regime-windowing-consistency | feature | — | ae9265f |
| feature-standalone-field-read | Standalone field-read (no deck required) | feature | — | ae9265f |
| feature-strong-player-signal | analytics/players/identity.py   (story 1) | feature | — | ae9265f |
| feature-subarchetype-variants | feature-subarchetype-variants | feature | — | ae9265f |
| feature-three-venue-meta-frame | analytics/venue.py | feature | — | ae9265f |
| fix-advisory-peer-review-bugs | Advisory correctness bugs (cross-model peer review, Codex xhigh) | feature | — | ae9265f |
| fix-analytics-peer-review-findings | Analytics correctness findings (cross-model peer review, Codex xhigh) | feature | — | ae9265f |
| fix-spine-peer-review-findings | Ingestion + archetype-spine findings (cross-model peer review, Codex xhigh) | feature | — | ae9265f |
| improve-positioning-pbest-uneven-sample | Positioning P(best) is biased toward thin-matchup-data decks | feature | — | ae9265f |
| improve-sideboard-realdata-quality | Sideboard recommender under-delivers on real data (budget under-fill + tag inflation) | feature | — | ae9265f |
| improve-whattoplay-proactivity-threat-signal | Calibrate whattoplay proactivity: add an aggressive-threat signal | feature | — | ae9265f |
| document-bundle-patterns | Document 4 new patterns (gate-patterns) | story | — | ae9265f |
| fix-analytics-peer-review-findings-data-integrity | Cardinality-safe rounds join + bye classification (findings 1 rounds-half, 7) | story | — | ae9265f |
| fix-analytics-peer-review-findings-matchup-trends | Mirror inclusion + top-cut trends denominator (findings 2, 8) | story | — | ae9265f |
| fix-analytics-peer-review-findings-metashare | Metashare coverage + blend fixes (findings 1 top-cut-half, 3, 4, 5, 6) | story | — | ae9265f |
| fix-cruft-batch2 | Cruft sweep: batch 2 (gate-cruft, 1 High + Medium/Low) | story | — | ae9265f |
| fix-cruft-dead-code-sweep | Dead-code / stale-comment sweep (gate-cruft) | story | — | ae9265f |
| fix-deck-dashboard-readability | Fix: deck-dashboard readability (Andrew feedback) | story | — | ae9265f |
| fix-docs-drift-batch2 | Foundation-doc drift: batch 2 (PRs #8-#11) (gate-docs, 3 High + Medium) | story | — | ae9265f |
| fix-foundation-doc-drift | Foundation-doc drift: ARCHITECTURE + SPEC (gate-docs, High) | story | — | ae9265f |
| fix-infra-ijson-and-ci-lint | Infra: declare ijson; CI lint; path/SSRF hardening (gate-infra/security, Medium+Low) | story | — | ae9265f |
| fix-recommendation-test-coverage | Recommendation-quality + threading test gaps (gate-tests, Medium) | story | — | ae9265f |
| fix-roundmatch-null-player2 | Fix: ingestion crashes on a bye's null Player2 | story | — | ae9265f |
| fix-ruleset-trailing-comma | Fix: load_ruleset crashes on trailing commas in upstream rule files | story | — | ae9265f |
| fix-scryfall-face-indexing-db | Fix: DuckDB cards table misses multi-face front-face names | story | — | ae9265f |
| fix-sideboard-surface-field-staples | Sideboard recommender structurally can't surface field staples (ROOT CAUSE) | story | — | ae9265f |
| fix-spine-peer-review-findings-classifier | Matcher contract fidelity (findings 1-4) | story | — | ae9265f |
| fix-spine-peer-review-findings-correctness | Rules SHA pinning + validate_deck enforcement (findings 5, 7) | story | — | ae9265f |
| fix-spine-peer-review-findings-hardening | Ingestion edge hardening (findings 6, 8, 9) | story | — | ae9265f |
| fix-trends-timestamp-date-span | Fix: trends crashes on full-timestamp tournament dates | story | — | ae9265f |
| fix-tuner-core-protection | Tuner over-cuts high-inclusion core cards | story | — | ae9265f |
| fix-tuning-sideboard-winrate-reuse | fix-tuning-sideboard-winrate-reuse | story | — | ae9265f |
| fix-venues-regime-default | `report meta --venues` should default to current regime (gate-tests / test-drive) | story | — | ae9265f |
| gate-cruft-deck-load-format-ignored | `deck load --format` is fully ignored — advertises 5 formats, delivers one | story | — | ae9265f |
| gate-cruft-overprice-factor-dead-param | `overprice_factor` threaded into the pure ranking core but never used there | story | — | ae9265f |
| gate-cruft-report-new-cards-db-ignored | `report new-cards --db` is silently ignored | story | — | ae9265f |
| gate-cruft-unused-imports | Unused imports — 9 sites (ruff F401-verified) | story | — | ae9265f |
| gate-docs-new-cards-mischaracterized | SPEC + README mischaracterize `report new-cards` as a speculative forecaster | story | — | ae9265f |
| gate-docs-pattern-skill-cli-anchors | Pattern-skill canonical examples cite stale cli.py line anchors (3 files, one root cause) | story | — | ae9265f |
| gate-docs-variants-readme | README mislabels `report variants` as "per-variant card inclusion divergence" | story | — | ae9265f |
| gate-patterns-v0.1.0 | Patterns extracted for v0.1.0 | story | — | ae9265f |
| gate-tests-ingestion-bad-deck-resilience | Ingestion does not tolerate one bad deck/event (resilience NFR unhonored + untested) | story | — | ae9265f |
| new-set-ingestion-and-speculation-analogous-matcher | new-set-ingestion-and-speculation-analogous-matcher | story | — | ae9265f |
| personal-inventory-and-decks-my-deck-integration | `--my-deck NAME` integration into the existing decklist-consuming leaves | story | — | ae9265f |
| personal-inventory-and-decks-printing-aware-allocation | Printing/condition-aware allocation (the $33-vs-$2 Dismember refinement) | story | — | ae9265f |
| strong-player-signal-consensus | Player-filtered consensus / tune — regime-safe, gated-additive | story | — | ae9265f |
| strong-player-signal-identity | Player identity resolution — curated alias table + heuristic suggester | story | — | ae9265f |
| strong-player-signal-strength | Player strength scoring + archetype-history tracking | story | — | ae9265f |

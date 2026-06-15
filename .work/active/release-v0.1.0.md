---
id: release-v0.1.0
kind: release
stage: quality-gate
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

107 done items (entire MVP), late-bound at release time. Grouped:

### epics
- epic-advisory
- epic-advisory-hardening
- epic-advisory-output-honesty
- epic-archetype-classifier
- epic-bigmana-coverage-sideboard-fidelity
- epic-deck-generation
- epic-deck-viz-platform
- epic-foundations-card-data
- epic-gap-discovery
- epic-meta-analytics
- epic-regime-aware-advisory
- epic-tournament-ingestion

### features
- epic-advisory-field-model
- epic-advisory-output-honesty-coverage-consumers
- epic-advisory-output-honesty-field-consistency
- epic-advisory-output-honesty-positioning-coverage
- epic-advisory-output-honesty-transparency
- epic-advisory-output-honesty-whattoplay-honesty
- epic-advisory-positioning
- epic-advisory-report
- epic-advisory-sideboard
- epic-advisory-whattoplay
- epic-archetype-classifier-labeler
- epic-archetype-classifier-matcher
- epic-archetype-classifier-rules-loader
- epic-deck-generation-consensus
- epic-deck-generation-export
- epic-deck-generation-per-card-value
- epic-deck-generation-sideboard-maindeck
- epic-deck-generation-tuning
- epic-deck-viz-platform-charts-migration
- epic-deck-viz-platform-dashboard
- epic-deck-viz-platform-foundation
- epic-foundations-card-data-banlist-snapshots
- epic-foundations-card-data-card-derivations
- epic-foundations-card-data-card-model-scryfall
- epic-foundations-card-data-duckdb-store
- epic-foundations-card-data-package-skeleton
- epic-gap-discovery-adjacency
- epic-gap-discovery-archetype-gaps
- epic-gap-discovery-discovery-tuning
- epic-meta-analytics-charts
- epic-meta-analytics-match-results
- epic-meta-analytics-matchup-matrix
- epic-meta-analytics-metashare
- epic-meta-analytics-trends
- epic-regime-aware-advisory-adaptive
- epic-regime-aware-advisory-cli-surface
- epic-regime-aware-advisory-windowing-core
- epic-tournament-ingestion-cache-mirror
- epic-tournament-ingestion-cache-parser
- epic-tournament-ingestion-duckdb-tables
- feature-advise-provenance-flag
- feature-analytics-reporting-completeness
- feature-archetype-empirical-recommendations
- feature-bigmana-ramp-tag
- feature-card-count-outlier-advisor
- feature-collection-aware-engine
- feature-considering-cards-pool
- feature-curated-price-source
- feature-custom-field-counts-normalization
- feature-deck-tuning-refresh-workflow
- feature-empirical-sideboard-swings
- feature-hoser-catalog-expansion
- feature-list-granular-positioning
- feature-new-set-ingestion-and-speculation
- feature-oracle-text-interaction-tags
- feature-personal-inventory-and-decks
- feature-regime-windowing-consistency
- feature-standalone-field-read
- feature-strong-player-signal
- feature-subarchetype-variants
- feature-three-venue-meta-frame
- fix-advisory-peer-review-bugs
- fix-analytics-peer-review-findings
- fix-spine-peer-review-findings
- improve-positioning-pbest-uneven-sample
- improve-sideboard-realdata-quality
- improve-whattoplay-proactivity-threat-signal

### storys
- document-bundle-patterns
- fix-analytics-peer-review-findings-data-integrity
- fix-analytics-peer-review-findings-matchup-trends
- fix-analytics-peer-review-findings-metashare
- fix-cruft-batch2
- fix-cruft-dead-code-sweep
- fix-deck-dashboard-readability
- fix-docs-drift-batch2
- fix-foundation-doc-drift
- fix-infra-ijson-and-ci-lint
- fix-recommendation-test-coverage
- fix-roundmatch-null-player2
- fix-ruleset-trailing-comma
- fix-scryfall-face-indexing-db
- fix-sideboard-surface-field-staples
- fix-spine-peer-review-findings-classifier
- fix-spine-peer-review-findings-correctness
- fix-spine-peer-review-findings-hardening
- fix-trends-timestamp-date-span
- fix-tuner-core-protection
- fix-tuning-sideboard-winrate-reuse
- fix-venues-regime-default
- new-set-ingestion-and-speculation-analogous-matcher
- personal-inventory-and-decks-my-deck-integration
- personal-inventory-and-decks-printing-aware-allocation
- strong-player-signal-consensus
- strong-player-signal-identity
- strong-player-signal-strength

## Gate runs

- **gate-tests** (2026-06-14) — 3 findings (1 Critical, 2 Low). Critical: ingestion resilience NFR
  unhonored + untested (one bad deck/event aborts the batch) -> gate-tests-ingestion-bad-deck-resilience
  (implementing). 2 Low -> backlog (thin-banner named-reason, ban-date boundary). Coverage otherwise
  strong; 2 candidate gaps confirmed false-positive. 3 prior gate-tests findings already done.
- **gate-cruft** (2026-06-14) — 6 findings (1 High, 3 Medium, 2 Low). High: 9 unused imports (ruff
  F401) -> gate-cruft-unused-imports. Medium -> deck-load --format ignored, report new-cards --db
  ignored, overprice_factor dead param. 2 Low -> backlog. No new dead funcs/shims (2 prior sweeps).

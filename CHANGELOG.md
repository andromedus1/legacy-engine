# Changelog

## v0.1.0

Maiden release. A local-first MTG Legacy analytics engine: ingest tournament data, classify
archetypes, model the meta, and produce honest, regime-aware advisory output. Honest degradation
under thin/absent data is the engine's defining property — every derived stat carries a confidence
tier, and thin signal is labeled, never silently smoothed over.

### Foundations & card data
- Pydantic model base (`LegacyEngineModel`), constants-only config, package skeleton.
- Scryfall card ingestion + DuckDB analytical store (raw JSON is the source of truth; DuckDB tables
  are rebuildable derived caches).
- Dated ban-list snapshots with version-stamped legality — a deck validates against the ban-list in
  force on its date.
- Card derivations: deck-color helper, Legacy interaction tags, oracle-text interaction facts.

### Tournament ingestion
- Mirror + parse the community fbettega cache (online MTGO + paper Melee/Topdeck), with provenance
  derivation and DuckDB tournament tables.
- Resilient ingestion: a single malformed deck or event is logged and skipped, never aborting the
  batch.

### Archetype classifier
- Ported MTGOArchetypeParser matcher with vendored rules, a typed rule loader, color logic, the
  labeler + `legacy label` CLI, golden tests, and sub-archetype variants.

### Meta & performance analytics
- Meta-share (three labeled definitions), matchup matrix (Wilson + two-level beta-binomial
  shrinkage + tiers), match-outcome extraction, and regime-aware trends across ban-list
  announcements.
- Player identity resolution, confidence-gated strength scoring, archetype-history tracking, and a
  three-venue meta frame.
- Analytics charts (tier list, meta share, matchup heatmap, trends).

### Advisory (meta attack)
- Meta-positioning score (Bayesian Monte-Carlo), sideboard recommender (weighted max-coverage:
  ILP + greedy), what-to-play advisor (proactivity · vulnerability · hate-equity), and the
  field-read + deck-recommendation report (`advise` surface).
- Field distribution model (global + custom field), standalone field-read, list-granular
  (deck-as-individual-cards) positioning, and a `--provenance` audit flag across advise leaves.
- Output honesty: transparency labeling, field/regime consistency, positioning coverage &
  confidence, and honest "what to play" output — thin/absent signal is always labeled.
- Regime-aware advisory: windowing core, CLI surface with thin-regime degrade, and adaptive
  per-cell windowing.

### Deck generation & gap discovery
- Consensus baseline generation, field-tuning, per-card win-rate (overall + per-card×matchup),
  maindeck-aware sideboard plans, and portable decklist export (Moxfield-import + multi-target).
- Gap discovery: card-adjacency model, archetype-gap finder (`report gaps`), and discovery tuning.
- New-set ingestion & speculation (`report speculate`, always labeled `PRE-DATA FORECAST`),
  curated price source, and collection-aware recommendations.

### Personal collection
- Personal inventory (binder) and named, versioned decks; `--my-deck` integration into the
  decklist-consuming leaves; printing/condition-aware allocation.

### Visualization
- `viz` platform: theme, render layer, validation, per-deck dashboard, and Vega-Lite chart
  builders replacing matplotlib.

### Fixes (cross-model peer review + correctness)
- Ingestion/archetype-spine: rules SHA pinning, `validate_deck` enforcement, matcher contract
  fidelity, bye/null-Player2 handling, trailing-comma-tolerant rule loading, multi-face front-face
  card indexing, full-timestamp trend dates.
- Analytics: cardinality-safe rounds join, mirror inclusion, top-cut denominators, metashare
  coverage + blend fixes.
- Advisory: positioning P(best) bias under thin matchup data, sideboard field-staple surfacing +
  real-data quality, tuner core-card protection, what-to-play threat-signal calibration.

### Tooling
- 12 documented code patterns; hermetic CLI tests (every CLI test pins `--db` to a temp DB); CI
  lint + dependency declaration; path/SSRF hardening on ingestion.

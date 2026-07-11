## v0.2.0 (2026-07-04)

The sideboard-intelligence release: `advise sideboard` gains a decomposed, explainable,
field-weighted scoring model, validated against real winning boards.

### Features
- **Decomposed impact scoring** — element weights are `field_share × swing × impact` where impact =
  centrality × symmetry × castability (multiplicative hard gates; draw-probability lives in the
  per-copy taper). New `advisory/impact.py` with per-card explainable breakdowns in CLI output.
- **Archetype linchpin model** — `advisory/linchpins.py`: hybrid derived + curated registry of
  per-archetype critical cards (`data/linchpins/legacy.json`), feeding the centrality factor.
- **Board backtest** — new `advise backtest`: compares recommended boards against top-finisher
  sideboards (overlap / scorer-only / winners-only), field/window-scopable via `--field-scope`.
  Reports resemblance with confidence tiers — never a pass/fail verdict.
- **Flexibility valuation** — submodular breadth aggregation consolidated into one canonical
  marginal-gain form; CVaR option-value bonus over the Dirichlet field (risk-appetite dial α);
  `_hate` self-protection made coverable; maindeck-aware coverage discount; slot-ROI/punt table.
- **Vulnerability vocabulary** — `graveyard-reliant` split into `graveyard-recursion`/`graveyard-fuel`;
  new `plays-<color>`, `noncreature-reliant`, `colorless-reliant` axes; hoser catalog grown to 37
  entries (Force of Negation, Spell Pierce, Mystical Dispute added; Hydroblast/Pyroblast re-tagged).
- **Config comparator + slot test** — `advise compare` (two-config / transform EV comparison, MC
  P(A>B), break-even) and `report cards --contrast` (matchup-conditioned WITH/WITHOUT slot test).
- **Sideboard core-and-hedge solver** — concave per-copy value, natural-budget τ stop, dedicated
  core vs flexible insurance hedge allocation, `--smart` output contract.

### Fixes
- Null Rod catalog color corrected to colorless; Consign to Memory oracle-grounded re-attribution;
  decklist parser comment handling; ingestion resilience follow-ups.

### Documentation
- Foundation docs + README rolled forward to the decomposed-scorer reality; new attested brief
  `docs/briefs/scorer-flexibility-valuation.md`; three new pattern skills
  (hybrid-derived-curated-registry, divergence-as-diagnostic-surface, closed-vocabulary-fail-fast-token).

### Internal
- Quality gates: 29 findings (tests/cruft/docs/patterns) drained pre-tag — comparator honesty-banner
  coverage, τ×option-value composition pinned, 5 vacuous tests rewritten, test-file cruft removed,
  helper builders consolidated into conftest. Suite: 2202 → **2578 passing** (+1 documented xfail).

# Changelog

## Unreleased

### epic-subarchetype-resolution + archetype-sweep backtest (PRs #35-#40, 2026-07)
- `discover run|list|apply|promote` — data-driven subarchetype discovery within a parent archetype
  (flex-band TF-IDF → TruncatedSVD/UMAP → HDBSCAN, two-gate validation, auto-naming, staged
  candidates; promotion into the curated variant registry). Deps: scikit-learn (core),
  umap-learn (optional `discovery` extra).
- `report matchups --split-variant <ARCH>` — opt-in camp-level matchup cells reusing the
  existing shrinkage + tier honesty gates; unlabeled residue always visible.
- `report cards --conditioned [--variant]` — archetype/camp-scoped card win-rate beside the
  marginal, with honest-degrade sign-conflict warnings; `report subgroup --winrates` adds
  per-camp W/L + win% + tier.
- `discover apply` — staged candidate splits consumable by analytics as labeled-speculative
  before promotion (cluster membership persisted in staged records; staged-provenance echo in
  `--split-variant` reports).
- `advise sweep` — batch backtest over every eligible archetype with ranked, root-cause-clustered
  scorer-vs-winners divergence mining (+ `--json` copy-count histograms); en route: ILP
  tie-break nondeterminism root-caused and fixed (sorted constraint construction).
- Fixed: discover auto-naming could assign the same name to two distinct camps (real case: two
  Sphere-led prison Lands builds) — names now disambiguate with the next signature card.
- Fixed: variant resolution silently NULLed every color-prefixed archetype's variants
  (labeler keyed on base_archetype; registry parents are display labels).

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

## Unreleased

### Features
- **Colour-split archetype layer** — a curated, tracked registry
  (`src/legacy_engine/data/color_splits/legacy.json`) carves one parent archetype label into
  mutually exclusive children keyed on the colours its **mainboard nonland** cards actually cast.
  It fills the gap between the archetype rule DSL (card names only) and MTGOFormatData's
  `IncludeColorInName` (full guild identity — a fixed core with a two-card splash fragments into
  a dozen labels). `label` applies it before variant resolution, so `decks.variant` rules and
  every downstream surface key on the label consumers see; `advise`'s pasted-decklist classifier
  applies it too, so a pasted list lands on the same label the corpus carries. Loader fails fast
  on an unknown colour, a duplicate parent, an unreachable bucket, or a one-bucket "split";
  the resolver fails fast when two buckets match the same deck. No registry, or a parent it
  doesn't carry → the classifier's label passes through untouched.
- **Energy splits into Boros Energy and Mardu Energy** — the first colour split. Over the field
  window opening at the 2026-06-29 Candelabra ban: 97 Boros / 47 Mardu of 144 Energy decks
  (67% / 33%). Black commitment is bimodal rather than a splash — 45 of the 47 Mardu lists play
  8+ black mainboard copies (Thoughtseize, Cabal Therapy, Orcish Bowmasters) — so the two
  branches are separate decks and now hold separate archetype rows everywhere, including in
  every *opponent's* ledger. Strategic-plan assignments and the `sac-001` white-creature
  superarchetype cluster carry both branches; the stale 3-camp `Energy` discovery split is
  retired.

### Changes
- **Archetype dropdowns are two independent disclosures** — on the agency ranking page, the
  strategic-plan block and the exact archetype ledger each open and close on their own, with a
  measured-cell count in each header, so neither has to be scrolled past to reach the other.
  Open/closed state is remembered across row expansions. Camp rows, which carry no plan block,
  keep their single always-open section.

## v0.4.0 (2026-08-05)

The stable-era release: every statistic windows to each archetype's (and camp's) own detected
stable era — the largest stretch of still-solid data — with the triggering disturbance named.

### Features
- **Per-entity stable-era detection** — new `analytics/eras/` package: density-adaptive entity
  series, signal ensemble (presence cliffs/ramps, composition change-points via ruptures, share
  shifts, win-rate corroboration), selection-corrected permutation p-values, fleet-wide
  Benjamini–Hochberg FDR, 30-deck era floors, camp inheritance. Calibrated against frozen
  real-corpus ground truths (the Flow State one-week adoption step; the Candelabra/Tron cliff).
- **Era ledger + CLI** — `eras run|list|explain|confirm`: rebuildable `entity_eras` store,
  ban/release/unattributed attribution (corpus-first-seen release fallback), Beta-Binomial BOCPD
  drift alarm, and the confirm loop that appends to the curated `BAN_EVENTS` JSON and heals the
  regime table.
- **Era-aware windows are the default** — the adaptive matchup matrix sources each cell over
  `[max(stable_since(a), stable_since(b)), now)` (ban-only fallback, loudly labeled); the global
  field era is detection-derived; consensus/card-frequency surfaces window at the entity's own
  era (camp-aware); `discover run` pools within the parent's stable era (`--all-pool` escape) and
  Gate C flags camps that are list generations.
- **Hierarchical + cross-era cell shrinkage** — cells shrink toward informative priors (parent →
  shrunk marginal; camp → leave-camp-out parent cell; thin post-boundary cells → their own
  pre-disturbance value, labeled) instead of flat 0.5; `prior_source` carried and rendered.
- **Superarchetype layer + serving lifecycle** — strategy clusters complete the taxonomy as
  superarchetype → parent archetype → camp. `superarchetype run` previews a derived candidate;
  `run --promote`, after operator review, explicitly replaces the serving JSON registry and its
  DuckDB cache. `list` and `explain` inspect serving memberships and provenance. The layer is
  internal matrix/statistical-borrowing context only — it emits no page-visible payload.
- **Best Deck / Best Call agency ranking page** — `scripts/refresh_best_call_ranking.py` generates
  the git-ignored `decks/best-deck-best-call-ranking.html`. Agency % = min(adjusted field WR,
  worst measured matchup); grounded/ungrounded honesty strata never intermix under sorting;
  ungrounded rows are explicit upper bounds. Adds a curated five-plan **strategic-plan view**
  (`Disrupt + Pressure`, `Go Off`, `Go Over`, `Go Wide`, `Lock + Outlast`) aggregated from
  decisive match records, and a direct five-cell plan block heading every archetype dropdown.
- **One-pass multi-split camp matrix** — the camp sweep builds one `build_multi_split_adaptive`
  plus one `build_multi_split_matrix` per distinct ban-scoped fallback date, serving all staged
  parents at once: field-for-field identical to the retired per-parent path (parity-tested at
  engine and script level) and ~21x cheaper (326s → 15s on the live corpus).
- **Cross-camp P(best)** — one shared-field `rank_decks` Monte Carlo (fixed seed) scores every
  camp and unsplit field archetype against the same sampled parent-level Dirichlet field, so
  values are comparable across camps of different parents. Candidacy is gated at the display
  coverage threshold so zero-coverage candidates cannot absorb the argmax as imputation noise.
- **Incremental camp assignment** — `discover apply` assigns decks ingested after a split was
  staged, using the staged candidate's frozen flex vocabulary and camp centroids, instead of
  leaving them unlabeled.
- **BAN_EVENTS as curated JSON** — migrated from code to package-shipped
  `data/banlist/events.json` (module API unchanged), appendable via `eras confirm`.

### Fixes
- **Refresh no longer wipes archetype labels** — `refresh all` performs a keyed reload that
  preserves `decks.archetype` and `decks.variant` for unchanged decks. Previously a no-op refresh
  could silently reset the entire label layer, requiring a full relabel plus per-parent re-apply.
- **Sideboard land resolution fails loudly** — a `cards` lookup failure now yields a named
  `land-resolution-failed` degraded plan with no swaps, instead of silently resurrecting the
  land-cut defect at `log.debug`.
- **Era drift alarm hygiene** — the alarm uses weekly recency with an 8-week recent-share gate,
  so a cliff hidden in an incomplete trailing bucket is no longer missed.
- **Aggregation provenance matches the typed verdict** — a heterogeneity-refused cell no longer
  claims a concentration label was *served*; a served not-computable cell now carries its
  heterogeneity verdict in provenance.

### Internal
- Test suite 2,578 → 3,540 passing. Review-test integrity pass replaced a golden's self-compared
  floats with independent expected values, exercised the previously-uncovered family-first
  imputation branch, and timestamped real-corpus spot checks so counts read as historical.

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

## v0.3.0 (2026-07-11)

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

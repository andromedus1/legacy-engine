---
name: architecture-legacy-engine
description: Read for how legacy-engine is built — module map, file responsibilities, data flow, the core data models, storage decision, conventions, dependencies, and the built-vs-deferred split. The detailed architecture grounded in all four research streams.
type: architecture
kind: planning
updated: 2026-09-05
summary: |
  Detailed architecture for legacy-engine, a Magic: The Gathering Legacy analytics platform (sibling to
  edh-engine). Python 3.11+ Click CLI mirroring edh-engine's stack, plus scipy/numpy/statsmodels/pulp
  for advisory and DuckDB as an embedded analytical store (the one justified divergence, driven by the
  matchup-matrix rounds-join workload). Full arc: ingestion/ (Scryfall + prices + fbettega cache + vendored
  MTGOFormatData rules + ban-list + releases) → archetype/ (ported MTGOArchetypeParser matcher + variant
  tagging) → analytics/ (meta-share, matchup matrix, per-card value, subgroup/venue/speculation,
  players/{identity,strength,history}) + advisory/ (positioning, maindeck-aware sideboard, what-to-play,
  collection-aware acquire, refresh, primer) + generation/ (consensus, export, field-tuning, gap-discovery,
  card_distribution) → models/ (incl. collection, variant) → data/. collection/ is the personal-layer peer
  of ingestion/. goldfish/ is the deferred pillar; only goldfish-validated candidate-validation remains
  deferred behind it. The generated Deck Rankings landing page adds a separate posterior field-performance
  and matchup-floor projection beside the mature advisory estimators. A separate retrospective
  served-model evaluator freezes that shared projection before later outcomes are read; it has no
  publication path. Local ops runs the decision refresh and detection-only format monitor under one
  artifact lock; human `eras confirm` remains the only B&R acceptance authority.
decisions:
  - "Mirror edh-engine's stack (Python 3.11+, Click CLI, Pydantic, httpx, local files) + add scipy/numpy/statsmodels (advisory stats), pulp/CBC (sideboard ILP), and vl-convert-python (Vega-Lite viz render)."
  - "STORAGE: raw mirrored JSON is the reproducible source of truth (data/cache/, data/scryfall/, data/rules/, data/banlist/, data/collection/); a rebuildable embedded DuckDB (data/legacy.duckdb) is the analytical layer for meta-share + matchup-matrix + prices + collection joins. The one justified divergence from edh-engine's pure-files approach, driven by the rounds-join matchup workload."
  - "archetype/ is the novel subsystem: vendor MTGOFormatData rules-as-JSON pinned to a SHA (data/rules/ + manifest), reimplement only the ~210-line MTGOArchetypeParser Detect matcher in Python, golden-test to >=99% label agreement against the archived C# parser's published labels (fallback: hand-curated fixtures). variants.py adds sub-archetype tagging (e.g. Bauble) driven by a card-presence registry."
  - "Scryfall ADR RESOLVED: EXTEND edh-engine's ingestion/scryfall.py (every needed function verified to exist), index the WHOLE oracle pool (~30k+ IDs, not a fixed subset); do NOT adopt Scrython (bulk index makes the API path rare) or mtg_parser (fbettega JSON is the decklist source, already name-normalized)."
  - "Deck color = lands.produced_mana ∩ nonlands.colors (NOT color_identity); legality validated against a version-stamped BanListSnapshot blacklist (NOT Scryfall's lagging legacy flag)."
  - "Matchup matrix: computed ourselves from Rounds; Wilson CIs + Beta-Binomial shrinkage; confidence tiers (speculative n<30 hidden / evolving 30-99 / established >=100); matchup-n kept separate from metashare-n; meta-% computed 3 labeled ways with online/paper split."
  - "Ingestion mirror-and-decouple: consume the fbettega cache JSON (not mtgo.com), behind an ingestion/ port so a replacement source swaps in without touching analytics/advisory."
  - "MVP + advisory-honesty-transparency = ingestion + archetype + analytics (incl. subgroup/venue/speculation/players) + advisory (incl. collection/acquire/refresh/primer) + generation (consensus/export/field-tuning/gap-discovery mode 3 + card_distribution); goldfish/ (port edh-engine's mana solver + straight-London mulligan) is the deferred pillar; only goldfish-validated candidate-validation remains deferred behind it."
  - "VISUALIZATION: viz/ is a local Vega-Lite presentation layer (interactive HTML via vega-embed + static PNG via vl-convert, strip-and-inject theming, 12-col tile/layout); headline deliverable is a reusable per-deck dashboard composing meta-share/matchups/trends/positioning/consensus. No server, no cloud (mirrors the knowledge-graph/board HTML precedent)."
  - "PRICES: ingestion/prices.py + seed prices + ingestion/releases.py serve the acquisition and new-card surface; PriceQuote.all_null is the honest-null signal (never a silent 0)."
  - "PLAYER SUBSYSTEM: analytics/players/{identity,strength,history,diagnostic,effect}.py classifies player handles via alias resolution, gates strength scoring on confidence tier, tracks per-regime archetype history, and runs a production-neutral future-only player-effect sensitivity. Diagnostic identity is provenance-local unless a dated curated snapshot exists; aggregate-only output can reach candidate-for-promotion-study but never alters the headline automatically."
  - "HONEST-DEGRADE POLICY: thin/absent signal → labeled banner or degraded flag + named reason + suppressed magnitude. No silent zeros. Applies in window.py (thin-regime banner), primer/sideboard (degraded=True note), the sideboard recommender (returns fewer than 15 with commit/insurance labels + a marginal-coverage curve rather than padding to a forced 15), speculation (PRE-DATA FORECAST label), prices (all_null flag), venue divergence."
  - "SUPERARCHETYPES (built; internal context): analytics/superarchetype/ adds the third taxonomy level above parent archetype. An offline `superarchetype run` preview clusters archetypes on staple-stripped maindeck core sets (Jaccard + average-linkage agglomerative, AU multiscale-bootstrap cut over resampled card features; definers >=30 decks/>=8 core cards, the tail assigned by mean Jaccard dissimilarity to cluster definers) and explicit `--promote` persists a reviewed derived registry merged under a package-shipped curated override registry. Clustering reads deck_cards ONLY — never rounds — so the cut can never be tuned against matchup coverage. matchup.py coarsens the opponent axis and adds the random-effects shrinkage rung; the resulting n_eff feeds the existing tier/display gate. Deck Rankings keeps composition-derived family evidence internal and exposes curated strategic plans plus exact matchup ledgers."
  - "DECK RANKINGS PROJECTION: advisory/deck_ranking.py consumes typed matchup measurements and normalized field shares to compute conditional Beta posterior cells, full-field performance, the non-mirror floor, seeded intervals, coverage, and Pareto status. advisory/recent_field.py supplies the provisional 28-day published-list field. The atomic publisher then attaches successive-snapshot change explanations and parent/build decision-unit disclosures; both are excluded from the ranking authority payload."
  - "SERVED DECK RANKINGS EVALUATION: scripts/evaluate_deck_rankings.py --served-model has freeze, development (default), and confirmation phases. All six predictions are sealed before development scoring; confirmation validates and reuses their bound configuration and seals --selected-method from development before future outcomes open. Retrospective production parent rules and the color-split registry are hash-pinned, including Boros/Mardu Energy, while camps remain disabled. Fixed scales 1/.5/2 and opponent-plan-prior-v1 retain the chosen cell view, match digest, and windows. Development selected scale 2; confirmation slightly favored scale 1, which remains in production. Dated score disclosure is read-only, with no apply or publication path."
  - "STABLE ERAS: analytics/eras/ detects per-entity boundaries and retains stable_since as the current/fallback projection. The built recurrent validation surface freezes cutoff-safe recurrent origins from a hash-bound parent benchmark plan, validates typed refit stages and full forecast grids, evaluates predictive + decision evidence on a shared future ledger, aggregates exact promotion assessments, and can emit only inert operator-review proposals. The intended recurrent-era serving extension still separates outcome-free candidate discovery from independent equivalence certification, persists versioned EraCertificates over disjoint half-open intervals, and lets matchup consumption intersect subject and opponent interval sets before estimation. Confirmed affectedness is a semantic veto; expanded evidence remains distinct from current-only evidence and requires future-only validation before promotion."
  - "FORMAT MONITOR: the scheduled refresh consumes current Scryfall gzipped JSONL, diffs Legacy legalities, strictly parses WotC Legacy attribution, and combines the existing set scan with actual new-card ingest evidence. Machine state is atomic under data/ops; signals distinguish clear/pending/not_due/unavailable; acknowledgement suppresses unchanged evidence only; `eras confirm` remains the sole supported ban-registration authority."
---

# Architecture: legacy-engine

*Last updated: 2026-09-05* (rolled forward to present implementation and intended recurrent-era contract)

> How the system is built. For *what* and *why*, see [VISION.md](VISION.md) and [SPEC.md](SPEC.md).
> For decision heuristics, see [PRINCIPLES.md](PRINCIPLES.md). For what to build when, the roadmap/epics
> come next (`/epicize`).

## System Overview

A Python 3.11+ Legacy-format analytics platform with a Click CLI and a local data layer. It **mirrors
edh-engine's architecture** (three data layers → analytical pillars, deck-as-data, Scryfall card
dimension, confidence metadata) with two deliberate divergences justified by the domain: an explicit
**`archetype/` classifier** (Legacy decks have no commander key) and an embedded **DuckDB** analytical
store (the matchup matrix is a rounds-join query workload). The MVP builds the
observed → label → analytics → advisory arc.

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                  CLI  (cli.py)                                   │
│  seed (cards|cache|rules|banlist|prices) · refresh (all|cards)                   │
│  · ops (scheduled-refresh|status|scheduler install|inspect|run-now|uninstall)     │
│  · label · report (meta|matchups|tiers|trends|cards|gaps|subgroup|variants|      │
│    new-cards|speculate|prices|affectedness)                                       │
│  · advise (positioning|sideboard|whattoplay|field|report|refresh|acquire|compare| │
│    backtest|sweep|benchmark|recurrent-validation)                                  │
│  · identify (suggest|strong|track)                                               │
│  · generate (consensus|tune|doctor) · export (deck) · viz (deck|meta|matchups|   │
│    trends|tiers)  [later: goldfish]                                               │
│  · collection (import|show|status|rebuild) · deck (save|load|list|show|          │
│    versions|buildable) · discover (run|list|apply|promote)                        │
│                                                                                   │
│  Cross-cutting flags: --since/--until/--regime/--all-time (ban-regime windowing)  │
│  --my-deck (load a saved UserDeck by name) · report meta: --venues/--by-variant  │
│  generate consensus: --variant/--players/--strong                                 │
│  --provenance online|paper (all advise leaves + report matchups/meta)             │
│  variant overlays (opt-in): report matchups --split-variant · report cards        │
│    --conditioned [--variant] · report subgroup --winrates                          │
│  advise positioning: --list-granular (opt-in S_granular deck-as-cards overlay)    │
└───┬──────────┬───────────┬────────────┬───────────────┬─────────────────────────┘
    │          │           │            │               │
┌───▼─────┐ ┌─▼────────┐ ┌▼──────────┐ ┌▼────────────┐ ┌▼──────────────┐
│ingestion/│ │archetype/ │ │analytics/ │ │advisory/    │ │generation/    │
│scryfall  │ │rules      │ │metashare  │ │positioning  │ │consensus      │
│cache     │ │matcher    │ │matchup    │ │sideboard    │ │export·tuning  │
│banlist   │ │colors     │ │trends     │ │whattoplay   │ │discovery      │
│rules_    │ │labeler    │ │affectedness│ │report       │ │card_distribut-│
│ vendor   │ │golden_test│ │card_value  │ │gaps         │ │ ion           │
│store     │ │variants   │ │match_result│ │window       │ │(goldfish/     │
│prices    │ │           │ │subgroup    │ │field        │ │ deferred)     │
│releases  │ │           │ │venue       │ │collection   │ │               │
│          │ │           │ │speculation │ │acquire      │ │               │
│          │ │           │ │players/    │ │primer       │ │               │
│          │ │           │ │ identity   │ │refresh      │ │               │
│          │ │           │ │ strength   │ │impact       │ │               │
│          │ │           │ │ history    │ │linchpins    │ │               │
│          │ │           │ │            │ │backtest     │ │               │
└───┬─────┘ └────┬──────┘ └─────┬─────┘ └──────┬──────┘ └───────────────┘
    │            │              │              │
┌───▼─────────────────────────────────────────────────────────────────────────────┐
│ collection/  (user personal layer — peer of ingestion/)                           │
│  persist · store · inventory · decks · allocation                                 │
└───┬─────────────────────────────────────────────────────────────────────────────┘
    │
┌───▼──────────────────────────────────────────────────────────────────────────────┐
│                                  models/                                          │
│  Card · Decklist · Deck · TournamentResult · Round · Standing · Archetype ·       │
│  ArchetypeRule · Condition · Variant · MatchupCell · BanListSnapshot ·            │
│  ConfidenceMetadata · Inventory · InventoryEntry · UserDeck · DeckVersion ·       │
│  DeckCardRef                                                                      │
│  (advisory/analytics result records are dataclasses in their own modules)         │
└──────────────────────────────────┬───────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────────┐
│   data/   (raw = source of truth)              data/legacy.duckdb (derived)       │
│   cache/    (mirrored fbettega JSON)            tournaments · decks · deck_cards  │
│   scryfall/ (oracle bulk + default_cards)       rounds · standings · labels       │
│   rules/    (vendored MTGOFormatData @SHA)       cards · card_prices               │
│   banlist/  (dated B&R snapshots)               matchups (materialized)           │
│                                                  entity_eras (rebuildable)         │
│   collection/ (user-authored SSOT)              inventory_entries · user_decks    │
│     inventory.json                               deck_versions · deck_version_    │
│     decks/<id>.json (per deck)                    cards                           │
│   players/  (curated alias map)                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Layers → Analytical Pillars (mirrors edh-engine)
| Layer | What | MVP pillar | Later |
|---|---|---|---|
| **Observed** | fbettega tournament cache, Scryfall cards, ban-list, archetype labels | Meta & Performance | feeds advisory |
| **Synthetic** | goldfish simulation (speed, consistency) | Deck Mechanics *(deferred)* | meta-speed metric |
| **Generated** | positioning, maindeck-aware sideboard packages, consensus + field-tuned deck candidates, gap-discovery (mode 3: archetype-gaps + adjacent-card discovery) | Meta Attack/Advisory + Deck Generation | goldfish-validated candidate-validation deferred |

---

## Module Map

### `ingestion/` — data acquisition (no runtime network calls; all pre-fetched + mirrored)
| File | Responsibility | External dep | Brief |
|---|---|---|---|
| `scryfall.py` | **Extended from edh-engine** (ADR: extend, don't fork). Streams the current `jsonl_download_uri` gzipped JSONL contract atomically (legacy JSON arrays remain readable), indexes the WHOLE oracle pool (~30k+ IDs), and supports `/cards/collection` fallback plus printing prices. | api.scryfall.com | scryfall-card-contract |
| `cache.py` | Mirror + parse the fbettega `MTG_decklistcache`. Parse the PascalCase `CacheItem {Tournament, Decks[], Rounds[], Standings[]}`; cards as `{Count, CardName}`; derive online/paper provenance from source-dir + Uri host; treat empty Rounds/Standings (Leagues) as normal. Incremental via `git pull` + day-folder diff. | github (fbettega) | fbettega-cache-schema |
| `rules_vendor.py` | Vendor MTGOFormatData rules-as-JSON via git subtree into `data/rules/`, pinned to a commit SHA in `RULES_MANIFEST.json`. `legacy refresh rules` pulls upstream, diffs `Formats/Legacy/`, surfaces new archetypes/condition-types. | github (Badaro) | mtgoformatdata-rule-schema, csharp-python-port-strategy |
| `banlist.py` | Maintain dated `BanListSnapshot`s (banned names + banned_date + ban_reason + category predicates) from WotC B&R announcements. Blacklist validation. `BAN_EVENTS` loads from package-shipped curated JSON (`data/banlist/events.json`); `eras confirm` appends a confirmed event — the drift-alarm → human-confirm → regime-heal loop. | (hand-curated + WotC) | legacy-foundations |
| `ban_monitor.py` | Pure strict parser for the WotC Legacy section, effective date, actions/no-change, next-announcement cursor, and bounded date-slug candidates. Ambiguous or drifted pages fail unavailable; this adapter never writes accepted B&R truth. | magic.wizards.com | data-autonomy-upstream |
| `prices.py` | Per-printing price layer: `price_quote(con, name)` → `PriceQuote` (cheapest paper USD across all printings). `PriceQuote.all_null=True` is the honest-null signal — never a silent 0 when every printing lacks a paper price. `deck_cost` accumulates totals and exposes an explicit `unpriced` list. | duckdb | — |
| `releases.py` | Scryfall `/sets` scan: `fetch_sets` + `upcoming_and_recent` classify sets as upcoming or recently-released in a configurable horizon window. Used by `refresh cards` to decide whether to force a bulk re-pull (release-aware incremental). | api.scryfall.com | — |
| `card_coverage.py` | Reconciles derived tournament card names through an explicit authority ladder: evidence-bearing exact provider exceptions, exact canonical names, provider-scoped serialization rules, then unique current Scryfall localized aliases. Provider rules require complete singular provenance and an existing exact canonical target; missing provenance, ambiguous aliases, truncated tokens, unsupported prefixes/providers, and manual candidates stay named and unresolved. `refresh card-coverage --benchmark-protocol` validates the frozen schedule before reconciliation, groups every residual by its first strictly later training cutoff, and fails after printing structured provider/event evidence for the complete audit when any planned cutoff remains open. | duckdb + package registry | best-deck-decision-trust |
| `store.py` | Normalize parsed raw JSON → Pydantic models → load into DuckDB (`data/legacy.duckdb`). Owns `rebuild` (drop+recreate cards), `rebuild_prices` (drop+recreate card_prices), and `load_cards_diff` (non-destructive incremental). DuckDB is a **rebuildable derived cache**; raw JSON is the source of truth. | duckdb | ingestion-ops-and-metashare |

### `ops/` — local decision-data operations

| File | Responsibility |
|---|---|
| `status.py` | Typed canonical and immutable per-attempt JSON status, atomic same-directory replacement, 36-hour freshness classification, and shared `//` audit-line projection. Missing/invalid/failed/degraded/running/stale remain distinct. |
| `scheduled_refresh.py` | Artifact-derived non-blocking `fcntl` execution lock shared by scheduled and manual entrypoints around `workflows.decision_refresh.run_decision_refresh` and the format monitor; maps both results to attributable status, best-effort terminalizes SIGTERM, and hashes only a ranking written by that attempt. A monitor outage degrades but does not discard a successful ranking. |
| `launchd.py` | Generates the 07:30 local user LaunchAgent with `plistlib` and controls it through an injected `launchctl` port. Lifecycle mutations hold the refresh lock, refuse active-run bootout, and restore/reload the previous configuration after any post-bootout failure; uninstall preserves the plist on failed bootout. |
| `format_monitor.py` | Typed atomic last-good legality/candidate state, stable evidence identities and acknowledgements, two-signal WotC/Scryfall correlation, release-window evidence, honest signal states, and `//` projection. Operational evidence is separate from `data/banlist/events.json`; no function imports or calls `append_ban_event`. |

The LaunchAgent uses absolute repository/virtualenv/log paths, `WorkingDirectory`, and
`StartCalendarInterval`; it omits `RunAtLoad`, `KeepAlive`, and `StartInterval`. Repository tests
inject both paths and process results, so they never invoke live `launchctl`, provider endpoints, or
touch `~/Library/LaunchAgents`. The same locked job runs detection-only B&R/release monitoring and
surfaces its state through `ops status`; the hot spare, vendor prices, and non-Legacy deployments
remain separate scopes.

### `collection/` — the user's personal layer (local single-user; schema cloud-ready)

The user's own card inventory and decks as first-class persistent entities. Raw JSON under
`data/collection/` is the source of truth (user-authored, precious, git-/hand-editable);
DuckDB tables are the rebuildable derived cache for allocation/buildability joins — same SSOT
split as `ingestion/`. Every owned row carries an `owner` key (defaulted `LOCAL_OWNER="local"`)
and every persistent entity a stable UUID, so a future hosted/multi-user surface migrates
without a schema rewrite. CLI-first; no web UI (deferred to its own research).

| File | Responsibility |
|---|---|
| `persist.py` | JSON SSOT read/write for `Inventory` + `UserDeck` docs under `data/collection/` |
| `store.py` | DuckDB DDL + load/fetch/rebuild for `inventory_entries`, `user_decks`, `deck_versions`, `deck_version_cards` (owns only these 4 tables) |
| `inventory.py` | Inventory domain ops (text/CSV import, merge/replace, owner-scoped counts) |
| `decks.py` | UserDeck ops: save (new deck / append version), load, list, show, version log |
| `allocation.py` | Pure derived views: buildability, free-binder, contention (objective-search-split) |

### `archetype/` — the novel subsystem (no commander key → rule-based classification)
| File | Responsibility | Brief |
|---|---|---|
| `rules.py` | Load vendored rule JSON → typed `ArchetypeRule`/`Condition`/`Variant`/`Fallback`. **Fail-fast** on unknown condition `Type` (mirrors edh-engine's fail-fast-on-unknown-role). 12 condition types. | mtgoformatdata-rule-schema |
| `colors.py` | Compute deck color = `lands.produced_mana (−C) ∩ nonlands.colors` per WUBRG (NOT color_identity). Guild/shard naming table extracted from `Archetype.cs:43-112`. | scryfall-card-contract, archetype-matching-algorithm |
| `matcher.py` | The ported `ArchetypeAnalyzer.Detect`: AND-test every archetype's conditions, collect all matches (emit `Conflict(...)` when >1, `PreferSimpler` optional), nest variants, fallback-by-card-overlap (≥10% floor) else `Unknown`. Pure function `classify(decklist, ruleset, card_colors) -> ArchetypeResult`. ~210-line core + 12 condition predicates. | archetype-matching-algorithm |
| `labeler.py` | Orchestrate: decklist → resolve names (Card index) → compute colors → `classify` → persist `archetype_labels`. | parent |
| `golden_test.py` | Fidelity harness: replay the archived C# parser's published labels over a frozen fbettega corpus at the pinned rules SHA; assert ≥99% per-deck agreement (CI gate). Fallback: hand-curated label fixtures. | csharp-python-port-strategy |
| `variants.py` | Sub-archetype variant tagging: given a card-presence registry (e.g. "Bauble" → requires card X), classifies each decklist's variant tag. Drives `generate consensus --variant` and `report meta --by-variant`. The curated registry is the promotion target for the **data-driven discovery engine** (below). | — |
| `analytics/discovery.py` (pure core) + `archetype/discovered.py` (staging/promotion/apply) | Data-driven discovery front-end to `variants.py`: within a single parent archetype, builds a flex-band deck-card matrix (drop ubiquitous core + rare tail), reduces (TruncatedSVD/UMAP), clusters with HDBSCAN (self-determines k, labels outlier brews as noise), gates each split through a statistical gate (resampling stability / prediction strength) **and** the engine's domain gate (both camps ≥ evolving tier + signature-card divergence, reusing `subgroup.py`), auto-names from signature cards, applies **Gate C** (temporal-mixing: camps whose median dates separate ≥120 days are flagged "camps may be list generations" — flagged, never failed; per-camp median date + %current surfaced and persisted; pools default to the parent's stable era, `--all-pool` escape), and stages survivors as **candidate** splits (`archetype/discovered.py`, as-built — the staging/promotion/apply surface lives beside `variants.py` even though the pure clustering core is in `analytics/`). `discover (run\|list\|apply\|promote)` CLI: `run` reports candidates + writes a staging registry read as labeled-speculative; `list` inspects it; `apply` labels a staged (still-unpromoted) split's camps directly onto `decks.variant` so analytics can read them before a human confirms — status stays `candidate`, curated registry untouched; `promote` moves a confirmed split into curated `data/variants/legacy.json`. Discovery/apply never auto-rewrite the curated taxonomy. Offline labeling pass (sibling to `label`). Deps: scikit-learn + umap-learn. | subarchetype-discovery |

### `analytics/` — Meta & Performance
| File | Responsibility | Brief |
|---|---|---|
| `match_results.py` | Shared foundation: join `rounds` → archetype labels via `decks` (normalized player name within a tournament), parse the aggregate match-score string into match-level W/L, accumulate directed `(arch_a, arch_b)→{wins,losses,n}` cells + per-archetype marginal records; normalize names, drop byes/draws, surface unmatched-pairing coverage. Consumed by `metashare` (§3c), `matchup.py`, and `card_value.py`. Also exposes `compute_card_winrates` — per-card `(card, board, opponent)→{wins,losses,n}` + per-card marginal aggregates joining `deck_cards`, reusing the same cardinality-safe CTEs (presence-correlational, NOT causal). | ingestion-ops-and-metashare |
| `card_value.py` | Confidence-rated per-card value over `compute_card_winrates`: two-level empirical-Bayes (matchup cell shrinks toward the card's shrunk marginal, which shrinks toward the global baseline); `CardValue` carries `lift`/`p_shrunk`/`tier`/`n`; `card_values_vs(...)` returns gated values consumed by `advisory/sideboard` (maindeck-aware plans) and `generation/tuning` (swap objective). | advisory-methods |
| `metashare.py` | Meta-% three labeled ways (raw count / top-cut presence / win-rate-weighted via `match_results`), split online/paper/blend; ≥2%-of-field inclusion. SQL over DuckDB. | ingestion-ops-and-metashare |
| `matchup.py` | Build the matchup matrix from `match_results`' directed cells: per-cell `{wins, n, p_raw, p_shrunk(Wilson/Beta), ci, tier}`; mirror fixed 0.5; **matchup-n separate from metashare-n**. Stats primitives (`beta_binomial_shrink_to`, `wilson_or_jeffreys_ci`) are reused by `card_value`. `build_matrix` takes a `since/until` window. `build_adaptive_matrix` currently sources each pairwise cell from the later scalar `stable_since`; the recurrent-era serving contract replaces that selection seam with normalized interval-set intersection for subject and opponent, retaining the scalar path as current-only/no-certificate fallback. Each selected match carries subject/opponent certificate and overlap-component provenance, while current-only, expanded, and added-history estimates remain separate. Cells continue to shrink toward hierarchical priors (parent cell → shrunk subject marginal → 0.5; camp cell → leave-camp-out parent cell′ → marginal′; thin post-era-boundary cells → their own pre-disturbance value), with `prior_mean`/`prior_source` carried per cell. **Opt-in variant dimension** and **multi-split entry points** retain their existing contracts. **Superarchetype rung** remains exploratory and ledger/navigation-only until the future-only decision benchmark passes. | advisory-methods, superarchetype-aggregation |
| `affectedness.py` | Ban-affectedness classifier: `archetype_valid_since` = the latest ban each archetype was materially affected by (ran a banned card in ≥ threshold of its pre-ban decks), data-derived from `BAN_EVENTS` × `card_frequencies` × `regime_windows`. Now the honest-degrade FALLBACK horizon behind `analytics/eras/` (entities never analyzed by `eras run` fall back to ban-only). Lives in `analytics` (no advice) so the matrix builder consumes it without an `analytics → advisory` cycle. | — |
| `advisory/field.py` + `analytics/eras/consume.py` | Credible-window policy boundary: `EraHorizon` takes the later stored/parent era and direct confirmed-ban lower bound, retaining both candidates when a stored era is clamped. `build_transition_field` keeps exact post-ban observed counts beside a capped (500-deck floor) preceding-regime prior with affected archetypes removed and deterministic integer rounding. Effective shares feed ranking only; matchup `PairWindow`s remain independently clamped. | credible-window ranking utility |
| `eras/` (package) | **Per-entity stable-era detection, certification, and ledger.** The built detector retains `series.py`, `bocpd.py`, `detect.py`, `ensemble.py`, attribution, drift alarms, and `stable_since` fallback. The recurrent extension adds an outcome-firewalled segment/fingerprint candidate layer, independent event-level equivalence certification with semantic affectedness/context/support/multiplicity guards, and a rebuildable versioned EraCertificate store over normalized disjoint half-open intervals. `consume.py` becomes the single interval-set eligibility seam: pairwise subject/opponent intersection plus explicit `data_until` and `knowledge_as_of`, with current-only fallback and no outcome access during discovery/certification. | change-point-detection, recurrent-era-intervals |
| `superarchetype/` (package) | **Strategy clusters over archetypes — the third taxonomy level** *(built; page decision authority remains exploratory)*. `cluster.py` — the pure, DB-free clustering core (objective-search-split): per-archetype maindeck **core set** (>=50% inclusion) minus **format staples** (core to >=30% of definers — hard removal; TF-IDF down-weighting demonstrably fuses half the field into one "plays blue" cluster), Jaccard dissimilarity, average-linkage agglomerative via `scipy.cluster.hierarchy`, cut by a pvpick-style root-excluded descent retaining the largest branch clearing a multiscale-bootstrap **AU p > 0.95** (strict) over resampled *card features* (numpy loop; pvclust's criterion ported, not the R package) **AND** a raw bootstrap-probability floor at scale 1.0 (AU is a bias-corrected extrapolation OF that BP, and near-root branches show flat BP ~0.02-0.15 that the fit extrapolates to 0.93-0.97 — the floor is what stops the extrapolation manufacturing a mega-cluster); an unsupported definer becomes a labeled `au-unsupported singleton`, never a forced member. Co-membership stability cross-check (annotates, never gates), definer (>=30 decks AND >=8 core cards) vs assignee (mean Jaccard dissimilarity to a cluster's definers — average linkage's own criterion, since a mean-vector centroid is metric-inconsistent with Jaccard) split. Every threshold is a named module-level calibration constant with a CLI flag. `aggregate.py` — the pure pooling kernel: continuity-corrected logits, DerSimonian-Laird `tau²`, random-effects inverse-variance pooled proportion, `n_eff` from the random-effects variance, `m_eff = 1/HHI` concentration gate, Q/I² heterogeneity gate + direction-spread and min-computability guards, intra-cluster flag, moment-matched Beta prior strength clamped `[5, 30]`. `registry.py` — derived-registry persistence under `DATA_DIR` (written only by explicit operator-reviewed promotion, records the derivation window + churn vs the previous refresh + the id remap) merged under the package-shipped curated overrides at `PACKAGE_DATA_DIR/superarchetypes/legacy.json` (curated wins by key; each override records the derived assignment it replaced). `consume.py` — the `cluster_of` adapter the matrix layer reads; a registry/consumer window mismatch is a loud `//` audit line, never a silent stale taxonomy. Deps: `scipy` + `numpy` only — no new heavyweight dependency, in deliberate contrast to the camp layer's `hdbscan`/`umap-learn`. | superarchetype-aggregation |
| `trends.py` | Meta evolution across ban-list regimes (version-stamped). | legacy-metagame |
| `subgroup.py` | Sub-archetype split: `SubgroupSplit` partitions an archetype's decks by a card-presence signature and computes per-subgroup meta-share, matchup deltas, and card-inclusion divergence. Surfaced via `report subgroup --archetype`. | — |
| `venue.py` | Venue-aware meta-share: `compute_venue_metashare` builds per-provenance (online/paper) reports; `venue_divergence` ranks archetypes by online-vs-paper share spread. Drives `report meta --venues` and `advise report --venues`. | — |
| `speculation.py` | Pre-data speculative forecasting for cards not yet in the tournament corpus: `speculate_card` computes an `intrinsic_score` from `interaction_facts` + card-tags, borrows a role-filtered analogue prior from established cards, and emits a `SpeculativeForecast` always labeled `PRE-DATA FORECAST`. Drives `report speculate` and `report new-cards`. | — |
| `players/identity.py` | Player identity resolution: `load_alias_map` loads `data/players/aliases.json`; `resolve_player` collapses handles to a canonical `player_id`. | — |
| `players/strength.py` | Strength scoring: `compute_player_records` builds per-player `{events, match_wins, match_losses, win_rate_shrunk, tier}` over a window; `strong_player_set` gates on min-events + confidence tier + win-rate. Drives `generate consensus --strong` and `identify strong`. | — |
| `players/history.py` | Per-player archetype history across ban-list regimes: `player_archetype_history` returns `(regime_label, archetype, deck_count)` rows. Drives `identify track`. | — |
| `players/diagnostic.py` | Pure identity-accessibility and pilot-stickiness ledger. Unaliased handles are provenance-local observations; dated curated aliases are the only cross-handle merge. Reports online/paper/all denominators, independent repeat/familiarity eligibility, deterministic event-bootstrap overlap, and privacy-suppressed aggregate cells without taxonomy verdicts or identity output. | advisory-methods |
| `players/effect.py` | Experimental future-only sensitivity: a separate three-estimator registry fits deterministic L2-pooled antisymmetric deck residuals plus frequency-weight-centered repeat-player and player-by-parent familiarity terms around frozen production-CI log odds. Distinct earlier origins bind their full base artifact/grid, outside-universe rows become named exclusions, and outcome-blind forecasts bind benchmark/identity hashes. Evaluation reuses benchmark support, adds declared cold/venue floors, and uses paired event-block log-loss/regret uncertainty; supported harm stops. It remains outside production and can reach only `candidate-for-promotion-study`. | advisory-methods |
| `advisory/recurrent_validation.py` | Future-only recurrent validation contracts and pure scoring logic. Owns the evaluation-only recurrent protocol (`recurrent-evidence-future-v1`), exact binding to the additive parent benchmark plan, typed five-stage refit artifacts, frozen forecast/origin/evaluation/bundle/proposal records, predictive + decision scoring, exact promotion-assessment rules, and inert operator-review proposal construction. It compares current-only / contiguous-era / recurrent-expanded evidence plus additive amplification methods on one common future ledger and deliberately has no apply path. | advisory-methods, recurrent-era-intervals |

### `advisory/` — Meta Attack/Advisory (the differentiator)
| File | Responsibility | Brief |
|---|---|---|
| `field.py` | `FieldDistribution` (the SSOT for "what is the field"): global-from-`metashare` (with Dirichlet counts) + custom user field (normalize/impute/Other); typed `RegimeCurrency` measures the exact current-ban-regime fraction for global dated decks or complete custom counts (`# current_regime_n`, with undated/partial custom aggregates explicitly unavailable). Field composition is windowed independently from matchup cells. Consumed by positioning, sideboard, whattoplay. | advisory-methods |
| `positioning.py` | **Legacy deck-specific positioning estimator.** `score(deck, field) = Σ w_a·winrate(D vs a)`; Bayesian Monte-Carlo (Beta cells + Dirichlet shares) primary, delta-method fast check; custom user field; risk-adjusted lower-posterior-quantile ranking, P(best), and its established grounded/lean/imputation-dominated/inactive/unscorable evidence classifications. The CLI and its window/provenance behavior remain available and are not the definition of the Deck Rankings page. | advisory-methods |
| `deck_ranking.py` | Current descriptive Deck Rankings projection. `rank_matchup_rows` validates typed rows, computes each cell's conditional Beta posterior using its actual `prior_strength`, retains fitted priors for supplied zero-observation cells and weak 50% priors for absent ledger cells, and returns full-field posterior mean performance, the minimum non-mirror posterior floor, seeded draw intervals, direct support, bad-matchup exposure, and Pareto frontier status. No new point-estimate support threshold suppresses an estimate; callers label prior-only rows and exclude them from calls. | advisory-methods |
| `deck_ranking_projection.py` | Shared projection handoff used by publication and retrospective evaluation. It resolves the same era/fallback/explicit-override source once per cell, scales only effective Beta prior strength for fixed sensitivity runs, and can overlay a conditional challenger prior without changing direct wins/n or selected-source identity. Frozen rows retain original/effective prior strength, prior contribution, and the selected view's match-id digest, admitted components/windows, clock, status, and concentration provenance. | advisory-methods |
| `recent_field.py` | `build_recent_field(con, since, until, half_life_days=28, provenance=None)` reads the half-open dated published-list window and returns recency-weighted shares, exact integer observations, weighted/effective counts, Kish ESS, source denominator/composition, camp fractions, and recent-vs-previous movement. Observed counts stay separate from transition prior counts and source completeness is not assumed. | advisory-methods |
| `ranking_changes.py` | Deterministic comparison of successive compatible published Deck Rankings snapshots. It emits at most three observations for field movement, modeled beneficiaries, and changed performance/floor calls. A symmetric identity separates performance movement into field-weight and matchup-estimate contributions; absent required forecasts remain unavailable, and method/scenario/regime/window changes start a new baseline. | advisory-methods |
| `decision_units.py` | Read-only parent-versus-camp diagnostic attached after projection. On one positive-share external-opponent set it separates pure pooling uplift from the parent/build floor gap and retains camp floors, toughest-pair support, and modeled coverage. Date-bounded facts add separate main/side mean-copy slot distances, within-camp radii, card-record coverage, and source-scoped normalized-pilot overlap. Missing cells remain unavailable; no classification or ranking authority changes. | advisory-methods |
| `ranking_benchmark.py` | Future-only validation contracts: a preregistered ten-estimator registry with `production-ci-gated` as primary; the exact fold schedule and as-of B&R ledger live inside the protocol hash; cutoff-safe parent-only snapshots; frozen retrospective parent-rules identity or dated contemporaneous taxonomy replay; hashed frozen predictions plus separate match and classified-deck held-out ledgers; an opt-in, outcome-blind whole-deck card-metadata quarantine ledger with raw/retained denominators, source/event evidence, hashes, and hard ceilings; explicit support/censoring and player-sensitivity boundaries; proper scores (log loss, Brier, calibration) and decision endpoints (rank tau, top-three, field-weighted structural-mirror regret with stable event-block oracle). External comparators validate parent taxonomy and expose eligible/common coverage. Evaluation is read-only and never tunes production. | advisory-methods |
| `workflows/ranking_benchmark.py` | Filesystem/DuckDB benchmark adapters: build raw pre-cutoff snapshots, plan and apply the same outcome-blind card-metadata ledger before taxonomy, recompute origin predictions, reclassify later decks under the frozen taxonomy identity, orient outcomes, emit the independent field-mass ledger, and compose immutable fold evaluation. Whole-date non-overlapping 28-day folds consume the frozen schedule, reset/truncate at B&R boundaries, and use a declared trailing pre-cutoff field horizon at an exact boundary. Deterministic artifact paths accept byte-identical replay and reject different content. | advisory-methods |
| `workflows/deck_ranking_evaluation.py` | Retrospective served-model experiment adapter. Freeze/development builds raw pre-cutoff snapshots for all six declared origins, refits production parent projections with hash-pinned parent rules plus the production color-split registry, disables camps, and seals predictions for scales 1/.5/2 plus `opponent-plan-prior-v1` before development outcomes load. Confirmation accepts only complete reusable artifacts whose fold, protocol, scales/draws, taxonomy, quarantine, plan registry, manifest, snapshot, and prediction hashes match; it seals the selected development method before loading confirmation outcomes. Card availability is observed-by-cutoff where release dates are unavailable; fixed `.5%` deck/`2%` round quarantine ceilings preserve raw/retained ledgers rather than repairing metadata. Evaluation is descriptive and has no apply or publication path. | advisory-methods |
| `workflows/recurrent_validation.py` | Filesystem/DuckDB recurrent-validation adapters: store the additive recurrent protocol content-addressed under its digest; verify that each recurrent fold is an exact member of the hash-bound parent benchmark plan; seal one recurrent origin from a cutoff snapshot, snapshot-manifest hash, typed refit-stage chain, aligned forecast payload, and code commit; persist snapshot bytes under the origin digest and reject divergent collisions; build the common future-case manifest and score predictive + decision evidence; aggregate immutable bundles; and write inert operator-review proposals only. The convenience seam `refit_and_freeze_origin` can build the cutoff snapshot itself, but the CLI intentionally exposes only the explicit `plan|freeze|evaluate|aggregate|proposal` lifecycle. | advisory-methods, recurrent-era-intervals |
| `workflows/player_effect_diagnostic.py` | Identity-snapshot, DuckDB, and temporal adapters for the experimental player diagnostic: validate dated alias payloads; load cutoff-safe registrations/training rows; recompute production bases at earlier inner origins; freeze a result-free participant schedule; and open result strings only in the later evaluation phase. | advisory-methods |
| `sideboard.py` | **Maindeck-aware, two-stage core+hedge, impact-modulated.** Weighted submodular max-coverage (ILP/CBC primary + greedy explainable fallback; bounded-integer copies, color pre-filter, reserved slots, anti-hate pseudo-elements). Element weight for an (archetype, tag) pair is `field_share × swing × impact(best_hoser, archetype, ...).score_without_draw_prob()` — centrality × symmetry × castability, with NO draw-probability factor (see `advisory/impact.py`); draw-probability lives exclusively in the per-copy redundancy taper, derived from `impact.draw_probability`'s hypergeometric marginal rather than a curated constant. **Stage 1 (dedicated core)**: a per-card-copy redundancy penalty (`_redundancy_penalty`, the brief's `U_redundancy`) + a per-slot natural-budget floor `τ` stop committing once a slot's net marginal clears τ — so the core may be **fewer than 15** instead of padding. **Stage 2 (hedge)**: `_hedge_fill` fills the leftover slots with diversity-preferring **insurance** picks over a uniform-widened field, never displacing a core commit. Smart-mode (`advise sideboard --smart`) calibrates redundancy/τ as fractions of `_coverage_scale` so defaults are field-scale-invariant; output carries commit/insurance labels + the marginal-coverage curve + the uncovered-field tail. `advise sideboard` output also includes a per-card impact-factor breakdown (centrality/symmetry/castability/draw_prob) with a Dirichlet-derived confidence/brittle flag, a coverage% diagnostic (explicitly NOT the optimization objective), and a slot-ROI/punt table (`MatchupROI`) ranking field matchups by expected-match-win-per-dedicated-slot. **Gated: `opponent_linchpins=None` (no corpus/curated linchpin data for the field) ⇒ byte-identical to the pre-impact weights.** Still additively augmented by per-card×matchup value (`card_value`): gate-clearing opponents up-weight elements, and a per-matchup **OUT/IN plan** (`matchup_plans`) sides the maindeck's dead cards out for the chosen 15's best tech in (post-board exactly-60, copy-capped, locked-core protected, **lands exempt from the OUT pool** — the land test is the `type_line`, never the `cards.is_land` column, which is true for modal-DFC spell faces). The IN side additionally requires the candidate to attack an axis the opponent actually presents (`_in_axis_verdict`), so correlational lift alone cannot board an inert card; declined candidates are recorded on the plan (`out_suppressed`/`in_suppressed`) rather than dropped. When the flex pool (maindeck − locked core − lands) is structurally empty the plan honest-degrades with a named `plan_status` (`no-legal-flex`) instead of manufacturing a land cut. Degrades to pure coverage where per-card data is thin. Hoser catalog: `data/hosers/legacy.json` (package-shipped, curated SSOT loaded at startup); its `attacks` tags were corrected to the new `plays-<color>` vocabulary (Hydroblast→plays-red, Pyroblast→plays-blue, plus newly-added Blue/Red Elemental Blast) as part of this rework. | advisory-methods, sideboard-core-and-hedge |
| `impact.py` | Decomposed per-(hoser, opponent) impact score: `ImpactBreakdown` = `centrality × symmetry × castability × draw_prob`, multiplicative hard gates (any factor ≈0 zeroes the score, with floors so a merely-awkward card doesn't crater to a hard 0). `hoser_capabilities` bridges a hoser's `attacks` tags to a linchpin's `neutralized_by` capability vocabulary via a curated, oracle-text-grounded lookup. | advisory-methods |
| `linchpins.py` | Archetype linchpin model (a linchpin = the card whose removal breaks the archetype's plan). Hybrid derive (near-mandatory inclusion% + combo-critical role, at a conservative default centrality) + curated override (`data/linchpins/legacy.json`, curated wins by name). Owns the `neutralized_by` capability-token vocabulary (artifact-ability-lock, artifact-bounce, artifact-removal, exile-graveyard, counter-on-cast, board-sweep, creature-removal, enchantment-removal). | advisory-methods |
| `whattoplay.py` | Composition-derived proactivity score; vulnerability tags (graveyard-recursion/graveyard-fuel/plays-<color>/combo/low-curve/nonbasic-manabase/artifact-mana-reliant/creature-based/low-interaction/storm-reliant/ramp/noncreature-reliant/colorless-reliant) — the single monolithic graveyard-vulnerability tag was split into `graveyard-recursion`/`graveyard-fuel`, and `plays-<color>` is color-contingent (white/blue/black/red/green), driving Hydroblast/Pyroblast-style matching; `noncreature-reliant` (creature-slot density below `_NONCREATURE_RELIANT_MAX`) is the broad attachment point for anti-noncreature interaction (Force of Negation, Spell Pierce), and `colorless-reliant` (colorless-nonland-spell density at/above `_COLORLESS_RELIANT_DENSITY`) is the independent attachment point for the colorless half of Consign to Memory — both are separate axes from `combo`/`storm-reliant`/`creature-based`; the manabase axis is split into `nonbasic-manabase` (LAND-side fragility, reached by Wasteland/Blood Moon/Back to Basics) and `artifact-mana-reliant` (nonland artifact fast mana, reached by Null Rod/artifact removal) — a card's value in PROTECTING its own manabase is deliberately not modeled by `attacks`; hate-equity (coverage not sum); best-deck vs best-call (matchup-spread variance). | advisory-methods |
| `report.py` | The "Field Read & Deck Recommendation" surface: field composition + vulnerability profile + ranked decks + sideboard package + audit trail (every number with derivation, n, heuristic-vs-data label). Handles `--venues` cross-venue positioning comparison. | advisory-methods |
| `window.py` | `resolve_advisory_window` → `WindowResolution`: converts `--since/--until/--regime/--all-time` flags into a concrete window; degrades thin regimes (<500 rounds) to full corpus + a loud banner. `build_advisory_inputs` assembles the era-aware matrix + the detection-derived global field era (`resolve_field_era`: max(current ban-regime start, latest accepted high-share boundary), thin-degrade back to the ban regime). Adaptive audit lines name each entity's window + trigger and surface `// ⚠` drift alarms (alarms never move numbers). Mode field: `adaptive` (per-cell era-aware, default) / `uniform` / `full`. `build_multi_split_inputs` → `MultiSplitAdvisoryInputs` runs the same mode dispatch over the multi-split builders (`build_multi_split_adaptive`/`build_multi_split_matrix`, parents from `staged_split_parents()`) with the same audit conventions plus a `// multi-split` line — the one-pass every-camp matrix behind a separate entry point, so `build_advisory_inputs` and its ~15 spine call sites stay untouched. | — |
| `collection.py` | `CollectionView`: parses `<qty> <card>` text into an owned-card map; drives owned/acquire annotations on sideboard recommendations without changing the core ILP path. | — |
| `acquire.py` | `acquire_plan`: ranked priced buy list for a target archetype/board — scored by `impact = field_relevance × archetype_relevance`, price-sorted when `seed prices` has run, with redundancy/over-quantity flags. Exposed via `advise acquire`. | — |
| `primer.py` | Plain-speak per-matchup primer: given the sideboard's `MatchupPlan` list, generates a human-readable explanation of each OUT/IN swap and why. When `plan.degraded=True` (no per-card data), labels the block reasoning-based and suppresses fabricated numbers. | — |
| `refresh.py` | `run_refresh` + `render_refresh_result`: full deck-tuning refresh per venue — field-tuned maindeck + sideboard + primer in one call. Exposed via `advise refresh`. | — |
| `backtest.py` | Board backtest: compares `recommend_sideboard`'s output for an archetype/field against the sideboards top-finishing decks of that archetype actually ran in a comparable window (top-quartile-by-standings-rank). `--field-scope/--no-field-scope` (default ON) restricts the top-finisher sample to tournaments whose own metagame overlaps `--field`'s archetypes by at least `_FIELD_OVERLAP_MIN` (excludes off-meta events, e.g. graveyard-heavy tech vs a local field); honest-degrade banner when field-scope excludes every candidate tournament, with `--no-field-scope` as the diagnostic escape hatch back to the prior global sample. Never emits pass/fail — reports overlap / scorer-only / winners-only with a named confounds caveat (self-selected + metagame-lagged). Exposed via `advise backtest`. | — |
| `sweep.py` | Batch archetype-sweep backtest: runs `backtest_board` for every eligible archetype (deck-count floor) against one shared field, aggregates per-archetype divergences (scorer_only / winners_only) into ranked, root-cause-clustered findings with per-archetype tier gating; divergence-as-diagnostic — clusters are engine-error-map input, never auto-calibrated back into scores. `--json` emits copy-count histograms. Own windowing (not the advisory-window block; no `--provenance`). Exposed via `advise sweep`. | — |

### `models/` — shared Pydantic types
`Card`, `Decklist`, `Deck`, `TournamentResult`, `Round`, `Standing`, `Archetype`, `ArchetypeRule`,
`Condition`, `Variant`, `Fallback`, `MatchupCell`, `BanListSnapshot`,
`ConfidenceMetadata` (`established | evolving | speculative`, reused from edh-engine).
`Inventory`, `InventoryEntry`, `UserDeck`, `DeckVersion`, `DeckCardRef` (the personal collection
entities — all subclass `LegacyEngineModel`; stable UUID ids; `owner` key threaded through; append-only
versioning). `models/collection.py` houses collection-specific model helpers. `models/variant.py` houses
`VariantTag` and related sub-archetype types. `models/decklist.py` houses the canonical public
`parse_decklist` function (the inverse of `generation.export.format_decklist`).
The advisory result records `PositioningResult` / `DeckRanking` / `SideboardPackage` / `FieldDistribution` /
`FieldReadReport` live as dataclasses in `advisory/` (computed records carrying numpy samples / coverage
state), alongside the analytics records (`MetaShareReport`, `MatchupMatrix`, `TrendSeries`) — not here.

### Support
`cli.py` (Click nested groups per the project's CLI pattern), `config.py` (paths, URLs, rate limits,
pinned SHAs), `confidence.py` (shared tiering + sample-size→tier mapping),
`interaction_facts.py` (pure `interaction_facts(card) → InteractionFacts` classifier: graveyard use,
counter interaction, speed/consistency signals — consumed by `analytics/speculation.py` and
`advisory/report.py`'s vulnerability tagger; no side effects, no DB),
`card_tags.py` (static `staple_role` / `is_free_spell` tagging by card name),
`colors.py` (top-level color helpers shared between `archetype/colors.py` and other modules).

### `generation/` — Deck Generation (built)
| File | Responsibility | Brief |
|---|---|---|
| `consensus.py` | Modal-card aggregation over an archetype's in-window decks → legal exactly-60 + ≤15 de-duped consensus list; `card_frequencies` (per-card inclusion %, the flex/lock + candidate-pool primitive). Supports `--variant`, `--players`, and `--strong` pool filters. | deck-generation-and-moxfield |
| `export.py` | Portable multi-target import text (Moxfield/Archidekt/MTGGoldfish/`.dec`); pure, offline, zero network. | deck-generation-and-moxfield |
| `tuning.py` | Field-tuning (mode 2): greedy maindeck-flex swaps driven **solely** by field-weighted per-card×matchup value (`card_value`) — proactive cards have real value, no gameplan hollowing; coverage is audit-only, never a swap driver. No per-card signal → no swaps (honest fallback). Re-runs the maindeck-aware `recommend_sideboard` for the 15 + per-matchup plans; combined main+side legality guaranteed; positioning S carried as archetype context. Optional injected `card_winrates` lets the `--discover` path reuse one corpus scan. | deck-generation-and-moxfield |
| `discovery.py` | Gap discovery (mode 3, card-gap half): `adjacency_candidates` nominates cards a shell does NOT run yet (∉ deck ∩ color-legal ∩ role-relevant ∩ CMC-band, ranked by `deck_cards` co-occurrence PMI vs the archetype core); `discover_candidates` scores them by **cross-archetype** per-card value transfer (`card_value.lift`, role-gated via `TRANSFERABLE_ROLES`, established-tier gated), emitting a distinct suggest-and-label surface that never drives the tuner's greedy objective. Synergy/engine candidates are nominated but omitted-and-reported (need in-shell/goldfish validation). | card-adjacency-and-discovery |
| `card_distribution.py` | Per-card frequency distribution helpers shared between `generate consensus` and the doctor surface; decouples histogram logic from the consensus aggregation path. | — |
| `models.py` | Deck-generation result dataclasses (`TunedDeck`, `DeckDoctorReport`, `DiscoveryResult`, etc.) kept separate from the shared Pydantic `models/` layer. | — |

### `advisory/gaps.py` — Archetype-Gap Finder (built)
- **`gaps.py`** — gap discovery (mode 3, archetype-gap half): `compute_archetype_gaps` ranks under-explored archetypes by `gap_score = S − share_weight·share` over `positioning.rank_decks` × `metashare`, with the thin-matchup-data confidence gate delegated to `rank_decks(min_coverage=…)` (excluded archetypes reported, not hidden). Pure `_assemble_gaps` split from the DB/MC path. Surfaced via `report gaps`. | card-adjacency-and-discovery

### `viz/` — Visualization & Reporting (presentation layer)
Local, self-contained, no server — mirrors the `/knowledge-graph` + kanban-`board` HTML precedent.
Authors **Vega-Lite** specs in Python and renders them two ways: interactive self-contained **HTML via
`vega-embed`** (CDN) and static **PNG via `vl-convert`** (Rust, no Chrome). Fed by `analytics/`,
`advisory/`, and `generation/`; every chart carries the same confidence/labels as the text reports
(source-transparency principle).

| File | Responsibility | Brief |
|---|---|---|
| `theme.py` | The canonical `THEME` dicts (`screen`/`print`, dark) + `strip_and_inject(spec, variant)` — a spec-internal `config` is stripped and the project theme re-injected at render (vega-embed #27). | deck-viz-platform |
| `models.py` | The pure prep dataclasses (`BarModel`/`HeatmapModel`/`TierModel`/`TrendModel`) + `_*_model` fns — they bake the honesty logic (masking, fringe, thin-regime banding). | deck-viz-platform |
| `specs.py` | Hand-built Vega-Lite v6 dict builders (no Altair): `spec_metashare`, `spec_matchup_heatmap`, `spec_tier_list`, `spec_trends` (format-level) + `spec_matchup_row`, `spec_positioning` (per-deck tiles). No runtime validator — spec validity is a test-time concern (real Vega-Lite compiler via vl-convert + JSON snapshots). | deck-viz-platform |
| `render.py` | Two renderers off one spec: `render_png` (vl-convert, offline, JS-free) and `render_html_tile` (vl-convert `vegalite_to_html`, self-contained, interactive). | deck-viz-platform |
| `layout.py` | `Tile`/`Dashboard` 12-col grid model + `render_dashboard_html` (self-contained dark page; chart tiles via vega-embed CDN triple or inlined when `offline=True`). | deck-viz-platform |
| `deck_dashboard.py` | The headline reusable **per-deck dashboard**: composes meta-share, the (adaptive per-cell) matchup spread, trends-across-ban-regimes, positioning (best-call vs best-deck), the two-column consensus 60+15 list, and an auto-generated primer (degrades on thin data) into one page. Later feeds Moxfield surfacing. | deck-viz-platform, deck-generation-and-moxfield |

CLI: `viz deck <archetype> [--out file.html|<dir>] [--offline]` + `viz meta|matchups|trends|tiers [--out file.html|.png]`. (`report … --chart-dir` was removed; rendering centralizes here.)

### Deferred modules (clear seams, not built in MVP)
- **`goldfish/`** — port edh-engine's bipartite-matching mana solver + role-dispatch engine; adapt the mulligan to **straight London (no free mull)**; deck-as-data YAML; calibrate clocks against the Oops-All-Spells anchor. Feeds the meta-speed distribution. (legacy-foundations)
- **Goldfish-validated candidate-validation** — discovery (mode 3) ships confidence-gated suggest-and-label without it; the `goldfish/` pillar later slots in as a candidate → goldfish-passes? → promote-from-suggestion filter (and the in-shell signal that lets synergy-role candidates surface).

---

## Data Flow (MVP arc)

```
Scryfall oracle bulk ─► data/scryfall/ ─► Card index (whole pool)
fbettega cache (git)  ─► data/cache/**/*.json  (mirrored; raw source of truth)
MTGOFormatData (subtree@SHA) ─► data/rules/ + RULES_MANIFEST.json
WotC B&R ─► data/banlist/snapshots/*.json
        │
        ▼  ingestion/store.py  (normalize → Pydantic → DuckDB)
data/legacy.duckdb: tournaments · decks · deck_cards · rounds · standings · cards
        │
        ▼  ingestion/card_coverage.py  (exact authority ladder → cutoff-aware closure gate)
   reconciled derived deck-card names; unresolved evidence remains fail-closed
        │
        ▼  archetype/labeler.py  (resolve names → colors → classify)
   archetype_labels (deck → Archetype, Color, Variant, Companion)
        │
        ├─► analytics/  metashare (3 defs, online/paper) · matchup matrix (Wilson+shrinkage+tiers) · trends
        │         └─► viz/  (Vega-Lite specs → HTML via vega-embed + PNG via vl-convert; per-deck dashboard)
        │
        └─► advisory/   positioning (Bayesian MC) · sideboard (ILP+greedy) · whattoplay → report (field read + audit trail)
```

DuckDB is **rebuildable** from `data/` raw at any time (`legacy seed` → `store`); deleting it loses no
source data. This keeps reproducibility (raw JSON, pinned SHAs) while giving SQL joins/aggregation for
the matchup + meta-share workloads.

---

## External Integrations
| System | Access | Auth | Notes | Brief |
|---|---|---|---|---|
| Scryfall | bulk download + REST batch | none | UA+Accept headers; bulk no rate limit; whole oracle pool | scryfall-card-contract |
| fbettega MTG_decklistcache | git clone/pull (mirror) | none | PascalCase CacheItem JSON; daily commit ~18:32 UTC; **fragile single-maintainer — mirror locally** | fbettega-cache-schema, ingestion-ops-and-metashare |
| Badaro MTGOFormatData | git subtree @ pinned SHA | none | rules-as-JSON; ~monthly Legacy updates; diff on refresh | mtgoformatdata-rule-schema |
| Badaro MTGOArchetypeParser (C#, archived 2025-09-24) | reference only | none | frozen port target + golden-label source | archetype-matching-algorithm, csharp-python-port-strategy |
| WotC B&R | scheduled HTTP detection; manual curated acceptance | none | attributed candidates; only `eras confirm` changes accepted truth | data-autonomy-upstream, legacy-foundations |

All external data fetched once and mirrored; the engine makes **no network calls at analysis time**.

---

## Conventions
- **Code org:** `src/legacy_engine/{cli,config,confidence,interaction_facts,card_tags,colors}.py` + `models/ ingestion/ collection/ archetype/ analytics/ advisory/ generation/` (+ deferred `goldfish/`). Mirrors edh-engine layout.
- **Naming:** `snake_case.py`, `kebab-case` CLI commands (nested groups per `.claude/rules/patterns.md`), `PascalCase` Pydantic models.
- **CLI:** Click nested groups:
  - `seed cards|cache|rules|banlist|prices`
  - `refresh all|cards`
  - `ops scheduled-refresh|status` and `ops scheduler install|inspect|run-now|uninstall`
  - `report meta|matchups|tiers|trends|cards|gaps|subgroup|variants|new-cards|speculate|prices|affectedness`
  - `advise positioning|sideboard|whattoplay|field|report|refresh|acquire|compare|backtest|sweep|benchmark plan|benchmark freeze|benchmark evaluate|benchmark run`
  - `advise recurrent-validation plan|freeze|evaluate|aggregate|proposal`
  - `identify suggest|strong|track`
  - `generate consensus|tune|doctor` (`tune --discover` adds gap-discovery; `consensus --variant/--players/--strong`)
  - `export deck`
  - `collection import|show|status|rebuild`
  - `deck save|load|list|show|versions|buildable`
  - Lazy imports inside commands; `_setup_logging(verbose)` first.
  - `--my-deck NAME` (shorthand for loading a saved `UserDeck`) is available on all advisory/generate/advise commands.
  - `eras run|list|explain|confirm` — the stable-era ledger: detect + persist per-entity boundaries, list stable_since + triggers, walk one entity's boundary derivation, confirm an unattributed disturbance into `BAN_EVENTS`.
  - `superarchetype run|list|explain` *(built)* — the strategy-cluster taxonomy: `run` previews the offline candidate by default (recluster over the current window, merge curated overrides, report cluster-membership churn); `--promote` explicitly replaces the serving registry and DuckDB cache after operator review; `list` inspects clusters and members with `derived`/`assigned`/`curated` provenance; `explain` walks one archetype's assignment (shared vs disjoint core cards, the branch's AU p-value, and the derived assignment any curated override replaced). Offline labeling pass, sibling to `label` / `discover run` / `eras run` — matrix builders READ the registry and never cluster in a query hot path. Runs after `eras run` and before the best-call page refresh.
  - **Era-aware advisory**: `report matchups|gaps`, `advise positioning|whattoplay|report|refresh` take `--since/--until/--regime/--all-time` and default to the **adaptive per-cell era-aware matrix + detection-derived global field era** (via `advisory/window.py::resolve_advisory_window` + `build_advisory_inputs`; ban-only fallback with a loud audit line when no era data exists); thin explicit windows degrade to full-corpus with a loud banner. `generate consensus` and single-archetype `report cards` window at the entity's own era (`entity_era_window`, camp-aware with `--variant`); `discover run` pools within the parent's era by default (`--all-pool` escape). The separate Deck Rankings page uses its own provisional 28-day recency-weighted observed field and records that divergence.
  - `report meta --venues KEYS` and `advise report --venues KEYS` enable cross-venue comparison; `report meta --by-variant` splits by variant tag.
  - `report meta` is deck-based (windows but never degrades; full-corpus default).
  - **`--provenance online|paper`** filters by tournament provenance; available on all `advise` leaves (`positioning|sideboard|whattoplay|field|report|refresh|acquire|compare`) and on `report matchups|meta`. `advise backtest` is a validation tool with its own `--since/--until` plus `--field-scope/--no-field-scope` (default ON — tournament-level field-overlap filter, see the `backtest.py` row above), not a regime-aware advisory surface — it deliberately does NOT take the full `--since/--until/--regime/--all-time/--provenance` advisory-window-resolution block.
  - **`advise positioning --list-granular`** enables an opt-in `S_granular` overlay that treats the deck as individual cards rather than a named archetype; experimental, printed alongside the standard legacy S score. It does not change Deck Rankings.
  - **`report affectedness --archetype NAME`** explains which bans drove an archetype's `valid_since` (ban-affectedness derivation); `--provenance` scopes the archetype frequency check.
  - **`report trends --movers N`** appends a biggest-movers digest ranking archetypes by share delta between the two most recent regimes.
  - **`advise compare`** compares two deck configurations against the field (named-archetype + flags); a config is 1+ modes with per-opponent `max`-over-modes WR, so a transform-alternate is `--a`/`--a-transform` and a hate sideboard is `--a-lift`/`--a-lift-slot`. Two layers: a Bayesian-MC base (field-EV CIs + P(A beats B)) and a point-estimate lift overlay + break-even solver. Lifts are presence-correlational overlays, never in the MC.
  - **`report cards --contrast`** runs the matchup-conditioned sideboard-slot test: for `--archetype` vs `--vs` opponent, the WITH-card vs WITHOUT-card win-rate on `--board` (defaults `side` in this mode), with Wilson/Jeffreys CIs + a Fisher's-exact significance test on the diff, shown for both the adaptive ban-aware and full-corpus windows. Presence-correlational, NOT causal.
- **Error handling:** ingestion tolerates one bad deck/event (catch, log, continue); unresolved card names → `unmatched` bucket (never drop a deck); **fail-fast** on unknown archetype condition-type (load time, not match time).
- **Uncertainty everywhere:** every emitted stat carries `established|evolving|speculative`, sample size, interval, and source basis where available. Legacy report gates retain their documented behavior; Deck Rankings labels low-n/prior-only cells and keeps their point estimates visible.
- **Legality:** version-stamped `BanListSnapshot` blacklist, validated as-of-event-date.
- **Testing:** ingestion (mock JSON → verify parse/dedup/provenance); archetype (golden-test ≥99% label agreement; `ConditionTests.cs` ports 1:1 as a parametrized suite); analytics (known subset → hand-checked stats); advisory (synthetic matrix → verify Wilson/shrinkage/positioning/ILP). Deterministic given seed.
- **Reproducibility:** raw JSON + pinned SHAs are source of truth; DuckDB derived/rebuildable.

---

## Dependencies
| Package | Purpose | Notes |
|---|---|---|
| `httpx` | async HTTP (Scryfall) | edh-engine parity |
| `pydantic` ≥2 | typed models | edh-engine parity |
| `click` ≥8 | CLI | edh-engine parity |
| **`vl-convert-python`** ≥1.9,<2 | render Vega-Lite specs → static PNG (`vegalite_to_png`) AND self-contained interactive HTML (`vegalite_to_html`); Rust, no Chrome/Node | new (viz); the single render dep |
| `pyyaml` | deck-as-data (goldfish, later) | edh-engine parity |
| **`duckdb`** | embedded analytical store (matchup/meta-share joins) | **new — the storage divergence** |
| **`numpy`/`scipy`** | Beta/Dirichlet sampling, stats; `scipy.cluster.hierarchy` (linkage/fcluster/cophenet) for the superarchetype clustering | new (advisory); the superarchetype layer adds **no** new dependency — its AU bootstrap is a numpy loop and DerSimonian-Laird is a closed-form moment estimator |
| **`statsmodels`** | Wilson/Jeffreys CIs (`proportion_confint`) | new (advisory) |
| **`pulp`** | sideboard ILP (bundled CBC solver) | new (advisory) |
| **`ruptures`** ≥1.1,<2 | offline change-point detection (PELT / cosine KernelCPD) for era boundaries | new (eras) |
| `git` (system) | vendor/mirror fbettega cache + MTGOFormatData subtree | — |

No web server. DuckDB is embedded (file-backed, no server) — keeps the "no server" property while adding SQL. The `viz/` layer preserves it too: interactive output is self-contained HTML opened directly in a browser (vega-embed from CDN), and static PNG via `vl-convert` needs no browser/Chrome.

---

## What's Deferred
| Capability | Why | Seam |
|---|---|---|
| **goldfish/** simulation (mana solver, London mulligan Monte-Carlo, clocks, meta-speed) | Deck Mechanics pillar; ports cleanly from edh-engine; not blocking meta+advisory | deck-as-data YAML + role dispatch; legacy-foundations brief |
| **goldfish-validated candidate-validation** (gap-discovery mode 3 itself is now built: `generation/discovery.py` + `advisory/gaps.py`) | discovery ships confidence-gated suggest-and-label; promoting a suggestion to "validated" needs the goldfish pillar | consumes generation/discovery + (later) goldfish outputs |
| Full rules-correct game engine | Legacy is 1v1; goldfish suffices for speed/consistency | — |
| Live/real-time event tooling | all data pre-fetched | — |
| Non-Legacy formats | card/data layer is largely format-agnostic but out of scope | — |

---

## Open Questions
| Question | Impact | Disposition |
|---|---|---|
| **Golden-test oracle availability** — can we obtain the archived C# parser's published `mtgo_data_*.json` labels (or run the .NET 8 binary once) for a frozen corpus? | The ≥99% fidelity gate depends on it | **Verify during the ingestion/archetype phase.** Fallback designed: hand-curated label fixtures from MTGGoldfish/MTGO published archetype names. Not blocking the rest of the arc. |
| **DuckDB vs pure-pandas** at MVP scale | storage complexity | **Resolved: DuckDB** — the rounds-join matchup + 3-way meta-share queries justify SQL; embedded so "no server" holds. Revisit only if it proves overkill. |
| **Matcher LOC reconciliation** (~210 core vs ~600 total cited) | effort estimate | **Resolved:** port target is the ~210-line `Detect` + 12 condition predicates + color intersection + fallback scoring; surrounding models/loader/enum are the rest. ~3-5 day estimate stands. |
| **fbettega `Rounds` matchup coverage** (Leagues lack rounds) | matchup-matrix sample is bimodal | **Resolved in design:** matchup-n kept separate from metashare-n; cells gated by n; surfaced as a caveat. |
| **MTGGoldfish/mtgdecks scraping** for cross-validation | nice-to-have | Deferred; aggregators 403-block bots — use as human cross-check only, not a feed. |
| **NIU thesis prior art** (sideboard MIP, 403-blocked) | novelty claim | Flag for a manual human pull before claiming full novelty in the sideboard recommender. |

---

## Related Documents
| Document | Purpose |
|----------|---------|
| [VISION.md](VISION.md) | Vision, four pillars, domain model |
| [SPEC.md](SPEC.md) | Capabilities, entities, NFRs |
| [PRINCIPLES.md](PRINCIPLES.md) | Decision heuristics |
| [research-plan.md](research-plan.md) | Research routing (all pre-architecture research complete) |
| [briefs/ingestion-archetype-contracts/parent.md](briefs/ingestion-archetype-contracts/parent.md) | ingestion/ + archetype/ data contracts |
| [briefs/advisory-methods.md](briefs/advisory-methods.md) | advisory/ statistical + optimization methods |
| [briefs/sideboard-core-and-hedge.md](briefs/sideboard-core-and-hedge.md) | sideboard core/hedge construction theory (per-copy value curve, natural budget, hedge objective) |
| [briefs/superarchetype-aggregation.md](briefs/superarchetype-aggregation.md) | strategy-cluster taxonomy, random-effects pooling, the concentration/heterogeneity gates, the shrinkage rung |
| [briefs/legacy-foundations.md](briefs/legacy-foundations.md) | rules, mulligan, format constraints (goldfish later) |
| [briefs/legacy-metagame.md](briefs/legacy-metagame.md) | meta, data sources |

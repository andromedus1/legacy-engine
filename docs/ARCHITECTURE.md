---
name: architecture-legacy-engine
description: Read for how legacy-engine is built — module map, file responsibilities, data flow, the core data models, storage decision, conventions, dependencies, and the built-vs-deferred split. The detailed architecture grounded in all four research streams.
type: architecture
kind: planning
updated: 2026-06-13
summary: |
  Detailed architecture for legacy-engine, a Magic: The Gathering Legacy analytics platform (sibling to
  edh-engine). Python 3.11+ Click CLI mirroring edh-engine's stack, plus scipy/numpy/statsmodels/pulp
  for advisory and DuckDB as an embedded analytical store (the one justified divergence, driven by the
  matchup-matrix rounds-join workload). MVP arc: ingestion/ (Scryfall + fbettega cache + vendored
  MTGOFormatData rules + ban-list) → archetype/ (ported MTGOArchetypeParser matcher) → analytics/
  (meta-share, matchup matrix, per-card value) + advisory/ (positioning, maindeck-aware sideboard, what-to-play)
  + generation/ (consensus, export, field-tuning, gap-discovery) → models/ → data/. goldfish/ is the
  deferred pillar; only goldfish-validated candidate-validation remains deferred behind it.
decisions:
  - "Mirror edh-engine's stack (Python 3.11+, Click CLI, Pydantic, httpx, local files) + add scipy/numpy/statsmodels (advisory stats), pulp/CBC (sideboard ILP), and vl-convert-python (Vega-Lite viz render)."
  - "STORAGE: raw mirrored JSON is the reproducible source of truth (data/cache/, data/scryfall/, data/rules/, data/banlist/); a rebuildable embedded DuckDB (data/legacy.duckdb) is the analytical layer for meta-share + matchup-matrix joins. The one justified divergence from edh-engine's pure-files approach, driven by the rounds-join matchup workload."
  - "archetype/ is the novel subsystem: vendor MTGOFormatData rules-as-JSON pinned to a SHA (data/rules/ + manifest), reimplement only the ~210-line MTGOArchetypeParser Detect matcher in Python, golden-test to >=99% label agreement against the archived C# parser's published labels (fallback: hand-curated fixtures)."
  - "Scryfall ADR RESOLVED: EXTEND edh-engine's ingestion/scryfall.py (every needed function verified to exist), index the WHOLE oracle pool (~30k+ IDs, not a fixed subset); do NOT adopt Scrython (bulk index makes the API path rare) or mtg_parser (fbettega JSON is the decklist source, already name-normalized)."
  - "Deck color = lands.produced_mana ∩ nonlands.colors (NOT color_identity); legality validated against a version-stamped BanListSnapshot blacklist (NOT Scryfall's lagging legacy flag)."
  - "Matchup matrix: computed ourselves from Rounds; Wilson CIs + Beta-Binomial shrinkage; confidence tiers (speculative n<30 hidden / evolving 30-99 / established >=100); matchup-n kept separate from metashare-n; meta-% computed 3 labeled ways with online/paper split."
  - "Ingestion mirror-and-decouple: consume the fbettega cache JSON (not mtgo.com), behind an ingestion/ port so a replacement source swaps in without touching analytics/advisory."
  - "MVP = ingestion + archetype + analytics + advisory + generation (consensus/export/field-tuning/gap-discovery mode 3); goldfish/ (port edh-engine's mana solver + straight-London mulligan) is the deferred pillar; only goldfish-validated candidate-validation remains deferred behind it."
  - "VISUALIZATION: viz/ is a local Vega-Lite presentation layer (interactive HTML via vega-embed + static PNG via vl-convert, strip-and-inject theming, 12-col tile/layout) that replaces matplotlib-based charting; headline deliverable is a reusable per-deck dashboard composing meta-share/matchups/trends/positioning/consensus. No server, no cloud (mirrors the knowledge-graph/board HTML precedent)."
---

# Architecture: legacy-engine

*Last updated: 2026-06-13*

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
┌────────────────────────────────────────────────────────────────────────────┐
│                                CLI  (cli.py)                                 │
│  seed · refresh · label · report (meta|matchups|tiers|trends|cards|gaps)      │
│  · advise (positioning|sideboard|whattoplay|report)                           │
│  · generate (consensus|tune) · export (deck) · viz (deck)  [later: goldfish]  │
│  · collection (import|show|status|rebuild) · deck (save|load|list|show|       │
│    versions|buildable)                                                         │
└───┬──────────┬───────────┬────────────┬───────────────┬─────────────────────┘
    │          │           │            │               │
┌───▼─────┐ ┌─▼────────┐ ┌▼──────────┐ ┌▼────────────┐ ┌▼──────────────┐
│ingestion/│ │archetype/ │ │analytics/ │ │advisory/    │ │generation/    │
│scryfall  │ │rules      │ │metashare  │ │positioning  │ │consensus      │
│cache     │ │matcher    │ │matchup    │ │sideboard    │ │export·tuning  │
│banlist   │ │colors     │ │trends     │ │whattoplay   │ │discovery      │
│rules_    │ │labeler    │ │charts     │ │report       │ │(goldfish/     │
│ vendor   │ │golden_test│ │card_value │ │gaps         │ │ deferred)     │
│store     │ │           │ │           │ │             │ │               │
└───┬─────┘ └────┬──────┘ └─────┬─────┘ └──────┬──────┘ └───────────────┘
    │            │              │              │
┌───▼─────────────────────────────────────────────────────────────────────────┐
│ collection/  (user personal layer — peer of ingestion/)                       │
│  persist · store · inventory · decks · allocation                             │
└───┬─────────────────────────────────────────────────────────────────────────┘
    │
┌───▼────────────────────────────────────────────────────────────────────────┐
│                                 models/                                     │
│  Card · Decklist · Deck · TournamentResult · Round · Standing · Archetype · │
│  ArchetypeRule · Condition · MatchupCell · BanListSnapshot · ConfidenceMetadata │
│  Inventory · InventoryEntry · UserDeck · DeckVersion · DeckCardRef          │
│  (advisory/analytics result records are dataclasses in their own modules)   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│   data/   (raw = source of truth)            data/legacy.duckdb (derived)     │
│   cache/    (mirrored fbettega JSON)          tournaments · decks · deck_cards │
│   scryfall/ (oracle bulk + name index)        rounds · standings · labels     │
│   rules/    (vendored MTGOFormatData @SHA)     cards · matchups (materialized) │
│   banlist/  (dated B&R snapshots)             inventory_entries · user_decks  │
│   collection/ (user-authored SSOT)            deck_versions · deck_version_   │
│     inventory.json                              cards                          │
│     decks/<id>.json (per deck)                                                │
└────────────────────────────────────────────────────────────────────────────┘
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
| `scryfall.py` | **Extended from edh-engine** (ADR: extend, don't fork). Oracle-bulk download + name index over the WHOLE pool (~30k+ IDs) + `/cards/collection` batch fallback. UA+Accept headers, 50-100ms delay. | api.scryfall.com | scryfall-card-contract |
| `cache.py` | Mirror + parse the fbettega `MTG_decklistcache`. Parse the PascalCase `CacheItem {Tournament, Decks[], Rounds[], Standings[]}`; cards as `{Count, CardName}`; derive online/paper provenance from source-dir + Uri host; treat empty Rounds/Standings (Leagues) as normal. Incremental via `git pull` + day-folder diff. | github (fbettega) | fbettega-cache-schema |
| `rules_vendor.py` | Vendor MTGOFormatData rules-as-JSON via git subtree into `data/rules/`, pinned to a commit SHA in `RULES_MANIFEST.json`. `legacy refresh rules` pulls upstream, diffs `Formats/Legacy/`, surfaces new archetypes/condition-types. | github (Badaro) | mtgoformatdata-rule-schema, csharp-python-port-strategy |
| `banlist.py` | Maintain dated `BanListSnapshot`s (banned names + banned_date + ban_reason + category predicates) from WotC B&R announcements. Blacklist validation. | (hand-curated + WotC) | legacy-foundations |
| `store.py` | Normalize parsed raw JSON → Pydantic models → load into DuckDB (`data/legacy.duckdb`). DuckDB is a **rebuildable derived cache**; raw JSON is the source of truth. | duckdb | ingestion-ops-and-metashare |

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

### `analytics/` — Meta & Performance
| File | Responsibility | Brief |
|---|---|---|
| `match_results.py` | Shared foundation: join `rounds` → archetype labels via `decks` (normalized player name within a tournament), parse the aggregate match-score string into match-level W/L, accumulate directed `(arch_a, arch_b)→{wins,losses,n}` cells + per-archetype marginal records; normalize names, drop byes/draws, surface unmatched-pairing coverage. Consumed by `metashare` (§3c), `matchup.py`, and `card_value.py`. Also exposes `compute_card_winrates` — per-card `(card, board, opponent)→{wins,losses,n}` + per-card marginal aggregates joining `deck_cards`, reusing the same cardinality-safe CTEs (presence-correlational, NOT causal). | ingestion-ops-and-metashare |
| `card_value.py` | Confidence-rated per-card value over `compute_card_winrates`: two-level empirical-Bayes (matchup cell shrinks toward the card's shrunk marginal, which shrinks toward the global baseline); `CardValue` carries `lift`/`p_shrunk`/`tier`/`n`; `card_values_vs(...)` returns gated values consumed by `advisory/sideboard` (maindeck-aware plans) and `generation/tuning` (swap objective). | advisory-methods |
| `metashare.py` | Meta-% three labeled ways (raw count / top-cut presence / win-rate-weighted via `match_results`), split online/paper/blend; ≥2%-of-field inclusion. SQL over DuckDB. | ingestion-ops-and-metashare |
| `matchup.py` | Build the matchup matrix from `match_results`' directed cells: per-cell `{wins, n, p_raw, p_shrunk(Wilson/Beta), ci, tier}`; mirror fixed 0.5; **matchup-n separate from metashare-n**. Stats primitives (`beta_binomial_shrink_to`, `wilson_or_jeffreys_ci`) reused by `card_value`. `build_matrix` takes a `since/until` window; `build_adaptive_matrix` (regime-aware advisory) sources each pairwise cell over `[max(valid_since(a), valid_since(b)), …)` — unaffected cells keep full history, ban-affected cells truncate. | advisory-methods |
| `affectedness.py` | Ban-affectedness classifier for adaptive regime-aware advisory: `archetype_valid_since` = the latest ban each archetype was materially affected by (ran a banned card in ≥ threshold of its pre-ban decks), data-derived from `BAN_EVENTS` × `card_frequencies` × `regime_windows`. Lives in `analytics` (no advice) so the matrix builder consumes it without an `analytics → advisory` cycle. | — |
| `trends.py` | Meta evolution across ban-list regimes (version-stamped). | legacy-metagame |

### `advisory/` — Meta Attack/Advisory (the differentiator)
| File | Responsibility | Brief |
|---|---|---|
| `field.py` | `FieldDistribution` (the SSOT for "what is the field"): global-from-`metashare` (with Dirichlet counts) + custom user field (normalize/impute/Other); consumed by positioning, sideboard, whattoplay. | advisory-methods |
| `positioning.py` | `score(deck, field) = Σ w_a·winrate(D vs a)`; Bayesian Monte-Carlo (Beta cells + Dirichlet shares) primary, delta-method fast check; custom user field; rank by risk-adjusted lower-posterior-quantile from shared-field draws (P(best) reported as a secondary view) + a data-coverage flag; report S **and** unweighted aggregate. | advisory-methods |
| `sideboard.py` | **Maindeck-aware.** Weighted submodular max-coverage (ILP/CBC primary + greedy explainable fallback; bounded-integer copies, color pre-filter, reserved slots, anti-hate pseudo-elements) chooses the 15, additively **augmented** by per-card×matchup value (`card_value`): gate-clearing opponents up-weight elements, and a per-matchup **OUT/IN plan** (`matchup_plans`) sides the maindeck's dead cards out for the 15's best tech in (post-board exactly-60, copy-capped, locked-core protected). Degrades to pure coverage where per-card data is thin → byte-identical to the rounds-less baseline. | advisory-methods |
| `whattoplay.py` | Composition-derived proactivity score; vulnerability tags (graveyard-reliant/combo/low-curve/greedy-manabase/creature-based/low-interaction/storm-reliant); hate-equity (coverage not sum); best-deck vs best-call (matchup-spread variance). | advisory-methods |
| `report.py` | The "Field Read & Deck Recommendation" surface: field composition + vulnerability profile + ranked decks + sideboard package + audit trail (every number with derivation, n, heuristic-vs-data label). | advisory-methods |

### `models/` — shared Pydantic types
`Card`, `Decklist`, `Deck`, `TournamentResult`, `Round`, `Standing`, `Archetype`, `ArchetypeRule`,
`Condition`, `Variant`, `Fallback`, `MatchupCell`, `BanListSnapshot`,
`ConfidenceMetadata` (`established | evolving | speculative`, reused from edh-engine).
`Inventory`, `InventoryEntry`, `UserDeck`, `DeckVersion`, `DeckCardRef` (the personal collection
entities — all subclass `LegacyEngineModel`; stable UUID ids; `owner` key threaded through; append-only
versioning).  `models/decklist.py` houses the promoted public `parse_decklist` function (the canonical
inverse of `generation.export.format_decklist`; previously private in `advisory/report.py`).
The advisory result records `PositioningResult` / `DeckRanking` / `SideboardPackage` / `FieldDistribution` /
`FieldReadReport` live as dataclasses in `advisory/` (computed records carrying numpy samples / coverage
state), alongside the analytics records (`MetaShareReport`, `MatchupMatrix`, `TrendSeries`) — not here.

### Support
`cli.py` (Click nested groups per the project's CLI pattern), `config.py` (paths, URLs, rate limits,
pinned SHAs), `confidence.py` (shared tiering + sample-size→tier mapping).

### `generation/` — Deck Generation (built)
| File | Responsibility | Brief |
|---|---|---|
| `consensus.py` | Modal-card aggregation over an archetype's in-window decks → legal exactly-60 + ≤15 de-duped consensus list; `card_frequencies` (per-card inclusion %, the flex/lock + candidate-pool primitive). | deck-generation-and-moxfield |
| `export.py` | Portable multi-target import text (Moxfield/Archidekt/MTGGoldfish/`.dec`); pure, offline, zero network. | deck-generation-and-moxfield |
| `tuning.py` | Field-tuning (mode 2): greedy maindeck-flex swaps driven **solely** by field-weighted per-card×matchup value (`card_value`) — proactive cards have real value, no gameplan hollowing; coverage is audit-only, never a swap driver. No per-card signal → no swaps (honest fallback). Re-runs the maindeck-aware `recommend_sideboard` for the 15 + per-matchup plans; combined main+side legality guaranteed; positioning S carried as archetype context. Optional injected `card_winrates` lets the `--discover` path reuse one corpus scan. | deck-generation-and-moxfield |
| `discovery.py` | Gap discovery (mode 3, card-gap half): `adjacency_candidates` nominates cards a shell does NOT run yet (∉ deck ∩ color-legal ∩ role-relevant ∩ CMC-band, ranked by `deck_cards` co-occurrence PMI vs the archetype core); `discover_candidates` scores them by **cross-archetype** per-card value transfer (`card_value.lift`, role-gated via `TRANSFERABLE_ROLES`, established-tier gated), emitting a distinct suggest-and-label surface that never drives the tuner's greedy objective. Synergy/engine candidates are nominated but omitted-and-reported (need in-shell/goldfish validation). | card-adjacency-and-discovery |

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
| `models.py` | The pure prep dataclasses (`BarModel`/`HeatmapModel`/`TierModel`/`TrendModel`) + `_*_model` fns migrated from the former `charts.py` — they bake the honesty logic (masking, fringe, thin-regime banding) and are matplotlib-free. | deck-viz-platform |
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
| WotC B&R | manual/curated | none | dated snapshots; blacklist validation | legacy-foundations |

All external data fetched once and mirrored; the engine makes **no network calls at analysis time**.

---

## Conventions
- **Code org:** `src/legacy_engine/{cli,config,confidence}.py` + `models/ ingestion/ collection/ archetype/ analytics/ advisory/ generation/` (+ deferred `goldfish/`). Mirrors edh-engine layout.
- **Naming:** `snake_case.py`, `kebab-case` CLI commands (nested groups per `.claude/rules/patterns.md`), `PascalCase` Pydantic models.
- **CLI:** Click nested groups (`seed cards|cache|rules|banlist`, `report meta|matchups|tiers|trends|cards|gaps`, `advise positioning|sideboard|whattoplay|report`, `generate consensus|tune` (`tune --discover` adds exploratory adjacent-card suggestions), `export deck`, `collection import|show|status|rebuild`, `deck save|load|list|show|versions|buildable`); lazy imports inside commands; `_setup_logging(verbose)` first. **Regime-aware advisory**: the matrix consumers (`report matchups|gaps`, `advise positioning|whattoplay|report`) take `--since/--until/--regime/--all-time` and default to the **adaptive per-cell ban-aware matrix + current-regime field** (via `advisory/window.py::resolve_advisory_window` + `build_advisory_inputs`); `--all-time` is the full-corpus escape; thin explicit windows degrade to full-corpus with a loud banner. `report meta` is deck-based (windows but never degrades; full-corpus default).
- **Error handling:** ingestion tolerates one bad deck/event (catch, log, continue); unresolved card names → `unmatched` bucket (never drop a deck); **fail-fast** on unknown archetype condition-type (load time, not match time).
- **Confidence everywhere:** every emitted stat carries `established|evolving|speculative` + sample size; low-n gated (matchup n<30 hidden, BEST-CALL only on established/evolving).
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
| **`numpy`/`scipy`** | Beta/Dirichlet sampling, stats | new (advisory) |
| **`statsmodels`** | Wilson/Jeffreys CIs (`proportion_confint`) | new (advisory) |
| **`pulp`** | sideboard ILP (bundled CBC solver) | new (advisory) |
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
| [briefs/legacy-foundations.md](briefs/legacy-foundations.md) | rules, mulligan, format constraints (goldfish later) |
| [briefs/legacy-metagame.md](briefs/legacy-metagame.md) | meta, data sources |

---
name: architecture-legacy-engine
description: Read for how legacy-engine is built — module map, file responsibilities, data flow, the core data models, storage decision, conventions, dependencies, and the built-vs-deferred split. The detailed architecture grounded in all four research streams.
type: architecture
kind: planning
updated: 2026-05-30
summary: |
  Detailed architecture for legacy-engine, a Magic: The Gathering Legacy analytics platform (sibling to
  edh-engine). Python 3.11+ Click CLI mirroring edh-engine's stack, plus scipy/numpy/statsmodels/pulp
  for advisory and DuckDB as an embedded analytical store (the one justified divergence, driven by the
  matchup-matrix rounds-join workload). MVP arc: ingestion/ (Scryfall + fbettega cache + vendored
  MTGOFormatData rules + ban-list) → archetype/ (ported MTGOArchetypeParser matcher) → analytics/
  (meta-share, matchup matrix) + advisory/ (positioning, sideboard recommender, what-to-play) → models/
  → data/. goldfish/ and generation/ are deferred pillars.
decisions:
  - "Mirror edh-engine's stack (Python 3.11+, Click CLI, Pydantic, httpx, matplotlib, local files) + add scipy/numpy/statsmodels (advisory stats) and pulp/CBC (sideboard ILP)."
  - "STORAGE: raw mirrored JSON is the reproducible source of truth (data/cache/, data/scryfall/, data/rules/, data/banlist/); a rebuildable embedded DuckDB (data/legacy.duckdb) is the analytical layer for meta-share + matchup-matrix joins. The one justified divergence from edh-engine's pure-files approach, driven by the rounds-join matchup workload."
  - "archetype/ is the novel subsystem: vendor MTGOFormatData rules-as-JSON pinned to a SHA (data/rules/ + manifest), reimplement only the ~210-line MTGOArchetypeParser Detect matcher in Python, golden-test to >=99% label agreement against the archived C# parser's published labels (fallback: hand-curated fixtures)."
  - "Scryfall ADR RESOLVED: EXTEND edh-engine's ingestion/scryfall.py (every needed function verified to exist), index the WHOLE oracle pool (~30k+ IDs, not a fixed subset); do NOT adopt Scrython (bulk index makes the API path rare) or mtg_parser (fbettega JSON is the decklist source, already name-normalized)."
  - "Deck color = lands.produced_mana ∩ nonlands.colors (NOT color_identity); legality validated against a version-stamped BanListSnapshot blacklist (NOT Scryfall's lagging legacy flag)."
  - "Matchup matrix: computed ourselves from Rounds; Wilson CIs + Beta-Binomial shrinkage; confidence tiers (speculative n<30 hidden / evolving 30-99 / established >=100); matchup-n kept separate from metashare-n; meta-% computed 3 labeled ways with online/paper split."
  - "Ingestion mirror-and-decouple: consume the fbettega cache JSON (not mtgo.com), behind an ingestion/ port so a replacement source swaps in without touching analytics/advisory."
  - "MVP = ingestion + archetype + analytics + advisory; goldfish/ (port edh-engine's mana solver + straight-London mulligan) and generation/ are deferred pillars with clear seams."
---

# Architecture: legacy-engine

*Last updated: 2026-05-29*

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
│  seed · refresh · label · report (meta|matchups|tiers) · advise (position|   │
│  sideboard|whattoplay)            [later: goldfish · generate]               │
└───┬──────────┬───────────┬────────────┬───────────────┬─────────────────────┘
    │          │           │            │               │
┌───▼─────┐ ┌──▼────────┐ ┌▼──────────┐ ┌▼────────────┐ ┌▼──────────────┐
│ingestion/│ │archetype/ │ │analytics/ │ │advisory/    │ │ (deferred:)   │
│scryfall  │ │rules      │ │metashare  │ │positioning  │ │ goldfish/     │
│cache     │ │matcher    │ │matchup    │ │sideboard    │ │ generation/   │
│banlist   │ │colors     │ │trends     │ │whattoplay   │ │               │
│rules_    │ │labeler    │ │charts     │ │report       │ │               │
│ vendor   │ │golden_test│ │           │ │             │ │               │
│store     │ │           │ │           │ │             │ │               │
└───┬─────┘ └────┬──────┘ └─────┬─────┘ └──────┬──────┘ └───────────────┘
    │            │              │              │
┌───▼────────────▼──────────────▼──────────────▼────────────────────────────┐
│                                 models/                                     │
│  Card · Decklist · Deck · TournamentResult · Round · Standing · Archetype · │
│  ArchetypeRule · Condition · MatchupCell · BanListSnapshot · SideboardPackage│
│  PositioningResult · ConfidenceMetadata                                     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│   data/   (raw = source of truth)            data/legacy.duckdb (derived)     │
│   cache/    (mirrored fbettega JSON)          tournaments · decks · deck_cards │
│   scryfall/ (oracle bulk + name index)        rounds · standings · labels     │
│   rules/    (vendored MTGOFormatData @SHA)     cards · matchups (materialized) │
│   banlist/  (dated B&R snapshots)                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### Data Layers → Analytical Pillars (mirrors edh-engine)
| Layer | What | MVP pillar | Later |
|---|---|---|---|
| **Observed** | fbettega tournament cache, Scryfall cards, ban-list, archetype labels | Meta & Performance | feeds advisory |
| **Synthetic** | goldfish simulation (speed, consistency) | Deck Mechanics *(deferred)* | meta-speed metric |
| **Generated** | positioning, sideboard packages, eventually deck candidates | Meta Attack/Advisory + Deck Generation *(gen deferred)* | — |

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
| `match_results.py` | Shared foundation: join `rounds` → archetype labels via `decks` (normalized player name within a tournament), parse the aggregate match-score string into match-level W/L, accumulate directed `(arch_a, arch_b)→{wins,losses,n}` cells + per-archetype marginal records; normalize names, drop byes/draws, surface unmatched-pairing coverage. Consumed by both `metashare` (§3c) and `matchup.py`. | ingestion-ops-and-metashare |
| `metashare.py` | Meta-% three labeled ways (raw count / top-cut presence / win-rate-weighted via `match_results`), split online/paper/blend; ≥2%-of-field inclusion. SQL over DuckDB. | ingestion-ops-and-metashare |
| `matchup.py` | Build the matchup matrix from `match_results`' directed cells: per-cell `{wins, n, p_raw, p_shrunk(Wilson/Beta), ci, tier}`; mirror fixed 0.5; **matchup-n separate from metashare-n**. | advisory-methods |
| `trends.py` | Meta evolution across ban-list regimes (version-stamped). | legacy-metagame |
| `charts.py` | matplotlib charts: tier list, meta share, matchup heatmap, trends. | (edh-engine pattern) |

### `advisory/` — Meta Attack/Advisory (the differentiator)
| File | Responsibility | Brief |
|---|---|---|
| `positioning.py` | `score(deck, field) = Σ w_a·winrate(D vs a)`; Bayesian Monte-Carlo (Beta cells + Dirichlet shares) primary, delta-method fast check; custom user field; rank by P(best) from shared-field draws; report S **and** unweighted aggregate. | advisory-methods |
| `sideboard.py` | Weighted submodular max-coverage; ILP (PuLP/CBC) exact primary + greedy (1−1/e) explainable fallback; bounded-integer copies, color pre-filter, reserved slots, anti-hate pseudo-elements. | advisory-methods |
| `whattoplay.py` | Composition-derived proactivity score; vulnerability tags (graveyard-reliant/combo/low-curve/greedy-manabase/creature-based/low-interaction/storm-reliant); hate-equity (coverage not sum); best-deck vs best-call (matchup-spread variance). | advisory-methods |
| `report.py` | The "Field Read & Deck Recommendation" surface: field composition + vulnerability profile + ranked decks + sideboard package + audit trail (every number with derivation, n, heuristic-vs-data label). | advisory-methods |

### `models/` — shared Pydantic types
`Card`, `Decklist`, `Deck`, `TournamentResult`, `Round`, `Standing`, `Archetype`, `ArchetypeRule`,
`Condition`, `Variant`, `Fallback`, `MatchupCell`, `BanListSnapshot`, `SideboardPackage`,
`PositioningResult`, `ConfidenceMetadata` (`established | evolving | speculative`, reused from edh-engine).

### Support
`cli.py` (Click nested groups per the project's CLI pattern), `config.py` (paths, URLs, rate limits,
pinned SHAs), `confidence.py` (shared tiering + sample-size→tier mapping).

### Deferred modules (clear seams, not built in MVP)
- **`goldfish/`** — port edh-engine's bipartite-matching mana solver + role-dispatch engine; adapt the mulligan to **straight London (no free mull)**; deck-as-data YAML; calibrate clocks against the Oops-All-Spells anchor. Feeds the meta-speed distribution. (legacy-foundations)
- **`generation/`** — gap discovery + build tuning against the (current/projected) meta, validated by simulation + matchup data.

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
        ├─► analytics/  metashare (3 defs, online/paper) · matchup matrix (Wilson+shrinkage+tiers) · trends · charts
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
- **Code org:** `src/legacy_engine/{cli,config,confidence}.py` + `models/ ingestion/ archetype/ analytics/ advisory/` (+ deferred `goldfish/ generation/`). Mirrors edh-engine layout.
- **Naming:** `snake_case.py`, `kebab-case` CLI commands (nested groups per `.claude/rules/patterns.md`), `PascalCase` Pydantic models.
- **CLI:** Click nested groups (`seed cards|cache|rules|banlist`, `report meta|matchups|tiers|trends`, `advise positioning|sideboard|whattoplay`); lazy imports inside commands; `_setup_logging(verbose)` first.
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
| `matplotlib` ≥3.8 | charts | edh-engine parity |
| `pyyaml` | deck-as-data (goldfish, later) | edh-engine parity |
| **`duckdb`** | embedded analytical store (matchup/meta-share joins) | **new — the storage divergence** |
| **`numpy`/`scipy`** | Beta/Dirichlet sampling, stats | new (advisory) |
| **`statsmodels`** | Wilson/Jeffreys CIs (`proportion_confint`) | new (advisory) |
| **`pulp`** | sideboard ILP (bundled CBC solver) | new (advisory) |
| `git` (system) | vendor/mirror fbettega cache + MTGOFormatData subtree | — |

No web server. DuckDB is embedded (file-backed, no server) — keeps the "no server" property while adding SQL.

---

## What's Deferred
| Capability | Why | Seam |
|---|---|---|
| **goldfish/** simulation (mana solver, London mulligan Monte-Carlo, clocks, meta-speed) | Deck Mechanics pillar; ports cleanly from edh-engine; not blocking meta+advisory | deck-as-data YAML + role dispatch; legacy-foundations brief |
| **generation/** (gap discovery, build tuning) | needs simulation + matchups to validate candidates | consumes advisory + goldfish outputs |
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

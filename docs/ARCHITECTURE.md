---
name: architecture-legacy-engine
description: Read for the high-level module map and data flow of legacy-engine. HIGH-LEVEL ONLY — detailed module design comes from /architecture after the pre-architecture research lands.
type: architecture
kind: planning
summary: |
  High-level architecture sketch for legacy-engine (produced by /ideate). Mirrors edh-engine's
  Python-CLI + local-files shape: ingestion → archetype-parser → analytics/advisory → models → data.
  Names the modules, the data flow, the committed external dependencies, and the biggest architectural
  risk (the fragile community scraper layer). Detailed design is deferred to /architecture.
decisions:
  - "Mirror edh-engine's stack exactly: Python 3.11+, Click CLI, Pydantic models, httpx, local files (JSONL/JSON/YAML), matplotlib; no DB or server for MVP."
  - "Module map: ingestion/ (scryfall + fbettega cache) → archetype/ (ported MTGOFormatData rules) → analytics/ (meta stats, matchup matrix) + advisory/ (positioning, sideboard recommender) → models/ → data/. goldfish/ and generation/ added in later pillars."
  - "The archetype/ module is the key novel subsystem (no commander to key on); it consumes ported MTGOFormatData rules + card data and emits Archetype labels."
  - "Ingestion decouples from mtgo.com: consume the fbettega MTG_decklistcache JSON (mirrored locally), not the raw site — the scraper layer is fragile (Badaro's cache died 2025-06-10)."
  - "Biggest architectural risk: the community scraper/cache layer is fragile and externally owned — mitigate by mirroring the cache repo and treating archetype rules + cache as versioned local inputs."
  - "Scryfall is the shared card-dimension source with edh-engine; deck-as-data + mana + mulligan code is ported from edh-engine's goldfish/ when the Deck Mechanics pillar starts."
created: 2026-05-29
updated: 2026-05-29
---

# Architecture: legacy-engine (high-level)

> **HIGH-LEVEL ONLY.** This is the /ideate sketch. Detailed module interfaces, file responsibilities,
> and data schemas come from `/research-pipeline:architecture` after the pre-architecture research in
> [research-plan.md](research-plan.md) lands. *Why* → [VISION.md](VISION.md). *What* → [SPEC.md](SPEC.md).

## System shape
A Python 3.11+ analytics platform with a Click CLI and a local file-based data layer — **mirroring
edh-engine exactly** for maximum pattern/code reuse. Three data layers (observed / synthetic /
generated) feed four analytical pillars. The MVP builds the observed → meta-analytics → advisory arc.

```
┌──────────────────────────────────────────────────────────────────────┐
│                            CLI  (cli.py)                              │
│  seed · refresh · parse · report · advise   (goldfish · generate later)│
└────┬──────────┬───────────┬───────────┬────────────┬──────────────────┘
     │          │           │           │            │
┌────▼────┐ ┌──▼────────┐ ┌▼─────────┐ ┌▼─────────┐ ┌▼──────────┐
│ingestion│ │archetype/ │ │analytics/│ │advisory/ │ │ (later:)  │
│         │ │           │ │          │ │          │ │ goldfish/ │
│scryfall │ │rules      │ │meta_stats│ │position  │ │generation/│
│fbettega │ │(MTGO-     │ │matchup   │ │sideboard │ │           │
│banlist  │ │ FormatData│ │trends    │ │whattoplay│ │           │
│         │ │ port)     │ │          │ │          │ │           │
└────┬────┘ └────┬──────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘
     │           │             │            │             │
┌────▼───────────▼─────────────▼────────────▼─────────────▼────┐
│                          models/                              │
│  Card · Decklist · Archetype · TournamentResult ·             │
│  MatchupCell · BanListSnapshot · (DeckDefinition later)       │
└──────────────────────────────┬────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│                            data/                                │
│  scryfall/   cache/(fbettega)   banlist/   meta/   reports/     │
└──────────────────────────────────────────────────────────────────┘
```

## Module map (high-level)

| Module | Responsibility | Maps to edh-engine |
|--------|---------------|--------------------|
| `ingestion/` | Fetch + cache Scryfall card data, the fbettega tournament-cache JSON, and banned-list snapshots. No runtime network calls. | `ingestion/` (scryfall shared; fbettega replaces topdeck/moxfield/edhtop16) |
| `archetype/` | **The novel subsystem.** Port MTGOFormatData rules → label each Decklist into the community taxonomy. Auditable, data-driven. | *(no analog — cEDH keys on commander)* |
| `analytics/` | Meta stats (tier list, multi-definition meta-%, online/paper splits), matchup matrix, trends across ban regimes. Charts/reports. | `analytics/` + `stats/` |
| `advisory/` | Meta-positioning score, sideboard recommender (set-cover over hoser→target graph), what-to-play advisor. | *(new — the Legacy differentiator)* |
| `models/` | Shared Pydantic types: Card, Decklist, Archetype, TournamentResult, MatchupCell, BanListSnapshot. | `models/` |
| `goldfish/` *(later)* | Deck-as-data, bipartite-matching mana solver, London-mulligan Monte Carlo. **Ported from edh-engine.** | `goldfish/` (direct reuse) |
| `generation/` *(later)* | Gap discovery + build tuning. | *(edh-engine's deferred optimizer)* |

## Data flow (MVP arc)

```
Scryfall bulk "Oracle Cards"  ──► data/scryfall/card_pool.json      (card dimension)
fbettega MTG_decklistcache    ──► data/cache/**/*.json              (tournament facts, mirrored)
WotC B&R announcements        ──► data/banlist/snapshots/*.json     (dated legality)
        │
        ▼
archetype/ (MTGOFormatData rules + card data)  ──► labeled Decklists (Archetype per deck)
        │
        ├──► analytics/  ──► tier list · meta-% (raw/top-cut/winrate-weighted) · matchup matrix · online-vs-paper
        │
        └──► advisory/   ──► positioning score · sideboard package · what-to-play   (consumes analytics + matchups)
```

## Committed external dependencies
- **Scryfall API** (free REST + daily bulk) — card dimension. Shared with edh-engine.
- **fbettega/MTG_decklistcache** + **mtg_decklist_scrapper** — tournament-results fact source (the edhtop16 analog). Mirror locally.
- **Badaro/MTGOFormatData** + MTGOArchetypeParser logic — archetype-detection rules to port.
- Python libs (mirror edh-engine): `httpx`, `pydantic`, `click`, `matplotlib`, `pyyaml`; `beautifulsoup4` if any HTML fallback scraping is needed.
- *(Later)* MTGJSON as a secondary card-data warehouse if needed.

## Biggest architectural risk
**The community scraper/cache layer is fragile and externally owned** — Badaro's original cache shut
down 2025-06-10; the live successor (fbettega) is one maintainer. Mitigation: consume the *cache JSON*
(not mtgo.com directly), **mirror the cache + rules repos locally as versioned inputs**, and design
ingestion so a new upstream source can be swapped behind the `ingestion/` boundary without touching
analytics/advisory. (To be hardened in /architecture.)

## Deferred to /architecture (after research)
Detailed file responsibilities, the exact fbettega cache JSON schema, the MTGOFormatData rule schema
and port strategy, the matchup-matrix statistics (CI method, confidence gating thresholds), the
sideboard set-cover formulation, and the storage decision (local files vs SQLite/DuckDB) if meta
queries warrant it. See [research-plan.md](research-plan.md).

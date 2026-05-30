---
id: epic-tournament-ingestion
kind: epic
stage: implementing
tags: [ingestion]
parent: null
depends_on: [epic-foundations-card-data]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Tournament Ingestion

## Brief

Mirror and parse the fbettega `MTG_decklistcache` — the Legacy analog to cEDH's edhtop16 — and load it
into DuckDB. This epic delivers the observed-data fact layer: tournaments, decks (mainboard +
sideboard), rounds (pairings + results), and standings, with online-vs-paper provenance derived at
ingest and card names joined to the card dimension.

Covers: the git-mirror + incremental pull of the cache, parsing the PascalCase `CacheItem
{Tournament, Decks[], Rounds[], Standings[]}` (treating empty Rounds/Standings on MTGO Leagues as
normal, not an error), provenance derivation (source-dir + Uri host), the unmatched-card-name bucket,
and normalization into DuckDB tables. The `ingestion/` port boundary keeps a replacement source
swappable without touching analytics. Does NOT cover archetype labeling (that's
`epic-archetype-classifier`) or any analytics.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md` — the exact CacheItem JSON schema, repo layout, provenance, cadence, consumption/mirroring strategy.
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — mirror-and-decouple resilience, source fragility, the Rounds → matchup-matrix feasibility (bimodal coverage).
- `docs/briefs/legacy-metagame.md` — data-source ecosystem context.

## Foundation references
- `docs/ARCHITECTURE.md` — `ingestion/cache.py`, `ingestion/store.py`; the mirror-and-decouple data flow; DuckDB tables (tournaments/decks/deck_cards/rounds/standings).
- `docs/SPEC.md` — Decklist, TournamentResult, Round, Standing entities; ingestion-resilience NFR.

## Decomposition

Split by capability into 3 features. The parser (models + JSON parsing + provenance) is the
foundation; the DuckDB tournament tables build on its models; the mirror integrates both into
`seed cache`. Card-name resolution reuses the foundations Scryfall index (no new join feature needed —
the parser keeps raw names, the analytics layer joins to the `cards` table).

### Child features
- `epic-tournament-ingestion-cache-parser` — models (TournamentResult/Deck/CardCount/RoundMatch/Standing) + `parse_cache_item` + provenance + League/Challenge handling — depends on: `[]`
- `epic-tournament-ingestion-duckdb-tables` — extend `store.py` with tournaments/decks/deck_cards/rounds/standings + load — depends on: `[epic-tournament-ingestion-cache-parser]`
- `epic-tournament-ingestion-cache-mirror` — git mirror + Legacy-event discovery + `seed cache` (mirror→parse→load) — depends on: `[epic-tournament-ingestion-cache-parser, epic-tournament-ingestion-duckdb-tables]`

### Decomposition risks
- Mirror/git operations must be isolated behind a thin function so tests drive discovery/load from fixtures, never a live clone.
- The `decks`↔`rounds` player join keys on player name strings (the cache's only link) — tolerate missing/duplicate names gracefully.

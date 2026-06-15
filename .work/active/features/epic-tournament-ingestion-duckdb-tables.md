---
id: epic-tournament-ingestion-duckdb-tables
kind: feature
stage: done
tags: [ingestion]
parent: epic-tournament-ingestion
depends_on: [epic-tournament-ingestion-cache-parser]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
---

# DuckDB Tournament Tables + Load

## Brief
Extend the DuckDB store (`ingestion/store.py`, which already owns the `cards` table) with the
tournament-data tables — `tournaments`, `decks`, `deck_cards`, `rounds`, `standings` — and the load
functions that persist parsed `TournamentResult` models into them. Each row carries the derived
provenance (online/paper) and the source tournament id so analytics can group/filter. Load is
idempotent per tournament (re-ingesting an event replaces its rows). Does NOT mirror the repo
(cache-mirror) or parse JSON (cache-parser).

## Epic context
- Parent epic: `epic-tournament-ingestion`. Consumes the parser's models; consumed by cache-mirror's load step.

## Inherited design decisions
- Reuse the existing `ingestion/store.py` access pattern (connect/init_schema); the `cards` table stays; add tournament tables to the same schema init.
- Rebuildable derived cache (raw JSON is source of truth).

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — the tournament tables the analytics/matchup layer needs (rounds carry pairings → matchup matrix; standings carry records).
- `docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md` — field shapes.

## Foundation references
- `docs/ARCHITECTURE.md` — `ingestion/store.py` DuckDB schema; `src/legacy_engine/ingestion/store.py` (existing cards table + `INSERT OR REPLACE` idiom).

## Architectural choice (autopilot, judgment)
Extend `ingestion/store.py` with 5 tournament tables, added to the same `init_schema`. A `tournament_id`
(the `Uri` if present, else `source:name:date`) keys all child rows. `decks` carries an `archetype`
column left NULL now (the archetype epic populates it). `load_tournament` is idempotent: `INSERT OR
REPLACE` the tournament row, then DELETE + re-insert that tournament's child rows (a re-ingest fully
refreshes one event). Cards stored as `deck_cards(tournament_id, deck_idx, board, name, count)`.

## Implementation Units
### Unit 1: extend `src/legacy_engine/ingestion/store.py`
`TOURNAMENT_DDL` for `tournaments(id PK, name, date, uri, format, source, provenance)`,
`decks(tournament_id, deck_idx, player, result, archetype)`, `deck_cards(tournament_id, deck_idx,
board, name, count)`, `rounds(tournament_id, match_idx, player1, player2, result)`,
`standings(tournament_id, rank, player, points, wins, losses, draws)`. `init_schema` creates these +
the existing `cards`. `tournament_id(tr)` helper. `load_tournament(con, tr) -> str` (returns the id).
**Acceptance**: load a parsed Challenge → 1 tournament, N decks, M deck_cards, rounds, standings rows; re-load same tournament → counts stable (idempotent); a League (no rounds/standings) loads decks only; query by `tournament_id` works.

## Testing
- `tests/test_store_tournaments.py` — in-memory DuckDB: load a Challenge + a League fixture (reuse parser fixtures via parse_cache_item); assert row counts per table; idempotent re-load; archetype column NULL.

## Implementation notes
- **Files changed**: extended `src/legacy_engine/ingestion/store.py` (TOURNAMENT_DDL ×5 tables, `init_schema` creates them, `tournament_id`, `load_tournament`).
- **Tests added**: `tests/test_store_tournaments.py` — full suite **101 passing in 0.81s**.
- **Discrepancies from design**: none. `archetype` column left NULL (archetype epic owns it); idempotent re-ingest via INSERT-OR-REPLACE tournament + DELETE/re-insert children.
- **Adjacent issues parked**: none.

## Review (2026-05-29)
**Verdict**: Approve. **Blockers/Important**: none.
**Nits**: `tournament_id` falls back to `source:name:date` when Uri is absent — fine for MTGO/Melee which always have a Uri; the fallback is for odd sources. The `decks`↔`rounds`↔`standings` join is on player-name strings (the cache's only link) — matchup computation (analytics epic) must tolerate name mismatches.
**Notes**: Reuses the existing store access pattern; tournament tables added to the same schema init alongside `cards`. Idempotent per-tournament refresh verified. 101 tests green. Unblocks cache-mirror.

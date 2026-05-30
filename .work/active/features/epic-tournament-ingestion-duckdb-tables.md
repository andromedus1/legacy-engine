---
id: epic-tournament-ingestion-duckdb-tables
kind: feature
stage: drafting
tags: [ingestion]
parent: epic-tournament-ingestion
depends_on: [epic-tournament-ingestion-cache-parser]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
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

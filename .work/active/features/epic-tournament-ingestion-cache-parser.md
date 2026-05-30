---
id: epic-tournament-ingestion-cache-parser
kind: feature
stage: drafting
tags: [ingestion]
parent: epic-tournament-ingestion
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Cache Parser: Models + CacheItem Parsing + Provenance

## Brief
The typed models for the fbettega tournament cache and the parser that turns a raw `CacheItem` JSON
object into them. Covers the Pydantic models (`TournamentResult`, `Deck`, `CardCount`, `RoundMatch`,
`Standing`) with PascalCase aliases, `parse_cache_item(raw, source) -> TournamentResult`, online/paper
**provenance derivation** (from the source directory + `Uri` host), and the League-vs-Challenge branch
(empty `Rounds`/`Standings` + a `"5-0"`-style `Result` is normal, not an error). Does NOT mirror the repo
(cache-mirror) or load DuckDB (duckdb-tables).

## Epic context
- Parent epic: `epic-tournament-ingestion`. Foundation feature — the models + parser the other two consume.

## Inherited design decisions
- Pydantic-everywhere via `LegacyEngineModel` (use `Field(alias="...")` for PascalCase keys; base has `populate_by_name=True`).
- Provenance is derived at ingest (not a field); kept on every deck/tournament row.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md` — the authoritative CacheItem schema, field names, League/Challenge structural differences, provenance encoding, ` // ` split names.

## Foundation references
- `docs/ARCHITECTURE.md` — `ingestion/cache.py`, the tournament data models.

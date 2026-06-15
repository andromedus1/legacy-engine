---
id: epic-tournament-ingestion-cache-parser
kind: feature
stage: done
tags: [ingestion]
parent: epic-tournament-ingestion
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
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

## Architectural choice (autopilot, judgment)
Models in `models/tournament.py` use `Field(alias="PascalCaseKey")` (base `populate_by_name=True`) so
they validate raw fbettega JSON directly via `model_validate`. The CacheItem is nested
(`{Tournament:{...}, Decks, Rounds, Standings}`), so `parse_cache_item(raw, source)` lifts tournament
meta from `raw["Tournament"]`, derives provenance, and validates the lists. `Rounds` shape is handled
defensively (flatten any nested `Matches`, else treat each entry as a match) since briefs disagreed on
whether it's a flat match list or round-wrapped. Dates kept as ISO strings (no tz parsing needed yet).

## Implementation Units
### Unit 1: `src/legacy_engine/models/tournament.py`
`CardCount{count:Count, name:CardName}`, `RoundMatch{player1:Player1, player2:Player2, result:Result}`,
`Standing{rank,player,points,wins,losses,draws}`, `Deck{player,result,anchor_uri:AnchorUri,
mainboard:Mainboard[CardCount], sideboard:Sideboard[CardCount]}`, `TournamentResult{name,date,uri,
format:Formats, source, provenance, decks, rounds, standings}`. All subclass `LegacyEngineModel`.
### Unit 2: `src/legacy_engine/ingestion/cache.py`
`derive_provenance(source, uri) -> "online"|"paper"|"unknown"` (MTGO/Manatraders→online;
MTGmelee/Topdeck/CardsRealm→paper; else uri-host fallback). `parse_rounds(raw) -> list[RoundMatch]`
(flatten nested Matches). `parse_cache_item(raw, source) -> TournamentResult`.
**Acceptance**: Challenge fixture → decks+rounds+standings populated, provenance "online"; League fixture → empty rounds/standings, decks with "5-0" Result, no error; Melee fixture → provenance "paper".

## Testing
- `tests/test_tournament_models.py` — alias mapping (Count/CardName/Player1...), defaults.
- `tests/test_cache_parser.py` — fixtures: a MTGO Challenge (rounds+standings), a MTGO League (empty rounds), a Melee paper event; assert provenance, deck/round/standing counts, League-empty-is-normal.

## Implementation notes
- **Files created**: `src/legacy_engine/models/tournament.py` (CardCount/RoundMatch/Standing/Deck/TournamentResult with PascalCase aliases), `src/legacy_engine/ingestion/cache.py` (`derive_provenance`, `parse_rounds`, `parse_cache_item`, `_coerce_format`).
- **Tests added**: `tests/test_tournament_models.py`, `tests/test_cache_parser.py` — full suite **96 passing in 0.70s**.
- **Discrepancies from design**: none. `Rounds` flattening handles both flat-match and round-wrapped shapes (briefs disagreed); `Formats` coerced from bare-string-or-list.
- **Adjacent issues parked**: none.

## Review (2026-05-29)
**Verdict**: Approve. **Blockers/Important**: none.
**Nits**: dates kept as ISO strings (no tz/`date` parsing yet — fine until trends need date math); `Standing` models the common tiebreakers (omits OMWP/GWP/OGWP — add if the matchup-weighting needs them).
**Notes**: Models validate raw fbettega JSON directly via aliases; League empty-rounds handled as normal; provenance derivation covers source-dir + Uri-host fallback. 96 tests green. Unblocks duckdb-tables.

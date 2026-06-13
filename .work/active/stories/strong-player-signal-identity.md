---
id: strong-player-signal-identity
kind: story
stage: done
tags: [analytics]
parent: feature-strong-player-signal
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

# Player identity resolution — curated alias table + heuristic suggester

Resolve free-text `decks.player` handles into canonical player ids. See the parent
`feature-strong-player-signal` § Design (Decision 1) for the full rationale.

**Approach:** explicit, git-tracked `data/players/aliases.json` is the source of truth (banlist
precedent: raw curated JSON is SSOT, DuckDB derived). No handle is ever silently merged; absent
handles resolve to themselves. An opt-in `identify suggest` heuristic proposes clusters for human
curation but writes nothing.

## Units
- U1 — `analytics/players/identity.py`: `resolve_player(handle, alias_map)` (pure; reuses
  `match_results.normalize_player` — collation SSOT, no second key) + `load_alias_map(path)`. Seed
  `data/players/aliases.json` with the `Bosh N Roll`/`BoshNRoll_Brian`/`Bosh95` cluster as the worked
  example + schema comment. `config.py` gets `ALIASES_PATH` (constants-only-config pattern).
- U2 — `materialize_player_aliases(con, alias_map)` derived `player_aliases(handle_norm, player_id)`
  table; idempotent (DROP+CREATE or INSERT OR REPLACE). Wire into the store rebuild path.
- U3 — `suggest_aliases(con, *, min_overlap=4)`: normalized-stem clusters that never co-occur
  same-event-same-day; returns `AliasSuggestion`s. `identify suggest` CLI leaf (new nested group;
  `_setup_logging` first; lazy imports).

## Tests (`tests/analytics/players/test_identity.py`)
- Three `Bosh*` handles → one id; `Andrea Mengucci` → itself; unknown → itself; None/blank → `""`.
- `materialize_player_aliases` idempotent (run twice, same rows).
- `suggest_aliases` surfaces a synthetic `Bosh*` cluster; does NOT propose merging two players who
  co-occur in the same event on the same day.

## AC
- `resolve_player` deterministic, reuses `normalize_player`, never raises.
- Handles absent from the map resolve to themselves (no silent drop/merge).
- `identify suggest` writes nothing — suggestions to stdout only.

## Implementation notes

**Files created:**
- `src/legacy_engine/data/players/aliases.json` — curated alias SSOT; seeded with `bosh-n-roll` cluster (three handles).
- `src/legacy_engine/analytics/players/__init__.py` — package init.
- `src/legacy_engine/analytics/players/identity.py` — `load_alias_map`, `resolve_player`, `materialize_player_aliases`, `suggest_aliases`, `AliasSuggestion`.
- `tests/analytics/players/__init__.py`
- `tests/analytics/players/test_identity.py` — 25 tests (all passing).

**Files modified:**
- `src/legacy_engine/config.py` — added `PLAYERS_DIR` and `ALIASES_PATH` constants (constants-only-config pattern).
- `src/legacy_engine/ingestion/store.py` — added `PLAYER_ALIASES_DDL` + wired into `init_schema` so a fresh DB always has the empty table structure; data population is separate via `materialize_player_aliases`.

**CLI:** deferred to the consensus story (`strong-player-signal-consensus`) per the design's CLI section — the `identify` group with `suggest` leaf is listed under CLI for story 1 in the feature design, but the story units explicitly decomposed it as U3 here. The logic is fully implemented in `identity.py`; the CLI wrapper can be added without touching this module. Noting the deferral here for the orchestrator.

**Deviations from design:**
- `PLAYER_ALIASES_DDL` constant in `store.py` + `CREATE TABLE IF NOT EXISTS` in `init_schema` ensures the table structure exists in every fresh DB. The data (rows) is populated separately via `materialize_player_aliases`. This cleanly separates schema declaration (store's job) from data materialization (identity module's job), mirroring the `cards` DDL pattern exactly.
- `suggest_aliases` uses a union-find over compatible pairs within each stem group rather than a simple pairwise list, to correctly handle clusters of 3+ handles.
- Test fixture for `test_proposes_bosh_cluster` places the three Bosh handles in separate tournaments (not the same event) — this is the realistic scenario (a player uses different handles at different events), and is what the heuristic is designed to find.

**Suite:** 1415 passed (was 1390; +25 new). Ruff: clean. Mypy: no new errors (pre-existing duckdb import-not-found is project-wide).

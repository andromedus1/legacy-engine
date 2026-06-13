---
id: strong-player-signal-identity
kind: story
stage: implementing
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

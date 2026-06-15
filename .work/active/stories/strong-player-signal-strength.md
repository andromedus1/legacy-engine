---
id: strong-player-signal-strength
kind: story
stage: done
tags: [analytics]
parent: feature-strong-player-signal
depends_on: [strong-player-signal-identity]
release_binding: v0.1.0
gate_origin: null
created: 2026-06-13
updated: 2026-06-14
---

# Player strength scoring + archetype-history tracking

Build a per-player track record from `standings` and define "strong" defensibly. See parent
`feature-strong-player-signal` § Design (Decision 2 + the tracking half of Decision 3).

**"Strong" = sustained, tier-gated, never a single 5-0.** Shrunk match-win-rate
(`beta_binomial_shrink_to`, prior 0.5) + a hard `≥min_events` floor + `evolving`-tier minimum
(≥30 decisive matches). Reuses `confidence.tier_for_sample` + the two-level-empirical-bayes
primitive — strong inherits the same honesty discipline as every emitted stat.

## Units
- U1 — `analytics/players/strength.py`: `PlayerRecord` dataclass + `compute_player_records(con, *,
  alias_map, since, until, provenance, cut_size)` — aggregate `standings` (wins/losses/draws/rank)
  across events, identity-resolved, windowed; compute `win_rate_shrunk` + `tier`. Honest about
  standings-only `events` (MTGO League dumps lack standings — bimodal coverage, documented).
- U2 — `is_strong(rec, *, min_events=3, min_tier="evolving", min_win_rate=0.55)` pure predicate +
  `strong_player_set(records, **gate) -> set[str]`.
- U3 — `analytics/players/history.py`: `player_archetype_history(con, player_id, *, alias_map)` →
  per-regime `(regime_label, archetype, deck_count)` using `trends.regime_windows`. CLI:
  `identify strong --archetype <a> [window flags] [gate flags]` and `identify track <player>`.

## Tests (`tests/analytics/players/test_strength.py`, `test_history.py`)
- Single 5-0 (events=1, n≈7) → `is_strong == False` (event floor + speculative tier).
- 25-10 across 5 events → `True`. Shrinkage pulls a 6-0/2-event player below 1.0.
- `compute_player_records` sums correctly across events; respects the window; deterministic.
- `player_archetype_history` partitions a player's decks into the right regimes.

## AC
- A single hot finish never qualifies as strong (the spec's explicit requirement).
- Scores reuse the project shrink + tier primitives (no ad-hoc threshold philosophy).
- `strong_player_set` computed over the consumer's window (so "strong in current regime" works).

## Implementation notes

**Files created:**
- `src/legacy_engine/analytics/players/strength.py` — `PlayerRecord` dataclass, `compute_player_records`, `is_strong`, `strong_player_set`.
- `src/legacy_engine/analytics/players/history.py` — `ArchetypeRegimeRow`, `player_archetype_history`.
- `tests/analytics/players/test_strength.py` — 31 tests across compute, alias pooling, is_strong gates, strong_player_set.
- `tests/analytics/players/test_history.py` — 12 tests covering regime partition, alias pooling, edge cases.

**Key design decisions made during implementation:**
- `history.py` does NOT call `resolve_player` — instead it iterates `alias_map.items()` to build `handles_norm` (all handles that map to `player_id`), then uses a SQL `IN` predicate. This avoids a DuckDB-side join and is simpler for the read-path.
- `compute_player_records` resolves identity in Python (iterate rows, call `resolve_player` per row) rather than via a DuckDB join on `player_aliases`. This keeps the Python and SQL collation in sync and avoids requiring the derived `player_aliases` table to be materialized for every query.
- `win_rate_shrunk` uses `prior_mean=0.5, strength=15.0` matching the `SHRINK_STRENGTH` constant in `matchup.py` for consistency.
- `display` name is chosen as the most-frequent raw handle within the query window (not a static alias config field), so it reflects recency.

**Test suite:** 43 new tests added (31 strength + 12 history). Full suite: 1458 passed (1415 baseline + 43 new). Ruff: clean. Mypy pre-existing errors in `matchup.py` not touched.

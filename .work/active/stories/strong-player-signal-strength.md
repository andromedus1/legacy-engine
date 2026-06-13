---
id: strong-player-signal-strength
kind: story
stage: implementing
tags: [analytics]
parent: feature-strong-player-signal
depends_on: [strong-player-signal-identity]
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
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

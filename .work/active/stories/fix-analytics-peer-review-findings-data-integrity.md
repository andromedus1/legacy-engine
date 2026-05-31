---
id: fix-analytics-peer-review-findings-data-integrity
kind: story
stage: done
tags: [analytics, bug]
parent: fix-analytics-peer-review-findings
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Cardinality-safe rounds join + bye classification (findings 1 rounds-half, 7)

## Brief
Make the rounds↔decks join in `analytics/match_results.py` cardinality-safe: a `dup` CTE flags normalized
player names that are non-unique within a tournament, and the accumulator excludes those pairings into a new
`MatchCoverage.ambiguous_player_names` counter instead of double-counting or mislabeling them unmatched (#1).
Also classify blank-opponent byes (`player2=""`) as `dropped_byes_draws` before the unmatched check (#7).

## Implementation
Parent `fix-analytics-peer-review-findings` → **Unit 1**. File: `analytics/match_results.py` only (incl. the
`MatchCoverage` dataclass + its invariant docstring). Tests in `tests/test_match_results.py`. See parent
`## Design decisions` (skip-the-confusing-ones) and `## Implementation Units` Unit 1 for the exact CTE,
loop ordering, and acceptance criteria. Trickiest — build the dup-CTE + ambiguous flagging first.

## Implementation notes

### Cardinality-safe join (finding #1)

Added two CTEs to `_JOIN_SQL`:

- **`dup`**: identifies `(tournament_id, norm)` pairs where `count(*) > 1` — the ambiguity detector.
- **`uniq_decks`**: collapses the raw `decks` table to one row per `(tournament_id, normalized-player)` using
  `ANY_VALUE(archetype)`. This is the critical cardinality guard: the original `LEFT JOIN decks d1` would
  produce N rows per pairing when a player had N duplicate deck rows, inflating both `total_pairings` and any
  counter that fired. The `uniq_decks` join is always exactly 0-or-1 rows.

The `amb1`/`amb2` boolean flags (from `du1.norm IS NOT NULL`) identify which pairings had a dup-CTE hit. These
are checked in the accumulator loop before the archetype is ever used, so an arbitrary archetype from
`ANY_VALUE` is safe.

**Design deviation from spec**: The spec's `_JOIN_SQL` used `LEFT JOIN decks d1` directly, which would still
fan out for duplicate names. Added the `uniq_decks` CTE to prevent the fan-out; otherwise `total_pairings`
and `ambiguous_player_names` would over-count (N times per ambiguous pairing, not once). The `dup`+`uniq_decks`
pair is the correct implementation of "skip the confusing ones" without silent inflation.

### Bye classification (finding #7)

The accumulator loop now checks `not (p2 and str(p2).strip())` **before** the ambiguous and unmatched checks.
A bye row (`player2=""`) had `arch2 = NULL` (no deck match), so the old code incremented `unmatched`. Now it
correctly increments `dropped_byes_draws` and continues.

### MatchCoverage invariant

Added `ambiguous_player_names: int = 0` field. Docstring updated to reflect the five-counter invariant:
`total_pairings == decisive_matched + unmatched + dropped_byes_draws + mirror_matches + ambiguous_player_names`.

### Tests added (12 new, 48 total, all passing)

- `test_ambiguous_player_names_classified_not_unmatched` — player1 name non-unique → `ambiguous_player_names=1`,
  `unmatched=0`, `decisive_matched=0`, no matchup tallies.
- `test_ambiguous_player_on_one_side_also_excluded` — ambiguity on player2's side also excludes the pairing.
- `test_blank_opponent_bye_counted_dropped_not_unmatched` — `player2=""` → `dropped_byes_draws`, not `unmatched`.
- `test_coverage_sum_invariant_five_counters` — combined tournament set exercises all five buckets; asserts
  `total_pairings == sum(all counters)`.
- Two new raw fixture dicts: `_DUP_NAMES`, `_BYE_ROUND`.

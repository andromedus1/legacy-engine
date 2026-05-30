---
id: epic-meta-analytics-match-results
kind: feature
stage: drafting
tags: [analytics]
parent: epic-meta-analytics
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Match-Outcome Extraction (rounds → archetype win/loss)

## Brief
The shared data-prep foundation both meta-share (win-rate-weighted definition) and the matchup matrix
build on. Read the DuckDB `rounds` table (`player1`, `player2`, `result`) and join each pairing to the
two players' archetype labels via the `decks` table (join key = normalized `player` within a
`tournament_id`). Parse the aggregate match-score `result` string (e.g. `"2-1"`, `"2-0"`) into
**match-level** W/L for player1 (the brief is explicit: `result` is an aggregate match score, NOT
per-game winners, so a `2-1` is one match win — exactly what a matchup matrix needs). Accumulate two
aggregates: a directed `(archetype_a, archetype_b) → {wins, losses, n}` table (the matchup raw cells)
and a per-archetype marginal `archetype → {wins, losses, n}` (the win-rate-weighted meta-share input).

Owns the fragile bits the ops brief flags as the weak link: **player-name normalization** (trim,
casefold, collapse whitespace) for the rounds↔decks join, and **byes / intentional-draws / forfeit**
handling (empty `player2`, no-clear-winner `result` rows are dropped from win-rate accumulation, never
counted). Surfaces an explicit **unmatched-pairing coverage** count (pairings whose players didn't
resolve to a labeled deck) as a stat — never silently dropped. Carries the online/paper provenance
through so downstream consumers can split. Emits raw `{wins, losses, n}` aggregates only.

Does NOT compute Wilson CIs, shrinkage, confidence tiers, or the MatchupCell stats (that's
`matchup-matrix`). Does NOT compute the three meta-share definitions (that's `metashare`). It is the
join + parse + normalize layer that produces the raw counts both consume.

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: **foundation feature** — produces the raw match-outcome aggregates that
  `metashare` (win-rate-weighted §3c) and `matchup-matrix` both depend on. Lets those two parallelize.

## Inherited design decisions
- **Match-level W/L, not game-level**: `rounds.result` ("2-1") counts as one match win for the winner — the source is match-score aggregate, not per-game. (Inherited; see parent `## Design decisions`.)
- **Player-name is the only join key** between `rounds` and `decks`; normalize (trim/casefold/whitespace) and match within-tournament. Pairings that don't resolve to a labeled deck go to an `unmatched` coverage count, surfaced — never silently dropped (project error-handling convention: never drop a deck/pairing silently).
- **Byes / draws / forfeits dropped** from win-rate accumulation (empty player2, no-clear-winner result).
- **matchup-n is a different (smaller) population than metashare-n** — only rounds-bearing events contribute here (MTGO Leagues ship decklists only). Keep this aggregate strictly separate from deck-count aggregates.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — §4 (matchup computation from `Rounds`, the join, §4.4 name-join fragility + byes/draws), §4.3 (bimodal coverage), §3c (win-rate-weighted input).

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/matchup.py` (the rounds→labels join); the DuckDB `rounds` / `decks` schema; "matchup-n separate from metashare-n".

<!-- feature-design fills in: SQL/DuckDB query shapes, the result-string parser signature, name-normalization helper, the aggregate record types, and test approach. -->

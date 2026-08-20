---
source_handle: ddp-match-store
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Local tournament and match store

The local DuckDB contains the tables `tournaments`, `decks`, `deck_cards`, `rounds`, and `standings`. Read-only queries reported 2,681 tournaments, 68,593 deck rows, 81,777 round rows, and 52,116 standings rows; Legacy tournament dates range from 2023-12-31 through 2026-08-19.

## Key passages

- The exact current Dimir source registration has a matching deck row and seven tournament round rows, but no round row containing player `2plus2isfive`; its standing is rank 10 with 4 wins, 2 losses, 0 draws.
- The exact current Esper/Battlegrounds League source registration has a deck-level `5-0` result and zero standings or round rows.
- The exact current light green-white/wizardpasta source registration has a matching deck row and seven tournament round rows, but no round row containing `wizardpasta`; its standing is rank 17 with 3 wins, 3 losses, 0 draws.
- The exact current four-color/wakame League source registration has a deck-level `5-0` result and zero standings or round rows.
- The dated BUG/wakame League source registration has a deck-level `5-0` result and zero standings or round rows.
- The dated Grixis/nevilshute source registration has seven tournament round rows, two containing `nevilshute`; its standing is rank 1 with 7 wins, 1 loss, 0 draws.
- The tutor-turbo/clan League source registration has a deck-level `5-0` result and zero standings or round rows.
- The Wasteland/Murktide/HJ_Kaiser source registration has seven tournament round rows, one containing `HJ_Kaiser`; its standing is rank 7 with 4 wins, 3 losses, 0 draws.
- The round rows expose player handles and match result strings, but do not provide complete direct target-player match coverage for every registered list.
- Coverage objects must be separated: every named source above has a matching `decks` row and
  deck-level result; only current Dimir, wizardpasta, HJ_Kaiser, and nevilshute have matching
  standings. An event can have round rows without a direct row for the registered pilot. Queries
  join `decks.tournament_id` to `tournaments.id`, join standings on exact tournament/player, and
  count a direct round only when the exact pilot is `rounds.player1` or `rounds.player2`.

## Revisions

- 2026-08-20 — Distinguished deck-level League result fields from standings, event-level rounds,
  and direct target-player round rows. The prior wording could be read as claiming standings for
  League registrations that have none.

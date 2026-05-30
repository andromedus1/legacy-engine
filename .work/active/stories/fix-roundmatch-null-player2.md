---
id: fix-roundmatch-null-player2
kind: story
stage: done
tags: [bug, ingestion]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Fix: ingestion crashes on a bye's null Player2

## Brief
Discovered while seeding the real fbettega cache: `seed cache` crashed ingesting Legacy tournaments
because a **bye** carries an explicit `"Player2": null` in the JSON, and `RoundMatch.player2: str` (default
`""`) rejected it — a field default only applies when the key is *absent*, not when it's explicitly null.
Byes/forfeits and occasionally null `Result`/`Player` are legitimate data across the 15k-file corpus.

## Fix
`models/tournament.py`: added a `_none_to_empty` before-validator on the string fields of `RoundMatch`
(player1/player2/result), `Standing` (player), `Deck` (player/result), and `CardCount` (name) — coercing
an explicit JSON `null` to `""`. A bye becomes an empty opponent, which the match-results join already
drops from win-rate accumulation (no behavior change downstream). Regression tests in
`tests/test_cache_parser.py` (`test_bye_null_player2_coerced_to_empty`, `test_nested_bye_null_player2`).

## Outcome
`seed cache` ingested 2,449 Legacy tournaments / 63,150 decks cleanly. 580 tests green.

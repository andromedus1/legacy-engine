---
source_handle: ddp-playtest-protocol
fetched: 2026-08-20
source_path: decks/doomsday-variants/playtest-protocol.md
provenance: source-direct
substrate_confidence: source-direct
---

# Existing paired-playtest protocol

The protocol defines game rows, pre/post-board pairs, matches, and matchup blocks. It directs randomized play/draw and list-order assignment, fixed opponent list/version within a block, explicit sentinel values, and a 20-match stopping threshold.

## Key passages

- Experimental-unit section: a game is one CSV row; a match groups games by `match_id`; a matchup block pairs one candidate with the Dimir control under one opponent list/version.
- Registration/randomization section: list id/version and opponent list/version are recorded; play/draw and list order are balanced inside blocks.
- Mulligans/play/boarding section: final opening-hand size, mulligan count, keep/mulligan decision, combo turn, and board changes are recorded.
- Field-definitions section: `not_seen` and `not_applicable` are explicit states; splash mana, Wasteland, protection, and alternate-plan fields are separate.
- Stopping-rule section: the preregistered threshold is 20 completed matches per list; thin pilots stay descriptive and are not ranked.

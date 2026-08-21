---
source_handle: ddx-strategy-playtest-protocol
fetched: 2026-08-20
source_path: decks/doomsday-variants/playtest-protocol.md
provenance: source-direct
substrate_confidence: source-direct
---

# Paired-playtest contract

The protocol preregisters a descriptive paired comparison, including identity, randomization,
measurement, and stopping rules.

## Key passages

1. A matchup block pairs one candidate and the Dimir control against the same registered opponent
   list/version; pair IDs align play/draw, pilot/date, board state, and randomized list order.
2. Play/draw and candidate/control order must be balanced within each block. Published event
   finishes cannot be entered as playtest rows.
3. The stopping threshold is 20 completed matches per list. Thin samples remain descriptive and
   emit no ranking.
4. The log separates pre/post-board state, mulligans, actual combo turn, splash-mana effects,
   Wasteland exposure, protection relevance, and alternate-plan deployment/outcome.

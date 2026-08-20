# Doomsday variant paired-playtest protocol

This is a preregistered descriptive comparison of the 15 lists in
[manifest.json](manifest.json). The manifest is the only list-id authority. Published finishes
and source dates are evidence posture, not playtest outcomes.

## Experimental units

- A **game** is one CSV row. `list_id`, `list_version`, opponent list/version, board state,
  play/draw, and list order identify the tested configuration.
- A **pre/post-board pair** is represented by the same `match_id` with `board_state` set to
  `pre` or `post`; pre-board rows use `not_applicable` for boarding and alternate-plan fields.
- A **match** is the games sharing a `match_id`. Record `match_result` on the completed match
  row and `not_seen` on earlier or unfinished rows.
- A **matchup block** holds one candidate and the Dimir control against the same
  `opponent_archetype` and `opponent_list_version`. `pair_id` links one candidate game to the
  corresponding control game.

The distributed log is game-level so opening decisions, actual combo turns, splash-mana effects,
Wasteland exposure, boarding, protection relevance, and alternate-plan outcomes cannot be merged
into a single headline number.

## Registration and randomization

Before a block begins, copy the candidate `list_id`, `list_version`, and manifest hash into the
session notes. A changed deck hash starts a new list version; do not overwrite old rows. Register
the opponent list/version as well. Randomize which list is played first and randomize play/draw
within each block, then keep the assignments fixed for that block. Balance both dimensions so each
arm has no more than one extra play or draw and no more than one extra first/second list position.

Use a fresh `pilot_id`/`played_on` value for each pilot session. Do not use published event results
as rows in this log.

## Mulligans, play, and boarding

Use the London mulligan and record the final opening-hand size, number of mulligans, and the
keep/mulligan decision. Record `combo_turn` only when the primary Doomsday win actually occurred;
otherwise use `not_seen`. A value is a turn number, not a turn estimate or intended goldfish clock.

Play the pre-board game(s) before sideboarding. For post-board games, record cards as
`<count> <card>` entries separated by semicolons (for example, `2 Veil of Summer;1 Carpet of
Flowers`). Use `not_seen` when a board change was not observed and `not_applicable` only before
boarding.

## Field definitions and conditional states

Every cell is required. Use `not_seen` when the game ended before a signal could be observed and
`not_applicable` when the signal cannot apply. Do not leave cells empty.

- `splash_mana_effect` is `helped`, `hurt`, `neutral`, or a sentinel; if it is a real effect,
  record `splash_color_failure` as `yes`, `no`, or `not_seen`.
- `wasteland_punished` is meaningful only when `wasteland_exposed=yes`.
- `protection_live` and `protection_relevant` are meaningful only when
  `protection_present=yes`; relevance asks whether it matched the interaction actually presented,
  not merely whether the card was held.
- `alternate_plan=yes` means the alternate threat/line was deployed or attempted. Its result is
  `win`, `loss`, or `not_seen`; otherwise its result is `not_applicable`.

## Stopping rule and interpretation

The preregistered stopping threshold is **20 completed matches per list**, with pre/post-board
games and balanced paired blocks. A thin pilot may be stopped earlier for time or card-availability
reasons, but the validator labels it `thin-sample` and the summarizer emits no ranking. Results are
descriptive: denominators, game/match wins, keep rate, combo-turn observations, and paired deltas
remain visible. No list is promoted to an interchangeable-sideboard series from this pilot alone.

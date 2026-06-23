---
id: idea-sb-maindeck-aware-coverage
created: 2026-06-15
tags: [advisory, sideboard]
---

Sideboard recommender: discount coverage the **maindeck already provides** before scoring SB hosers.

The coverage model in `advisory/sideboard.py` weights candidate hosers by `field_share × swing` per
opponent vulnerability tag, but it does NOT subtract the answers the *maindeck* already supplies to
the same axis. Found in a dogfooding test-drive: the deck runs **4 Wasteland maindeck** (covering the
anti-big-mana-land / ramp axis), yet the SB still recommended **Ghost Quarter** for
"ramp/greedy-manabase" coverage — redundant land destruction, and Ghost Quarter is a strictly worse
Wasteland (ramps the opponent, no tempo). The solver double-counts an axis the maindeck already
addresses.

Fix direction: before scoring SB hosers, discount each vulnerability tag's weight by the coverage the
maindeck already provides to that tag. The recommender is already "maindeck-aware" via
`matchup_pressure` for per-card value, but the coverage-ELEMENT weighting ignores maindeck answers.
Net effect: stop recommending SB cards redundant with what the deck already runs. Relates to
epic-sideboard-core-and-hedge (scope under/alongside it later).

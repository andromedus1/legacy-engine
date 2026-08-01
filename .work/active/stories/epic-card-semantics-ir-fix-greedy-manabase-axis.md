---
id: epic-card-semantics-ir-fix-greedy-manabase-axis
kind: story
stage: implementing
tags: [advisory, bug]
parent: epic-card-semantics-ir
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-31
---

# Fix greedy-manabase axis category error (attack vs protection: FoV/Krosan Grip)


# `greedy-manabase` conflates "attacks manabases" with "protects MY manabase" (FoV/Krosan Grip)

Found by independent review (2026-07-03). `whattoplay.py` derives `greedy-manabase` as a
VULNERABILITY (this archetype has a fragile nonbasic/fast-mana manabase → vulnerable to mana
denial). Wasteland/Blood Moon correctly ATTACK that axis. But Force of Vigor and Krosan Grip carry
`attacks: ["greedy-manabase"]` with comments saying they "answer Blood Moon / Back to Basics /
Chalice" — that's PROTECTING my own greedy manabase (a `_hate`-shaped protective role), not
attacking the opponent's. `_derive_attacks_for_promoted` rule 6 duplicates the error ("destroy
target artifact/enchantment" → greedy-manabase). Partially defensible only for artifact fast-mana
(Mox-heavy) decks.

Fix: split the axis (e.g. `artifact-mana-reliant` vs `nonbasic-manabase` as attack targets) and move
FoV/Grip's anti-hate rationale to the protection model. Relates to
[[idea-hate-coverability-overvalues-defense-grid]] (protection semantics) and
[[idea-card-semantics-rules-layer]].

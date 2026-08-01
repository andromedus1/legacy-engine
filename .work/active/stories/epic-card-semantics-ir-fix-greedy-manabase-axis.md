---
id: epic-card-semantics-ir-fix-greedy-manabase-axis
kind: story
stage: done
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

## Implementation notes

**Full migration** (not the union-alias fallback). `greedy-manabase` is retired everywhere in
`src/` and `tests/`; no deprecated alias is emitted. Real change stayed well under the ~300 LoC
fallback trigger — the bulk of the churn was mechanical literal renames in tests.

**Vocabulary split.** The single manabase axis became two independent tags, separated by which
hoser can physically reach them:
- `nonbasic-manabase` — LAND-side fragility. Fires on `nonbasic_land_count >=
  _NONBASIC_MANABASE_MIN_COUNT` (8) OR `land_manabase_fast_count >= _NONBASIC_MANABASE_MIN_LAND`
  (4), where the latter counts `mana_base_tags & {dual, fast_mana_land, fetchland}`. Reached by
  Wasteland ("Destroy target nonbasic land"), Blood Moon ("Nonbasic lands are Mountains"), Back
  to Basics ("Nonbasic lands don't untap during their controllers' untap steps").
- `artifact-mana-reliant` — nonland ARTIFACT fast-mana fragility. Fires on
  `artifact_fast_mana_count >= _ARTIFACT_MANA_RELIANT_MIN` (4), counting the `fast_mana`
  card role. Reached by Null Rod ("Activated abilities of artifacts can't be activated"),
  Force of Vigor, Krosan Grip, Engineered Explosives.

The tags are independent: a dual-heavy Delver deck is `nonbasic-manabase` only; an
artifact-accelerated dual-base shell carries both. Tests pin all four quadrants.

**Combo tag held invariant.** The pre-split `fast_mana_cards` counter fed both the manabase tag
and combo's "broken signal" leg. Splitting it would have silently changed `combo` emission, so
the combo leg now sums both counters against the new `_COMBO_FAST_MANA_MIN` (4) — byte-identical
to prior behavior. This is deliberate: combo cares that the deck accelerates, not which half.

**Category error corrected.** Force of Vigor and Krosan Grip lost the manabase-attack claim.
Verbatim oracle text (queried from `data/legacy.duckdb`, not recalled):
- Force of Vigor: "Destroy up to two target artifacts and/or enchantments."
- Krosan Grip: "Destroy target artifact or enchantment."
Neither can target a land, so neither attacks `nonbasic-manabase`. Both legitimately attack
`artifact-mana-reliant`. Their value against an opposing Blood Moon / Back to Basics is
PROTECTION of the caster's own manabase — a relation the `attacks` vocabulary does not express.
Left unmodeled on purpose and noted in each `_comment`; the protection model is parent-epic work.

Also corrected: Null Rod `greedy-manabase` -> `artifact-mana-reliant` (kept `ramp`); Engineered
Explosives likewise (its "Destroy each NONLAND permanent ..." cannot hit lands).

**Derivation rules.** `_derive_attacks_for_promoted` rule 3b (land destruction) ->
`nonbasic-manabase`; rule 6 (artifact/enchantment removal) -> `artifact-mana-reliant`.
Rule 6 no longer claims the land axis. Docstring priority list updated.

**Closed-vocabulary guard added.** `load_hoser_catalog` now validates `attacks` against a
module-level `_VALID_ATTACK_TAGS` frozenset, raising `ValueError` naming the offending tag and
the sorted allowed set (the project's closed-vocabulary-fail-fast-token pattern, matching
`_VALID_SYMMETRY` / `_VALID_CAST_REQUIRES`). The story anticipated extending an existing check
in `catalog_lint.py`, but that module has no `attacks` validation at all — the loader is the
correct chokepoint since it is the single path curated JSON enters the system. A regression test
pins that the retired `greedy-manabase` literal is now rejected at load time.

## Implementation discovery

**Latent case-sensitivity bug in artifact fast-mana detection (NOT fixed — out of scope).**
`_card_roles` (whattoplay.py ~152-156) matches artifact fast mana with
`re.search(r"add \{[cC]\}\{[cC]\}|add \{[wubrgWUBRG]\}", text)` where `text = card.oracle_text
or ""` is NOT lowercased and the regex carries no `re.IGNORECASE`. Real oracle text capitalizes
the word ("{T}: Add {U}."), so this branch never matches production data — artifact fast mana is
detected ONLY via the `staple_role == "fast_mana"` curated list (Chrome Mox, Lotus Petal, Lion's
Eye Diamond, plus the lands Ancient Tomb / City of Traitors, which route through `mana_base_tags`
instead). Consequence: `artifact-mana-reliant` currently under-fires on decks whose artifact
acceleration is not in that curated list (Mox Diamond, Mox Opal, Grim Monolith). Fixing the regex
would change `fast_mana` role membership and therefore ALSO `combo` emission and the proactivity
score, so it is a separate calibrated change, not a drive-by. The new tests use Lotus Petal
(curated) so they pin real behavior rather than the dead regex branch.

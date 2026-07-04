---
id: gate-tests-catalog-blast-rows
kind: story
stage: done
tags: [testing]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: tests
created: 2026-07-04
updated: 2026-07-04
---

# Shipped catalog blast rows not directly asserted

## Priority
Medium

## Spec reference
Item: `feature-sb-effect-tagging-model` (Unit 3). ACs: blasts attack plays-red/plays-blue; Hydroblast+BEB share functional_group 'red-blast'.

## Gap type
AC covered only indirectly — a catalog edit regressing Pyroblast/REB (no end-to-end blue test) would pass.

## Suggested test
One shipped-data test asserting the four blast rows' attacks + paired functional_group literals from HOSER_CATALOG.

## Test location
`tests/test_sideboard.py` (alongside test_all_entries_have_nonempty_attacks)

## Resolution
Added 5 tests to `TestHoserCatalog` asserting the shipped literals directly from `HOSER_CATALOG`
(`src/legacy_engine/data/hosers/legacy.json`): `test_pyroblast_attacks_plays_blue`,
`test_red_elemental_blast_attacks_plays_blue`, `test_hydroblast_attacks_plays_red`,
`test_blue_elemental_blast_attacks_plays_red` (each asserting both the `attacks` tag and its
`functional_group`), plus `test_blast_pairs_share_functional_group` pinning the two functionally-
identical pairs (Hydroblast/Blue Elemental Blast -> "red-blast"; Pyroblast/Red Elemental Blast ->
"blue-blast"). Full suite green.

---
id: gate-tests-catalog-blast-rows
kind: story
stage: drafting
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

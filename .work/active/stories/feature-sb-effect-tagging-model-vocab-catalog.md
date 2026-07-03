---
id: feature-sb-effect-tagging-model-vocab-catalog
kind: story
stage: implementing
tags: [advisory]
parent: feature-sb-effect-tagging-model
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Vocabulary replace + HoserCard model + catalog rewrite + wire into current tool

## Brief

The atomic vocabulary migration + the shippable quick-fix. Replace the monolithic
`graveyard-reliant` tag with `graveyard-recursion` / `graveyard-fuel`, add color-contingent
`plays-<color>` tags, extend `HoserCard` with `symmetry` / `cast_requires` / `functional_group`,
rewrite the hoser catalog (re-tag graveyard cards, fix the mis-tagged Hydroblast/Pyroblast blasts,
add Blue/Red Elemental Blast, add symmetry, mark functional groups), and wire the fixes + a
`functional_group` de-dup into the current `advise sideboard` matcher. These MUST ship together —
a half-migrated vocabulary breaks matching on main.

## Implementation

Covers parent feature units **1, 2, 3, 5** — see
`feature-sb-effect-tagging-model` § Implementation Units for exact signatures, files, and
acceptance criteria. Files: `advisory/whattoplay.py`, `advisory/sideboard.py`,
`data/hosers/legacy.json`; tests in `tests/test_whattoplay.py`, `tests/test_sideboard.py`,
`tests/test_recommendation_coverage.py`.

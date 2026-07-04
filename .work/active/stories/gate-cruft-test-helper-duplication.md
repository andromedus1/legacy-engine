---
id: gate-cruft-test-helper-duplication
kind: story
stage: drafting
tags: [cleanup]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: cruft
created: 2026-07-04
updated: 2026-07-04
---

# Promote duplicated _con/_make_field/_make_card test helpers to conftest fixtures

## Confidence
Medium

## Category
Duplicated logic (violates pytest-factory-fixtures pattern)

## Locations
`_con()` byte-identical in tests/test_sideboard.py:76 + tests/test_whattoplay.py:42 ·
`_make_field()` identical in test_sideboard.py:83 + test_whattoplay.py:67 ·
`_make_card()` in test_whattoplay.py:49 + test_linchpins.py:33

## Removal
Promote to tests/conftest.py factory fixtures per .agents/skills/patterns/pytest-factory-fixtures.md
(conftest already carries make_hoser/make_linchpin/etc.); delete per-file copies. Verify signatures
match before consolidating. Surgical — no behavior change.

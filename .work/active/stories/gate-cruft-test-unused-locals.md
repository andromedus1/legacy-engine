---
id: gate-cruft-test-unused-locals
kind: story
stage: implementing
tags: [cleanup]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: cruft
created: 2026-07-04
updated: 2026-07-04
---

# Remove 5 unused locals (F841) in test files; verify one lost assertion

## Confidence
High

## Category
Dead code — unused locals

## Locations (ruff --select F841)
tests/test_sideboard.py:5712,5747,5812 dead `con = _con()` · tests/test_sideboard.py:6425 `pool_names` ·
tests/test_whattoplay.py:175 `exhume = _make_card(...)` in test_exhume_has_graveyard_recursion

## Removal
Drop the three dead con setups + pool_names. For `exhume`: the card is built but never asserted —
the test likely LOST its assertion; check intent and either restore
`assert 'graveyard_recursion' in _card_roles(exhume)`-style verification or remove the dead builder.
This one may be a real coverage hole, not just cruft.

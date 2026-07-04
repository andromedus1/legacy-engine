---
id: gate-cruft-test-unused-locals
kind: story
stage: done
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

## Resolution
- `tests/test_sideboard.py` three dead `con = _con()` (in `test_dimir_tempo_field_surfaces_gy_hate`,
  `..._combo_hate`, `..._creature_removal`) — removed; each test builds the coverage model by hand
  and never used `con`.
- `tests/test_sideboard.py` `pool_names` in `test_considering_pool_includes_not_selected_cards` —
  RESTORED an assertion instead of deleting: the test's own name promises "includes not selected
  cards" and the line right after computing `pool_names` already commented "H_A and H_B were not
  selected and have residual coverage value", but nothing actually checked they were in the pool.
  Added `assert {"H_A", "H_B"} <= pool_names`.
- `tests/test_whattoplay.py:175 exhume` — **investigated and confirmed a REAL production gap, not
  just cruft.** Ran `_card_roles()` directly against the actual Exhume oracle text ("Each player
  puts a creature card from THEIR graveyard onto the battlefield.") and it returns an EMPTY set —
  `_RE_GRAVEYARD`'s third alternative only matches `from (?:a|any|your) graveyard ... onto the
  battlefield`, and does not recognize "their graveyard" (Exhume's symmetric "each player"
  template). The test's own name (`test_exhume_has_graveyard_recursion`) and the abandoned `exhume`
  local prove the original intent was to assert this directly against Exhume, but the developer
  hit the regex mismatch and silently substituted a different card (Animate Dead) instead of fixing
  the regex or flagging the gap. Restored the intended assertion on `exhume` itself, marked
  `@pytest.mark.xfail(strict=True, reason=...)` documenting the regex gap by name, and split the
  passing Animate Dead check into its own `test_animate_dead_has_graveyard_recursion` so it keeps
  running unconditionally. Per batch scope, the regex itself was NOT fixed (only the two authorized
  sideboard.py docstring sentences are in-scope for src changes this drain) — flagging here for a
  future story: `_RE_GRAVEYARD` should recognize "their graveyard" for symmetric reanimation
  templates (Exhume and similar).

Full suite green; the xfail is intentional and expected (not a failure).

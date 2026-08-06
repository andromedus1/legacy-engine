---
id: gate-tests-stale-xfail-docstring
created: 2026-08-05
updated: 2026-08-05
tags: [testing, documentation]
---

`tests/test_whattoplay.py:169` documents a sibling test as xfailing that does not xfail.

The docstring on `test_animate_dead_has_graveyard_recursion` says it is "kept as the passing
sibling of test_exhume_has_graveyard_recursion above, **which xfails** on the symmetric 'their
graveyard' phrasing gap."

`test_exhume_has_graveyard_recursion` (line 157) carries **no xfail marker** and passes —
`tests/test_whattoplay.py` reports `118 passed`, and the full suite reports zero xfailed. So
`_RE_GRAVEYARD` now recognizes the symmetric "their graveyard" phrasing that the v0.2.0 gate
originally xfailed as `bug-re-graveyard-their-template`.

Two things to reconcile:

1. The docstring asserts a suite state that is false — it will mislead the next reader of that
   file into thinking a known gap is still open.
2. `epic-card-semantics-ir-fix-graveyard-regex` is still tracked as open work under
   `epic-card-semantics-ir`. If the regex gap is genuinely closed, that story should be verified
   and closed rather than left as a phantom obligation; if it is only *partly* closed, the
   docstring should say which half.

Found by the v0.4.0 gate-tests integrity pass. Low priority, ambient — no coverage is missing,
the defect is a lying comment plus possibly-obsolete tracked work.

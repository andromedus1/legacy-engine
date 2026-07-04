---
id: gate-cruft-test-helper-duplication
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

## Resolution
Design decision (this story was left "drafting; design inline"): promoted `_con`, `_make_field`,
`_make_card` into `tests/conftest.py` as plain **functions**, not `@pytest.fixture`-decorated
closures, deliberately deviating from the pytest-factory-fixtures pattern's usual shape for this
one case — documented inline in conftest.py with the rationale:

- All three are called **directly as bare functions** (`_con()`, `_make_field({...})`,
  `_make_card(**kw)`) well over 200 times combined across test_sideboard.py (19 + 138) and
  test_whattoplay.py (28 + 23 + 49), including from inside `@staticmethod` corpus-builder helpers
  (e.g. `TestRedundancyDecay._gy_field_corpus`, `TestHedgeIntegrationNonVacuous._two_tag_corpus`)
  that pytest never collects as test items — such methods cannot receive injected fixtures at all
  (pytest fixtures are non-callable outside DI; calling a `@pytest.fixture`-decorated function
  directly raises at runtime).
- True fixture-DI conversion would require adding a fixture parameter to every one of those 200+
  call sites AND restructuring every static corpus-builder to accept/thread the fixture down from
  its caller — a large, invasive rewrite that is the opposite of "surgical, zero behavior change"
  and carries real risk of silently altering test behavior at this file's scale.
- Precedent already exists in this codebase for importing a plain conftest.py helper directly:
  `assert_renders` (conftest.py) is imported via `from tests.conftest import assert_renders` in
  test_viz_render.py/test_viz_specs.py/test_viz_tiles.py.

Implementation: added `_con`/`_make_field`/`_make_card` to conftest.py (signatures byte-identical
to the removed per-file copies), deleted the three per-file duplicate definitions, and added
`from tests.conftest import ...` in test_sideboard.py, test_whattoplay.py, test_linchpins.py. No
call site changed. Also removed now-dead `build_custom_field`/`FieldDistribution` (test_whattoplay)
and `Card` (test_linchpins) module imports that were only used inside the now-removed local
definitions — verified via ruff these weren't needed elsewhere.

Verification: ruff `--select F401,F811,F841` clean on all 6 batch-B files; full suite
`.venv/bin/python -m pytest -q` → **2578 passed, 1 xfailed** (the intentional Exhume xfail from
gate-cruft-test-unused-locals) — at/above the 2565 floor plus this batch's additions, zero
regressions from the conftest promotion.

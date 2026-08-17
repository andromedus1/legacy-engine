---
id: story-fix-manual-refresh-import-path
kind: story
stage: review
created: 2026-08-16
updated: 2026-08-16
tags: [bug, ops]
parent: null
depends_on: []
release_binding: null
gate_origin: null
---

# Make the documented manual decision refresh executable directly

## Brief

The documented one-command manual refresh, `.venv/bin/python scripts/refresh_decision_data.py`,
successfully refreshes sources, card coverage, labels, camps, and eras but fails at the final ranking
step with `No module named 'scripts'` unless the repository root is supplied through `PYTHONPATH`.
The last-good HTML is preserved and running the ranking generator with `PYTHONPATH=.` succeeds.

## Simplification opportunity

Make the documented direct script entry point establish one consistent repository import context;
do not require operators to know or supply an undocumented environment override.

## Symptom

The live composed refresh completed sources, card coverage, labeling, staged camps, and eras, then
failed its protected final ranking step with `No module named 'scripts'`. Running the ranking
generator with `PYTHONPATH=.` succeeded.

## Root cause

Direct Python script execution puts the `scripts/` directory—not the repository root—at
`sys.path[0]`. The workflow's ranking port imports `scripts.refresh_best_call_ranking` lazily, so the
documented entry point could import the installed `legacy_engine` package but could not resolve its
sibling `scripts` namespace.

## Fix approach

`scripts/refresh_decision_data.py` now inserts its resolved repository root once before loading
workflow modules. Project imports remain lazy inside the adapter/main functions, preserving clean
module-level lint and the existing test injection surface.

## Regression test

`tests/test_refresh_decision_script.py::test_direct_script_establishes_repository_import_root`
executes the script module from an unrelated working directory with `PYTHONPATH` removed, verifies
the root is established, and imports the exact ranking module that failed in production.

## Implementation notes

- **Execution capability:** focused inline bug fix; the failure was reproducible and isolated to one
  script boundary, so no feature-scale design or independent review was warranted.
- **Files changed:** `scripts/refresh_decision_data.py`, `tests/test_refresh_decision_script.py`.
- **Confirmation:** the regression failed before the patch and now passes; both script tests pass;
  changed-file Ruff passes; the exact documented refresh command completes all six steps and rewrites
  the ranking; the full repository passes `3,983 passed, 1 skipped`.
- **Adjacent issues:** none bundled. The unreadable cached Standard event remains an explicit
  non-Legacy skip, and low ranking groundedness remains an honest data/support state.

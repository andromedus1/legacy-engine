---
id: idea-local-ci-python-drift
created: 2026-08-05
updated: 2026-08-05
tags: [ci, tooling, tests]
---

The local `.venv` has drifted ahead of CI and the project declares no upper bound, so the local
suite and CI now disagree about what "green" means. `pyproject.toml` says only
`requires-python = ">=3.11"`; CI pins `python-version: '3.13'`; the working `.venv` is now
**Python 3.14 with NumPy 2.5**.

Two concrete costs observed 2026-08-05:

1. **The optional `discovery` extra is unusable locally.** `umap-learn` → `numba`, and numba
   raises `ImportError: Numba needs NumPy 2.4 or less. Got NumPy 2.5.` Worse, `pytest.importorskip`
   no longer masks this: since pytest 8.2 it re-raises an `ImportError` that comes from a
   *different* module than the one requested, so `test_umap_smoke` **hard-failed** rather than
   skipping. A fresh clone on a current interpreter got a red suite over an optional dependency.
   (Fixed in the public-repo hygiene PR — the test now skips on any `ImportError` and names the
   reason — but the underlying version drift is untouched.)

2. **11 tests fail locally on `main` while `main`'s CI is green.**
   `tests/test_cli_superarchetype.py` (9) and `tests/test_sideboard.py::TestPlanMatchupsRealSwap`
   (2). Example: `assert plan.degraded is False` → `AssertionError: assert True is False`. These
   reproduce on unmodified `main` in a clean worktree, so they are not caused by any local edit.
   They pass on the in-flight feature branch, so they may simply be fixed there — but the fact that
   local and CI disagree at all on the same commit is the problem, because it destroys the local
   suite's value as a pre-push signal. This is the mirror image of the tracked
   green-local/red-CI trap.

Not yet diagnosed: whether (2) is interpreter/NumPy-version sensitivity, a PuLP/CBC solver
difference across versions, or a hidden dependency on the default DuckDB (which was refreshed
today). Worth resolving *before* trusting either signal — a suite that's red locally for
unexplained reasons trains everyone to ignore it.

Wanted, roughly:
- Declare the supported range honestly in `pyproject.toml` (an upper bound, or a documented
  "tested on" statement) instead of an open `>=3.11`.
- Add the interpreter the maintainer actually develops on to the CI matrix, so drift surfaces in
  CI rather than only on the dev machine.
- Root-cause the 11 divergent tests and either fix them or pin what they depend on.
- Note the optional-extra reality in `CONTRIBUTING.md` (already partly written up there: the
  discovery extra lags new Python/NumPy releases).

This matters more now that the repo is public and expecting outside contributors — a newcomer
following `CONTRIBUTING.md` on a current Python gets failures that have nothing to do with their
change.

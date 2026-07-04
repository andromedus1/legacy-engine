---
id: gate-cruft-test-unused-imports
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

# Remove 17 unused imports (F401) across bundle test files

## Confidence
High

## Category
Dead code — unused imports

## Locations (ruff 0.12.0, --select F401)
tests/advisory/test_compare.py:199 duckdb · tests/test_backtest.py:16 _TOP_FINISHER_QUANTILE ·
tests/test_cli.py:268,292 os ·
tests/test_sideboard.py:67 build_adaptive_matrix, :843 _COVERAGE_P, :1965 _VALUE_GATE, :3004,3046 sideboard, :3085 archetype_valid_since, :5324,5349 Path ·
tests/test_whattoplay.py:13 BestDeckCall, :15 _archetype_composition, :21 _GY_FUEL_DENSITY, :22 _GY_RECURSION_DENSITY, :1734 DISPLAY_GATE_N

## Removal
Delete each unused name from its import (ruff --fix-safe). CAUTION: the internal constants
(_TOP_FINISHER_QUANTILE, _COVERAGE_P, _VALUE_GATE, _GY_FUEL_DENSITY, _GY_RECURSION_DENSITY,
DISPLAY_GATE_N) look like leftovers from reshaped tests — verify no intended assertion was dropped
before removing (if a threshold assertion was clearly intended, restore it instead).

## Resolution
(batch B scope only — tests/advisory/test_compare.py:199 and tests/test_cli.py:268,292 belong to
batch A, already resolved separately.)

- `tests/test_backtest.py:16 _TOP_FINISHER_QUANTILE` — RESTORED an assertion instead of deleting:
  the docstring already asserts `ceil(0.25*8)=2` in prose; added
  `assert math.ceil(_TOP_FINISHER_QUANTILE * 8) == 2` right before the existing
  `n_winning_decks == 4` check so a future retune of the constant fails loudly instead of
  silently invalidating the fixture's math.
- `tests/test_sideboard.py:67 build_adaptive_matrix` — genuinely unused (only named in a
  docstring); removed from the import.
- `tests/test_sideboard.py:843 _COVERAGE_P` (local shadow import) — removed; the outer
  module-level import (still used by `TestSaturatingCoverageModel`) is unaffected.
- `tests/test_sideboard.py:1965 _VALUE_GATE` — removed (also fixed the co-located
  `_build_coverage_model` F811 dup, tracked separately by gate-cruft-test-dup-import).
- `tests/test_sideboard.py:3004,3046 sideboard` (`import ... as _sb_mod`, unused in those two
  test bodies) — removed both.
- `tests/test_sideboard.py:3085 archetype_valid_since` (aliased `_avs_real`, unused) — removed;
  the file's OTHER `_sb_mod`/`_aff_mod` monkeypatch imports in the same test are used and kept.
- `tests/test_sideboard.py:5324,5349 Path` — removed (both tests use `f.name`, never `Path`).
- `tests/test_whattoplay.py:13 BestDeckCall` — RESTORED an assertion instead of deleting: added
  `assert isinstance(result, BestDeckCall)` to `test_result_has_expected_fields`, matching its
  own docstring ("BestDeckCall carries archetype, label, variance, means") which the prior
  assertions never actually checked.
- `tests/test_whattoplay.py:15 _archetype_composition` — removed; the function is exercised
  indirectly via its caller elsewhere in whattoplay.py, no dropped assertion found.
- `tests/test_whattoplay.py:21,22 _GY_FUEL_DENSITY, _GY_RECURSION_DENSITY` — removed; no
  boundary-value test referencing these constants existed or was evidently dropped.
- `tests/test_whattoplay.py:1734 DISPLAY_GATE_N` — RESTORED an assertion instead of deleting:
  added `assert DISPLAY_GATE_N == 30` pinning the value the test's own `n<30`/`n>=30` comments
  and fixture literals assume.

Ruff (`--select F401,F811,F841`) is clean on all 6 batch-B files after these changes. Full suite
green.

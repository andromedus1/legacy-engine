---
id: gate-cruft-test-unused-imports
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

---
id: feature-sb-board-backtest-compute
kind: story
stage: implementing
tags: [advisory, analytics]
parent: feature-sb-board-backtest
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Backtest recommended boards vs top-finisher boards + CLI

## Brief

New `advisory/backtest.py`: pull top-finisher decklists of an archetype in a window, extract their
sideboards + inclusion%, run `recommend_sideboard` for the same archetype+field, and diff
(overlap / scorer-only / winners-only), gated by winner-sample confidence. New `advise backtest`
CLI leaf renders it with the honest "divergence is a signal, not proof" caveat. The empirical
anchor for the whole scoring model — measures *resemblance to what wins*, never a pass/fail verdict.

## Implementation

Covers parent feature **Units E1 + E2** — see `feature-sb-board-backtest` § Implementation Units for
`BoardBacktest`, `backtest_board`, the `_TOP_FINISHER_QUANTILE`/`_OBSERVED_THRESHOLD` constants, and
acceptance criteria. Files: new `src/legacy_engine/advisory/backtest.py` + `src/legacy_engine/cli.py`;
tests in new `tests/test_backtest.py` (hermetic file-backed tmp DuckDB) + a CLI test with tmp `--db`.

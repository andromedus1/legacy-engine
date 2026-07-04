---
id: feature-archetype-sweep-backtest-copy-surfaces
kind: story
stage: done
tags: [advisory, analytics]
parent: feature-archetype-sweep-backtest
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# Copy-count + solver pass-through surfaces on the backtest

## Brief

Gated-additive extension of `BoardBacktest`: `recommended_counts` (solver card→copies, currently
flattened away), `observed_copy_distribution` (card → copies → n_decks among top-finisher boards,
dupe rows summed per deck), and a `solver` pass-through kwarg on `backtest_board`. Defaults keep
every existing caller/test byte-identical. This is the data dimension the copy-count
tipping-point study (idea-copy-count-tipping-point) needs.

## Implementation

Parent feature `## Implementation Units` → **Unit 2**. Hermetic-DB tests per
file-backed-cli-test-db-builder; existing backtest tests stay untouched-green.

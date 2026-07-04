---
id: feature-archetype-sweep-backtest-sweep-module
kind: story
stage: done
tags: [advisory, analytics]
parent: feature-archetype-sweep-backtest
depends_on: [feature-archetype-sweep-backtest-ilp-determinism, feature-archetype-sweep-backtest-copy-surfaces]
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# Sweep module + CLI — batch driver, clustering/ranking, `advise sweep`

## Brief

New `advisory/sweep.py`: `enumerate_archetypes` (≥ min-decks, excludes Unknown/NULL) +
`run_sweep` looping `backtest_board` over one shared field, with PURE `cluster_divergences`
(tag-based via injected `attacks_lookup`; per-direction; `unclassified` is first-class) and
`rank_clusters` (`(-n_archetypes_nonspeculative, -total_adoption, …)` — label thin tiers, never
blend). CLI leaf `advise sweep` with audit-echo report, substrate-ready finding bullets, the
divergence caveat, and `--json` payload (incl. copy histograms + solver counts) for the
distribution study.

## Implementation

Parent feature `## Implementation Units` → **Units 3 + 4** (always ship together).
Divergence stays diagnostic — never an empirical prior in scores.

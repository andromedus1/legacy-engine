---
id: feature-ranking-future-only-benchmark-protocol-snapshot
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: feature-ranking-future-only-benchmark
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Preregistered protocol and leakage-safe origin snapshot

## Brief

Define the frozen benchmark protocol and whole-event-date walk-forward folds, then build an
auditable cutoff-safe corpus snapshot that recomputes eras and excludes future taxonomy, B&R,
player, card, and outcome state.

## Implementation

Implement Unit 1 in the parent feature's `## Implementation Units` section. This is the trickiest
unit and must prove the leakage boundary before predictions or scores are allowed to exist.

## Implementation notes

- Execution capability: inherited frontier model at high effort; this checkpoint owns the
  statistically load-bearing temporal boundary and cross-module DuckDB/era integration.
- Review weight: standard, inherited from the active autopilot run; child stories do not receive
  an independent review.
- Files changed: `advisory/ranking_benchmark.py`, `workflows/ranking_benchmark.py`,
  `analytics/affectedness.py`, and focused benchmark/snapshot tests.
- Tests added: protocol registry validation; whole-date/B&R fold truncation/reset; adversarial twin
  snapshots that differ only after cutoff; exclusion of future tournaments, variants, player
  aliases, card rows, and superarchetype state; and fail-closed future taxonomy manifests.
- Simplification: the snapshot copies only the five raw tournament fact tables plus referenced card
  rows, clears variants, and recomputes eras. It deliberately does not copy or sanitize arbitrary
  derived tables after the fact.
- Discrepancies from design: the existing `run_eras` seam already accepted an injected ban ledger,
  so only `archetype_valid_since` required the matching optional override. The snapshot manifest is
  returned to the caller rather than stored inside DuckDB; the artifact writer owns persistence in
  the next checkpoint.
- Adjacent issues parked: none.
- Verification: 37 focused protocol/snapshot/era tests passed in 4.24s; Python compilation passed.

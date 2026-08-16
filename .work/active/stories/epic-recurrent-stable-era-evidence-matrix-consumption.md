---
id: epic-recurrent-stable-era-evidence-matrix-consumption
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-interval-consumption
depends_on: [epic-recurrent-stable-era-evidence-view-decomposition]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Adaptive matrix and ranking-ledger interval consumption

## Brief

Implement Unit 4 from the parent feature: route adaptive and multi-split matrices through the shared
interval authority, project current-only compatibility, and carry typed expanded/added diagnostics,
both clocks, complete provenance, concentration, and abstention into ranking measurement.

## Implementation

See `epic-recurrent-stable-era-evidence-interval-consumption` Unit 4 for exact interfaces, decisions,
notes, and acceptance criteria. Current-only remains ranking-authoritative in this feature; expanded
raw support cannot clear existing measurement gates. Camps stay current-only and disjoint sets never
collapse to an earliest-start scalar.

## Acceptance

- Scalar no-certificate matrices and ranking rows retain golden values through the interval adapter.
- Parent expansion preserves gaps/provenance across plain, split, multi-split, and ranking replay.
- Camps do not expand, diagnostic support cannot promote authority, and disjoint sets refuse scalar
  projection.

## Tests

Run focused integration, matchup parity, and ranking replay tests, all era/matchup suites, Ruff on
touched files, and compileall as specified by the parent feature.

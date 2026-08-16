---
id: epic-recurrent-stable-era-evidence-discovery-firewall-corpus
kind: story
stage: implementing
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-discovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Outcome-free discovery corpus and cutoff boundary

## Brief

Implement Unit 1 from the parent feature: the frozen extra-forbidden discovery models, checked-in
versioned calibration, and the batched cutoff adapter that projects parent deck construction,
source, event, pilot, legality, and taxonomy facts without making any outcome-bearing relation or
field available to the discovery core.

## Implementation

See `epic-recurrent-stable-era-evidence-discovery` Unit 1 and its acceptance criteria.

Review weight remains `standard` at the parent feature boundary.

## Implementation notes

- Execution capability: delegated standard implementation owner; this checkpoint is a bounded
  source-adapter/model contract and was implemented directly without nested delegation.
- Review weight: standard from the parent feature/project default; child checkpoints close directly.
- Files changed: `src/legacy_engine/analytics/eras/discovery.py`,
  `src/legacy_engine/analytics/eras/discovery_source.py`, `src/legacy_engine/config.py`,
  `src/legacy_engine/data/eras/discovery-v1.json`,
  `tests/analytics/eras/test_discovery_source.py`.
- Tests added/removed: source cutoff, board ordering, closed-model, and missing-outcome-table
  tests covering the firewall interface.
- Simplification: the source adapter is a single bounded projection seam; no outcome-bearing
  compatibility type or query was introduced.
- Discrepancies from design: none; the source adapter is exported through a thin dedicated module
  while the typed implementation remains colocated with the pure core contracts.
- Adjacent issues parked: none.

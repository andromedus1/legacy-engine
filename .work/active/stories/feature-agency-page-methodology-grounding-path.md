---
id: feature-agency-page-methodology-grounding-path
kind: story
stage: done
tags: [analytics, advisory]
parent: feature-agency-page-methodology
depends_on: [feature-agency-page-methodology-kernel]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Typed path-to-grounding planner

## Brief

Turn the existing top-k and measured-coverage grounding contract into a deterministic data-
acquisition agenda that names every required cell and additional match count while limiting the
page preview to three explicitly truncated actions.

## Implementation

Implement Unit 2 in the parent feature's `## Implementation Units` section after
`feature-agency-page-methodology-kernel` is done.

## Implementation notes

- Execution capability: inherited frontier model at high effort; the planner turns an honesty gate
  into concrete collection guidance and must not overstate a partial path.
- Review weight: standard, inherited from the autopilot caller.
- Files changed: `src/legacy_engine/advisory/ranking_measurement.py` and
  `tests/test_ranking_measurement.py`.
- Tests added/removed: added mandatory top-k ordering, share-per-match coverage prioritization,
  replay-to-grounded verification, era-first projected source ties, complete path truncation/total,
  typed-ledger adaptation, grounded no-op, and invalid-configuration regressions; no tests removed.
- Simplification: the planner consumes a rate-free `GroundingCellState`; archetype/camp ledgers and
  direct strategic-plan cells can share it without importing a second coverage formula.
- Discrepancies from design: `GroundingCellState` carries the fallback kind so projected actions can
  preserve `ban-fallback` versus `full-corpus` provenance. The strategic-plan adapter regression is
  owned by the dependent report-surface story where that adapter is introduced.
- Adjacent issues parked: none.
- Verification: ranking measurement plus generator regressions — 58 passed.

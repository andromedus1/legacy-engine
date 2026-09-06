---
id: feature-player-effect-diagnostic-coverage-stickiness
kind: story
stage: done
tags: [analytics, players, experimental]
parent: feature-player-effect-diagnostic
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Player identity accessibility and pilot-stickiness ledger

## Brief

Measure what the corpus can honestly treat as a recurring player observation, separately by
provenance and identity basis, then emit privacy-safe pairwise pilot overlap for existing parent /
configuration subdivisions. This story is descriptive only: it neither merges suggested aliases nor
decides the taxonomy.

## Implementation

Implement Unit 1 in the parent feature's `## Implementation Units`. Establish the identity,
accessibility, minimum-repeat, privacy, and pilot-overlap contracts before any player effect is fit.

## Implementation notes

- Execution capability: inherited frontier worker at high effort; identity scoping and denominators
  are consequential inputs to the later statistical model.
- Review weight: standard (autopilot/default feature review).
- Files changed: `analytics/players/diagnostic.py`, the player-effect DuckDB workflow adapter, and
  focused analytics/workflow tests.
- Tests added: provenance-local versus curated identity, dated/hash/mode snapshot failures,
  independent repeat/familiarity gates, deterministic privacy-safe stickiness, and a hermetic
  online/paper corpus with blank and duplicate within-event handles plus variants.
- Simplification: identity eligibility and stickiness are pure typed functions; the adapter emits
  structural rows and never calls alias suggestion or writes a registry.
- Discrepancies from design: none. The workflow uses a private structural training-row model until
  Unit 2 installs the public `PlayerTrainingMatch` contract.
- Verification: 5 focused tests passed; focused Ruff and diff checks passed.
- Adjacent issues parked: none.

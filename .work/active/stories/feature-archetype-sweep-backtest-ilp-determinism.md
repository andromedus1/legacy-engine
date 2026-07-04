---
id: feature-archetype-sweep-backtest-ilp-determinism
kind: story
stage: implementing
tags: [advisory, sideboard]
parent: feature-archetype-sweep-backtest
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# ILP deterministic model construction

## Brief

`_ilp_solve` builds its PuLP/CBC model by iterating dicts/sets whose order varies across
processes (str-hash randomization), so equal-objective boards can differ run-to-run. Sort every
iteration during model construction (x_vars, z_c^k, y_vars, p_c, objective terms, linking
constraints) so the generated model is byte-stable; single-threaded CBC is then deterministic.
Drains `.work/backlog/idea-ilp-tiebreak-nondeterminism.md` (remove it in the same commit).

## Implementation

Parent feature `## Implementation Units` → **Unit 1**. Test: shuffled/reversed model-dict
insertion orders yield identical `card→copies`; full suite stays green.

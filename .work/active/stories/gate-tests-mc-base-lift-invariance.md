---
id: gate-tests-mc-base-lift-invariance
kind: story
stage: done
tags: [testing]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: tests
created: 2026-07-04
updated: 2026-07-04
---

# MC base layer lift-invariance contract untested

## Priority
High

## Spec reference
Item: `epic-sb-config-evaluation-config-comparator` (Unit 2 + Risks). AC: 'lifts only ever touch the point-estimate overlay (never the MC base).'

## Gap type
Business rule from spec untested — a regression folding lifts into the MC base would pass silently, defeating the honesty design.

## Suggested test
Same seed/configs, without lifts vs with a large --a-lift; assert p_a_beats_b_base, ev_a_base_ci, ev_b_base_ci identical.

## Test location
`tests/advisory/test_compare.py::TestMonteCarlo`

## Resolution
Added `test_mc_base_invariant_to_lifts` — same seed/matrix/field, config A with no lift vs config
A with a large (+0.45) lift; asserts `p_a_beats_b_base`, `ev_a_base_ci`, `ev_b_base_ci`, and
`ev_a_base` are all identical between the two runs, plus a sanity check that `ev_a_adj` DID move
(so the test isn't vacuously "nothing changed" — it isolates which layer the lift is allowed to
touch).

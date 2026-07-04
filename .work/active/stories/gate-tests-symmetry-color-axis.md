---
id: gate-tests-symmetry-color-axis
kind: story
stage: drafting
tags: [testing]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: tests
created: 2026-07-04
updated: 2026-07-04
---

# plays-<color> axis never exercised through symmetry_factor

## Priority
Medium

## Spec reference
Item: `feature-sb-field-weighted-scorer-impact`. AC: 'shares the hosed axis' = hoser.attacks & my_vulnerability_tags non-empty (same tag space claim).

## Gap type
Valid partition untested — symmetry floor only ever triggered via graveyard-recursion; color-axis drift would silently stop symmetry firing.

## Suggested test
symmetry_factor(make_hoser(symmetric, attacks={plays-blue}), my_tags={plays-blue,...}) hits _SYMMETRY_FLOOR; complement stays ~1.0.

## Test location
`tests/test_impact.py::TestSymmetryFactor`

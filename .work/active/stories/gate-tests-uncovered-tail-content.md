---
id: gate-tests-uncovered-tail-content
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

# uncovered_tail content never verified (vacuous type-only test)

## Priority
Medium

## Spec reference
Item: `epic-sideboard-core-and-hedge-output-contract`. AC: 'the uncovered-field tail with sizes.'

## Gap type
Tautological test — asserts isinstance(tuple) + vacuous all() over an empty tail.

## Suggested test
Two-archetype field where one tag has no candidate answer; assert that element appears in the tail with its weight and the covered element does not.

## Test location
`tests/test_sideboard.py::TestOutputContract` (rewrite test_covered_element_not_in_uncovered_tail)

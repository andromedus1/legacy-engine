---
id: gate-tests-uncovered-tail-content
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

## Resolution
Rewrote `test_covered_element_not_in_uncovered_tail`. The existing `_gy_field_corpus`/`_gy_catalog`
fixture is a single-element model (only Reanimator's element exists), so there was never a second,
genuinely-uncovered element to surface — the old assertions (`isinstance(tuple)` + `all(w>=0)`)
passed vacuously against an EMPTY tail. Rather than build a new DB corpus that could accidentally
also fully cover both tags, monkeypatched `_build_coverage_model` to a fixed, hand-built 2-element
`CoverageModel` (Reanimator|graveyard-recursion, weight 0.30, covered by the one catalog card;
BigMana|ramp, weight 0.20, covered by NO candidate) — the same `_make_model` house style used
throughout this file. Asserts the covered element is picked (clears τ=0.10), the uncovered
BigMana|ramp element appears in `uncovered_tail` with its real weight (0.20), and the covered
element does not appear in the tail. Full suite green.

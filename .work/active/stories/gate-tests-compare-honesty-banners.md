---
id: gate-tests-compare-honesty-banners
kind: story
stage: implementing
tags: [testing]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: tests
created: 2026-07-04
updated: 2026-07-04
---

# advise compare mandatory honesty banners have no test

## Priority
Critical

## Spec reference
Item: `epic-sb-config-evaluation-config-comparator` (Unit 4). AC: 'Lift overlay + data-ceiling banners always print.'

## Gap type
Acceptance criterion with no test — the always-on presence-correlational + transform-optimistic-ceiling banners (cli.py:2302-2303) are asserted nowhere.

## Suggested test
In TestAdviseCompare: run a basic comparison, assert both banner substrings; re-run with --a-lift and --b-transform, assert they still print.

## Test location
`tests/test_cli.py::TestAdviseCompare`

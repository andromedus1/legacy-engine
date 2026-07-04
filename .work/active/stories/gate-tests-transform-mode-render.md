---
id: gate-tests-transform-mode-render
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

# Transform chosen-mode rendering tested vacuously

## Priority
Critical

## Spec reference
Item: `epic-sb-config-evaluation-config-comparator` (Unit 4). AC: '--b-transform adds a second mode; the table shows the chosen mode per matchup.'

## Gap type
Tautological test — test_transform_mode_shown asserts 'Control' in output, which is a field row label printed regardless of --b-transform; the per-matchup mode label is never verified.

## Suggested test
Rewrite: build a matrix where mode B strictly wins one matchup and loses another; assert the mode label appears on the correct row and differs between rows.

## Test location
`tests/test_cli.py::TestAdviseCompare::test_transform_mode_shown` (rewrite)

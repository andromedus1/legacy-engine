---
id: gate-tests-transform-mode-render
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

## Resolution
Rewrote `test_transform_mode_shown` against a new hermetic fixture `transform_split_db`
(4 hand-built matchup cells, n=20 each: Combo 80% vs X / 20% vs Y, Control 20% vs X / 80% vs Y)
plus `xy_field_file` ({X:0.5, Y:0.5}). Config A is an unrelated imputed archetype so its label
can't collide with B's mode text. Asserts the X row shows B's chosen mode as "Combo" (and NOT
"Control"), and the Y row shows "Control" (and NOT "Combo") — the mode label now differs per row,
proving it tracks the actual per-matchup max rather than being a static field label.

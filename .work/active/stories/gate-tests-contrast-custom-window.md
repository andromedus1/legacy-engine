---
id: gate-tests-contrast-custom-window
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

# CLI custom single-window branch for --contrast untested

## Priority
Medium

## Spec reference
Item: `epic-sb-config-evaluation-matchup-slot-test` (Units 2/3). AC: explicit --since/--until yields ONE labeled custom-window report.

## Gap type
Valid partition untested at the public interface.

## Suggested test
report cards --contrast ... --since X --until Y --db <tmp>: assert exactly one section labeled custom, adaptive/full-corpus labels absent.

## Test location
`tests/test_cli.py::TestReportCardsContrast`

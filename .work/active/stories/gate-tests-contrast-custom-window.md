---
id: gate-tests-contrast-custom-window
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

## Resolution
Added `test_contrast_custom_window_single_section` — `report cards --contrast ... --since
2026-01-01 --until 2026-12-31`; asserts `result.output.count("// window:") == 1`, a `"custom ("`
label is present, and neither `"adaptive ban-aware"` nor `"full-corpus (all-time)"` appear.

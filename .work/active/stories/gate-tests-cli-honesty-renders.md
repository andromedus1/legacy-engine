---
id: gate-tests-cli-honesty-renders
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

# CLI honesty renders weak: thin-n banner untested; lift-slot test branch-ambiguous

## Priority
High

## Spec reference
Items: `epic-sb-config-evaluation-matchup-slot-test` (Unit 4: thin-n banner + tier per row) + `config-comparator` (Unit 4: --a-lift-slot folds a measured diff).

## Gap type
Boundary untested / weak assertion — no CLI test asserts the rendered thin-n banner (_echo_slot_contrast, cli.py:1442); test_a_lift_slot_folds_measured_diff asserts only the 'lift-slot:' prefix shared by folded AND skipped branches (cli.py:2288 vs 2293-2294).

## Suggested test
(a) CLI contrast on a thin corpus asserting the banner text; (b) lift-slot test asserting the folded-value line (or adjusted-EV shift), plus the skipped branch as a negative case.

## Test location
`tests/test_cli.py::TestReportCardsContrast`, `::TestAdviseCompare`

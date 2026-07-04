---
id: gate-tests-cli-honesty-renders
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

## Resolution
(a) Added `TestReportCardsContrast::test_contrast_thin_cohort_renders_thin_banner` — asserts the
`// thin: cohorts with n<30 are speculative...` banner renders on `contrast_db` (n_repeats=5 seeds
a WITH cohort of n=10, under the speculative floor).
(b) Disambiguated the lift-slot branches in `TestAdviseCompare`: added a new `slot_split_db`
fixture where Control's "Hate Card" has a genuine WITH/WITHOUT split (one owning winner, one
non-owning loser) so `test_a_lift_slot_folds_measured_diff` now exercises the actual FOLDED branch
— asserts the `→ measured lift +1.000.` line and that `adjusted field EV` moved. Added
`test_a_lift_slot_skipped_when_no_computable_diff` (using the original `compare_db`, where every
Control deck owns "Surgical Extraction" so the WITHOUT cohort is always empty) as the explicit
negative case for the SKIPPED branch — asserts the `no computable diff ... — skipped.` line and
that no `→ measured lift` text appears. The two branches were previously indistinguishable because
the old test only checked the shared `"lift-slot:"` prefix (and it turned out to be exercising the
skipped path, not the folded one, since `compare_db`'s Control decks all own the pulled card).

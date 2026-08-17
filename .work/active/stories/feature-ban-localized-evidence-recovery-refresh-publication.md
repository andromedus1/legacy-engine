---
id: feature-ban-localized-evidence-recovery-refresh-publication
kind: story
stage: done
tags: [advisory, ui, ops, testing]
parent: feature-ban-localized-evidence-recovery
depends_on: [feature-ban-localized-evidence-recovery-pair-selection]
release_binding: null
gate_origin: null
created: 2026-08-17
updated: 2026-08-16
---

# Automatic current-refresh evidence activation and utility-first publication

## Brief

Implement Unit 3 of the parent feature: make the normal current Best Deck / Best Call refresh
resolve matching exact recurrent-evidence artifacts automatically and publish the best available
current estimate in the existing archetype table with separate provenance, confidence, and proof
labels.

## Implementation notes

- Execution capability: GPT-5.6 high; current-target resolution and first-read publication cross
  refresh, analytics, status, and UI boundaries.
- Review weight: standard (project default); the parent feature remains the independent review
  boundary.
- Unqualified CLI and decision-refresh generation now resolve one exact current typed target. A
  missing certification/amplification table is the normal direct-evidence path with
  `certificate_run_id=None`; multiple exact artifacts refuse instead of selecting a latest winner.
- Published `best_available_estimate` on every archetype/camp row outside ranking authority. The
  first-read table labels it as a covered-field direct matchup estimate and exposes direct sample,
  cell/field coverage, clean-history recovery, provenance, confidence, and proof status.
- Added a report-utility projection that counts visible estimates, affected/unaffected direct cells,
  recovered physical history matches, and proof-grade rows separately. Scheduled status renders
  estimate coverage and proof coverage as distinct ratios.
- Preserved explicit `--field-since` as the legacy authority-only override and kept the mature
  ranking payload byte-identical by excluding additive row estimates/report utility from the
  authority projection.
- Tests added: no-artifact current CLI activation, exactly-once generation, decision-refresh target
  attachment, visible row copy, archetype/camp header-to-cell arithmetic, and status estimate/proof
  separation.
- Simplification: normal refresh uses the same typed target and evidence attachment path as exact
  report generation; there is no second refresh-specific evidence implementation.
- Discrepancies from design: none.
- Adjacent issues parked: none.

## Verification evidence

- `.venv/bin/pytest tests/test_decision_refresh.py tests/test_ops_status.py
  tests/test_refresh_best_call_ranking.py
  tests/analytics/amplification/test_best_call_evidence.py -x -q` — 79 passed.
- `git diff --check` — passed.

---
id: feature-ban-localized-evidence-recovery-pair-selection
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: feature-ban-localized-evidence-recovery
depends_on: [feature-ban-localized-evidence-recovery-exposure-authority]
release_binding: null
gate_origin: null
created: 2026-08-17
updated: 2026-08-16
---

# Pairwise localized selection and evidence-view recovery

## Brief

Implement Unit 2 of the parent feature: feed localized clean-interval authority into exact
pairwise selection and report evidence views so unaffected parent pairs keep compatible history,
affected edges exclude only contaminated exposure intervals, and camps remain current-only.

## Implementation notes

- Execution capability: GPT-5.6 high; exact pairwise selection and report provenance cross the
  analytics/advisory boundary.
- Review weight: standard (project default); feature review remains the independent boundary.
- Threaded localized clean atoms through the existing exact pair intersection and selected-outcome
  ledger. Unaffected entity intervals remain unchanged; affected pairs expose the pre-exposure and
  post-ban components while the contamination gap stays absent.
- Added report-level localized source metadata and a typed `best_available_direct` projection with
  `localized-clean-direct`, `certified-direct`, `current-direct`, or `unavailable` provenance.
- Provenance is observation-based: localized/certified labels require actual selected added-history
  rows from those components; zero added history is always `current-direct`.
- The physical ledger now fails closed if any expanded observation lands inside a typed localized
  contamination gap.
- Preserved parent/camp parity: camp evidence still has identical current/expanded match digests,
  empty added history, and the explicit `camp-current-only` reason.
- Tests added: localized pair report projection, best-direct sample recovery, exact boundary/card
  provenance, and no duplicate match ids across selected views.
- Simplification: no second pair aggregation or reverse-selection path; the report is an adapter over
  the existing canonical physical ledger.
- Discrepancies from design: none.
- Adjacent issues parked: none.

## Verification evidence

- `.venv/bin/pytest -q tests/analytics/eras/test_interval_consumption.py
  tests/analytics/amplification/test_best_call_evidence.py tests/test_refresh_best_call_ranking.py`
  — 69 passed.
- `.venv/bin/python -m compileall -q src/legacy_engine/advisory/best_call_evidence.py` — passed.

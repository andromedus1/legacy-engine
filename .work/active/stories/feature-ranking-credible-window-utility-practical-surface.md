---
id: feature-ranking-credible-window-utility-practical-surface
kind: story
stage: done
tags: [analytics, advisory, ui, testing]
parent: feature-ranking-credible-window-utility
depends_on: [feature-ranking-credible-window-utility-transition-field]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Practical shortlist and first-read hierarchy

## Brief

Implement Unit 3 of the parent feature: use the existing posterior lean to rank every supported row
for the practical first read while retaining ci-gated Agency as the proof-grade authority.

## Implementation notes

- Added `practical_recommendation_order`, sorting supported rows by existing lean Q25, then median,
  then stable label. It never mutates or substitutes `production_recommendation_order`.
- Evidence payloads now carry observed and decision field shares and can identify transition-prior
  rows; archetype rows receive the typed evidence projection from the generated CI-gated ledger.
- The HTML template now leads with an accessible practical first-read panel showing lean intervals,
  observed/effective field provenance, prior influence, horizon clamps, and the separate proof-grade
  call. Existing disclosure/table controls remain after this compact panel.

## Verification

- `PYTHONPATH=. uv run --no-sync python -m pytest -q tests/test_positioning.py::TestRankingEvidencePayload tests/test_refresh_best_call_ranking.py` (50 passed)
- `PYTHONPATH=. uv run --no-sync python -m pytest -q tests/test_positioning.py::TestRankingEvidencePayload::test_practical_order_uses_lean_q25_then_median_then_label` (included above)

## Deviations / adjacent issues

- Camp payload shape remains parity-compatible with its established additive allow-list; the first-
  read recommendation is archetype-level, while camp evidence remains available in its existing
  generated evidence column and disclosures.

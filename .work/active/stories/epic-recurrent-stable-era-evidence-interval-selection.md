---
id: epic-recurrent-stable-era-evidence-interval-selection
kind: story
stage: done
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-interval-consumption
depends_on: [epic-recurrent-stable-era-evidence-interval-algebra]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Exact pair selection and gap-proof match provenance

## Brief

Implement Unit 2 from the parent feature: one resolved-match ledger, deterministic match ids, exact
subject/opponent interval intersection, gap-preserving row selection, and the legacy aggregate API as
an adapter over the shared selection seam.

## Implementation

See `epic-recurrent-stable-era-evidence-interval-consumption` Unit 2 for exact interfaces, notes, and
acceptance criteria. Preserve existing join cardinality, ambiguity, bye/draw, mirror, split-label,
source, and directed-symmetry behavior while retaining both sides' component/certificate provenance.

## Acceptance

- A row enters only an exact pair atom before exclusive `data_until`; one-sided history and gaps are
  excluded.
- Stable match/component ids survive ordering and pooling without duplication.
- One-component scalar aggregation remains field-for-field compatible with the current API.

## Tests

Run focused match-record/selection tests, existing match-results/era tests, Ruff on touched files,
and compileall as specified by the parent feature.

## Implementation notes

- Added deterministic `ResolvedMatch`, `PairEligibility`, and `SelectedMatch` contracts.
- Added one resolved decisive-pair scan with stable duplicate ordinals and canonical match ids.
- Added exact current/expanded pair intersection and half-open membership selection, retaining both
  component and certificate provenance per selected row.
- Kept `compute_match_results` behavior unchanged while exposing the shared record seam for the
  subsequent evidence/matrix adapters.

## Verification evidence

- `PYTHONPATH=. .venv/bin/pytest -q tests/test_match_results.py tests/test_regime_windowing_core.py` — 62 passed.
- `PYTHONPATH=. .venv/bin/python -m compileall -q src/legacy_engine/analytics/match_results.py` — passed.

## Simplifications/deviations

- The legacy aggregate remains an adapter target for the next checkpoint; this commit introduces
  the cardinality-safe resolved ledger without changing established aggregate golden values.

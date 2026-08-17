---
id: story-fix-resolved-match-timestamp-dates
kind: story
stage: review
created: 2026-08-16
updated: 2026-08-16
tags: [analytics, bug]
parent: null
depends_on: []
release_binding: null
gate_origin: null
---

# Accept timestamp-shaped tournament dates in resolved match evidence

## Brief

Make the resolved-match evidence path accept the production corpus' supported date and timestamp
storage shapes so localized-evidence refresh can select physical matches without changing date
cutoff or identity semantics.

## Simplification opportunity

Reuse the ingestion layer's existing date normalization shape if available; do not add a parallel
timestamp authority or change the stored corpus.

## Symptom

The live current ranking refresh raised `ValueError: Invalid isoformat string:
'2025-07-20T09:00:00+00:00'` while `resolve_match_records` built the localized selected-outcome
ledger.

## Root cause

`_JOIN_SQL` deliberately returns the corpus date column as text, but `resolve_match_records` passed
the whole value to `date.fromisoformat`. Most fixtures store `YYYY-MM-DD`; production also stores
valid timezone-aware ISO timestamps whose first ten characters carry the same calendar-date
authority used by the SQL half-open cutoffs.

## Fix approach

Normalize the returned ISO value to its `YYYY-MM-DD` prefix at the resolver boundary, matching the
existing ingestion/analytics convention and retaining all physical-match and cutoff semantics.

## Regression test

`tests/analytics/eras/test_interval_consumption.py` inserts a timezone-aware tournament timestamp
and asserts the resolver returns its calendar date without rejecting the physical match.

## Implementation notes

- Execution capability: GPT-5.6 high; a minimal parser fix was selected because the production
  failure was deterministic and isolated to one boundary.
- Files changed: `src/legacy_engine/analytics/match_results.py` and
  `tests/analytics/eras/test_interval_consumption.py`.
- The regression first failed with the production `ValueError`, then passed after normalizing the
  SQL-returned ISO value to its ten-character calendar-date prefix.
- Four-step confirmation: the new regression passes; the resolver/match suite passes (67 tests);
  the full suite passes (3,989 passed, 1 skipped); the original live command advanced past the
  timestamp row into evidence selection without the parser failure.
- Adjacent issues parked: none. The pre-existing pair-by-pair query cost surfaced after the parser
  fix and remains in the parent feature's Unit 4 implementation scope because the normal refresh
  must be operational at current-corpus scale.

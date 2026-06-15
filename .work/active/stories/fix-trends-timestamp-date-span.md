---
id: fix-trends-timestamp-date-span
kind: story
stage: done
tags: [bug, analytics]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-05-30
updated: 2026-06-14
---

# Fix: trends crashes on full-timestamp tournament dates

## Brief
Discovered running `compute_trends` on the real corpus: `_window_event_stats` called
`date.fromisoformat(max_date_str)` on `tournaments.date`, which crashed with
`Invalid isoformat string: '2025-11-09T14:00:00+00:00'`. The trends feature assumed dates are always
plain `YYYY-MM-DD` (the fixtures used date-only), but real fbettega data — notably MTGmelee events —
carries **full ISO timestamps** (`YYYY-MM-DDTHH:MM:SS+00:00`). The SQL regime windowing is unaffected
(lexicographic ISO comparison still half-opens correctly across mixed formats); only the Python span_days
computation broke.

## Fix
`analytics/trends.py` `_window_event_stats`: take the date portion (`max_date_str[:10]`) before
`date.fromisoformat`. Regression test `tests/test_trends.py::TestMetashareWindowing::
test_timestamp_format_dates_do_not_crash_span` loads two timestamp-dated events and asserts compute_trends
counts them without crashing.

## Outcome
`compute_trends` runs across all 7 ban regimes on the real corpus. 581 tests green. The trends output
revealed the Entomb ban (2025-11-10) collapsed Dimir Reanimator 14.7%→0.1% and the Undercity Informer ban
(2026-05-18) collapsed Oops! All Spells 5.5%→0.7% — recontextualizing the whole-year meta-share ranking.

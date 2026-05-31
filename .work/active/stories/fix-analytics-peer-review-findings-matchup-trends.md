---
id: fix-analytics-peer-review-findings-matchup-trends
kind: story
stage: review
tags: [analytics, bug]
parent: fix-analytics-peer-review-findings
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Mirror inclusion + top-cut trends denominator (findings 2, 8)

## Brief
In `analytics/matchup.py`, make the row-inclusion denominator `2*(decisive_matched + mirror_matches)` so the
ratio is consistent with the numerator (which already includes each archetype's mirror credits) — a
mirror-only corpus no longer yields an included row with `total_matches=0` (#2). In `analytics/trends.py`,
for top-cut trends skip regimes whose report `total_decks == 0` rather than keeping a zero-denominator regime
that merely had in-window events (#8).

## Implementation
Parent `fix-analytics-peer-review-findings` → **Unit 3**. Files: `analytics/matchup.py`, `analytics/trends.py`.
Tests in `tests/test_matchup.py`, `tests/test_trends.py`. Reads only existing `MatchCoverage` fields — no
dependency on the other stories. See parent `## Design decisions` (count-mirrors-both-sides) and
`## Implementation Units` Unit 3 for exact changes + acceptance criteria.

## Implementation discovery
None — both fixes applied cleanly as designed with no deviations.

## Implementation notes
- **Finding #2 (`matchup.py`)**: Changed `_denom_base = decisive_matched + mirror_matches` (was
  `total_matches` only), so the row-inclusion denominator is `2 * (decisive_matched + mirror_matches)`.
  Added helper `_denom_base` local variable for readability. Updated `build_matrix` docstring to state
  the denominator now includes mirror matches and why (numerator/denominator consistency). The
  `MatchupMatrix.total_matches` field still carries `decisive_matched` only (unchanged — it is the
  decisive-match count used by callers for the headline stat, not the denominator).
- **Finding #8 (`trends.py`)**: Added a guard after `compute_metashare` in the main loop: if
  `definition == "topcut"` and `report.total_decks == 0`, log at DEBUG and `continue`. The skip uses
  the *report's* `total_decks` (top-cut decks from standings), not `_window_event_stats` event count,
  so a regime with events but no standings rows is correctly excluded.
- **Tests added**: `TestMirrorInclusion` (3 tests in `test_matchup.py`) and
  `TestTopCutZeroDeckRegimeSkipped` (3 tests in `test_trends.py`). 92 tests total, all passing
  (was 86 before this story).
- **Pre-existing note**: `test_trends.py` has `test_timestamp_format_dates_do_not_crash_span`
  floating between `TestMetashareWindowing` and `TestComputeTrends` — Python collects it as part of
  `TestMetashareWindowing` due to indentation. Pre-existing; not touched.

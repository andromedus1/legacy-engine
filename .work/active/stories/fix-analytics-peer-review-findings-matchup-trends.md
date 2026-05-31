---
id: fix-analytics-peer-review-findings-matchup-trends
kind: story
stage: implementing
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

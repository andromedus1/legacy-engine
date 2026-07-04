---
id: feature-sb-slot-roi-punt-roi
kind: story
stage: implementing
tags: [advisory]
parent: feature-sb-slot-roi-punt
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Slot-ROI table + punt detection + render

## Brief

Additive decision-support layer: per-matchup slot-ROI (`marginal equity gain × field share`),
punt detection (max realistic dedication still <50%, or better ROI elsewhere), rendered in
`advise sideboard`. Does NOT change which cards are picked — it advises slot allocation.

## Implementation

Covers parent feature **Units D1 + D2 + D3** — see `feature-sb-slot-roi-punt` § Implementation
Units for `MatchupROI`, `_slot_roi_table`, punt rules, render block, and acceptance criteria.
Files: `src/legacy_engine/advisory/sideboard.py` + `src/legacy_engine/cli.py`; tests in
`tests/test_sideboard.py` + a CLI render test with a tmp `--db`.

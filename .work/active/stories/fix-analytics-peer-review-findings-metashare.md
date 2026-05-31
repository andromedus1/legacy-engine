---
id: fix-analytics-peer-review-findings-metashare
kind: story
stage: done
tags: [analytics, bug]
parent: fix-analytics-peer-review-findings
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Metashare coverage + blend fixes (findings 1 top-cut-half, 3, 4, 5, 6)

## Brief
In `analytics/metashare.py`: apply the same dup-CTE ambiguous-name exclusion to `_TOPCUT_SQL` (#1 top-cut
half); add a top-cut-specific unlabeled count instead of hardcoding `unlabeled=0` (#3); honor `display_total`
in the non-grouped `_assemble` return path (#4); surface wrw archetypes with deck-count-but-no-match-data via
a new `MetaShareReport.excluded_no_match_data` field (#5); and in `blend_shares` keep the "Other" bucket in
the blend (no named-share inflation) and guard against a zero weight-sum (#6).

## Implementation
Parent `fix-analytics-peer-review-findings` → **Unit 2**. File: `analytics/metashare.py` only (incl. the
`MetaShareReport` dataclass). Tests in `tests/test_metashare.py`. See parent `## Design decisions`
(keep-Other-in-the-mix) and `## Implementation Units` Unit 2 for SQL, signatures, and acceptance criteria.

## Implementation discovery

### Stale-test fix (surfaced per story instructions)
`_wrw_weights` now returns a 3-tuple `(weights, matchup_n, excluded)` — the `excluded` list (finding #5)
is a new third element. The four existing `TestWrwWeights` tests that unpacked the old 2-tuple were stale
and required mechanical fixes (changed `weights, matchup_n = ...` → `weights, matchup_n, _excluded = ...`).
This is expected breakage from the signature change, not a production bug. Surfaced here as required.

### Design rationale: _topcut_unlabeled as separate SQL
A separate `_TOPCUT_UNLABELED_SQL` (with its own `_topcut_unlabeled` helper) was introduced rather than
modifying `_TOPCUT_SQL` to return a second column. This keeps the SQL focused on one concern per query,
matches the pattern of `_raw_counts` / `_unlabeled_count` being separate, and avoids changing the return
type of `_topcut_counts` (which is used in several places and imported directly in tests).

### Finding #6b: blend_shares normalization note
After removing the `if entry.archetype != "Other"` filter, the blended shares of Delver+Other now
sum to ~1.0 before the `share_total > 0` renorm step, so the renorm is effectively a no-op in the
typical single-provenance case. The assertion in `test_blend_shares_keeps_other_not_inflated` verifies
the end-to-end share values are correct (~0.80 Delver, ~0.20 Other).

### All 6 acceptance criteria met
- [x] Top-cut counts no longer inflate from duplicate normalized names; ambiguous names are excluded.
- [x] A top-cut window with 1 labeled + 1 NULL-archetype deck reports `total_decks=1, unlabeled=1`.
- [x] `compute_metashare(definition="wrw", group_other=False)` reports `total_decks` = matchup-n, not 1.
- [x] A wrw archetype with deck count but zero match data appears in `excluded_no_match_data`.
- [x] `blend_shares` with A=80%/Other=20% keeps Other at ~20% (named shares not inflated to 100%).
- [x] `blend_shares` with all-zero weights raises `ValueError`, not `ZeroDivisionError`.

---
id: fix-analytics-peer-review-findings-metashare
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

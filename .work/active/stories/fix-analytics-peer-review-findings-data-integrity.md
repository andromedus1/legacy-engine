---
id: fix-analytics-peer-review-findings-data-integrity
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

# Cardinality-safe rounds join + bye classification (findings 1 rounds-half, 7)

## Brief
Make the rounds↔decks join in `analytics/match_results.py` cardinality-safe: a `dup` CTE flags normalized
player names that are non-unique within a tournament, and the accumulator excludes those pairings into a new
`MatchCoverage.ambiguous_player_names` counter instead of double-counting or mislabeling them unmatched (#1).
Also classify blank-opponent byes (`player2=""`) as `dropped_byes_draws` before the unmatched check (#7).

## Implementation
Parent `fix-analytics-peer-review-findings` → **Unit 1**. File: `analytics/match_results.py` only (incl. the
`MatchCoverage` dataclass + its invariant docstring). Tests in `tests/test_match_results.py`. See parent
`## Design decisions` (skip-the-confusing-ones) and `## Implementation Units` Unit 1 for the exact CTE,
loop ordering, and acceptance criteria. Trickiest — build the dup-CTE + ambiguous flagging first.

---
id: feature-ranking-measurement-integrity-evidence-contracts
kind: story
stage: done
tags: [analytics, advisory, honesty]
parent: feature-ranking-measurement-integrity
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Pair-window and concentration evidence contracts

## Brief

Make current build/camp comparison windows outcome-blind and attach additive event/month
concentration evidence to the exact matchup cells selected from those windows.

## Implementation

Implements Unit 1 of the parent feature's `## Implementation Units`: pair-window clamping,
directed event/month tallying, concentration metadata, and single/multi adaptive parity.

## Implementation notes

- Execution capability: inherited frontier model at high effort; the analytics contracts are broad
  and statistically consequential, matching the autopilot caller's explicit choice.
- Review weight: standard (caller).
- Files changed: `models/matchup.py`, `analytics/match_results.py`, `analytics/matchup.py`,
  `analytics/eras/consume.py`, and the four designed test surfaces.
- Tests added/removed: added deterministic pair-window, event/month bucket, concentration tie/null,
  and bucket-integrity regressions; no tests removed.
- Simplification: both adaptive builders now use one `clamp_pair_window` contract; event/month
  evidence uses the same explicit opponent-pooling map as numeric tallies.
- Discrepancies from design: concentration bucket maps are additive fields on `MatchResults` so the
  exact selected scan remains their source; no separate tally wrapper was necessary.
- Adjacent issues parked: none.
- Verification: `PYTHONPATH=. .venv/bin/pytest -q tests/test_match_results.py
  tests/test_matchup.py tests/test_matchup_multi_split.py tests/analytics/eras/test_consume.py`
  — 198 passed.

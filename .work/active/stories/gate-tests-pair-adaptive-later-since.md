---
id: gate-tests-pair-adaptive-later-since
kind: story
stage: done
tags: [testing]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: tests
created: 2026-07-04
updated: 2026-07-04
---

# Adaptive pair-window later-of-two valid_since path untested

## Priority
Critical

## Spec reference
Item: `epic-sb-config-evaluation-matchup-slot-test` (Unit 2). AC: 'Adaptive since equals the later of the two archetypes' valid_since.'

## Gap type
Acceptance criterion with no test — only the unaffected/None case of pair_adaptive_since is tested; the max(dates) branch (ban-regime correctness core) is not.

## Suggested test
Hermetic DB with hero/opponent archetypes carrying different ban-affectedness valid_since dates; assert pair window == the later. Also one-affected/one-not.

## Test location
`tests/analytics/test_slot_test.py::TestWindowing`

## Resolution
Added `test_pair_adaptive_since_later_of_two` (Hero ban-affected by Grief at 2024-08-26, Opp
ban-affected by Entomb at 2025-11-10 — asserts the pair window is the LATER date, 2025-11-10) and
`test_pair_adaptive_since_one_affected_one_not` (only Opp is ban-affected — asserts the pair still
resolves to Opp's valid_since rather than None). Both use real BAN_EVENTS dates with hand-built
pre-ban decks running the banned card in half the cohort (>= the 0.25 affect_threshold).

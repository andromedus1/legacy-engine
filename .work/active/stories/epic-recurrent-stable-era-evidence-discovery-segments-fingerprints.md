---
id: epic-recurrent-stable-era-evidence-discovery-segments-fingerprints
kind: story
stage: done
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-discovery
depends_on: [epic-recurrent-stable-era-evidence-discovery-firewall-corpus]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Cutoff-refit segments, fingerprints, and recurrent candidates

## Brief

Implement Unit 2 from the parent feature: pure outcome-free weekly segmentation, board-separated
segment fingerprints, deck-mixture and field/source comparison channels, support-aware refusals,
and deterministic complete-link nomination of older parent-archetype states against the current
reference segment.

## Implementation

See `epic-recurrent-stable-era-evidence-discovery` Unit 2 and its acceptance criteria.

Review weight remains `standard` at the parent feature boundary.

## Implementation notes

- Execution capability: delegated standard implementation owner; pure segmentation, fingerprint,
  channel comparison, support refusals, and complete-link nomination were implemented against the
  closed corpus contract without nested delegation.
- Review weight: standard from the parent feature/project default; child checkpoints close directly.
- Files changed: `src/legacy_engine/analytics/eras/discovery.py`,
  `tests/analytics/eras/test_discovery.py`.
- Tests added/removed: deterministic recurrence, sideboard/mixture channels, hard-contract epochs,
  and parent-only entity tests.
- Simplification: the v1 detector is deterministic and keeps the seed as a forward-compatible
  contract input without introducing an unnecessary random state layer.
- Discrepancies from design: the inspectable boundary detector uses a weighted local PELT-style
  gain guard rather than an external mutable fit object; hard boundaries remain structural even
  when they create thin segments, which then receive explicit support refusals.
- Adjacent issues parked: none.

## Completion evidence

- Focused verification: `.venv/bin/pytest -q tests/analytics/eras/test_discovery*.py` — 11 passed.

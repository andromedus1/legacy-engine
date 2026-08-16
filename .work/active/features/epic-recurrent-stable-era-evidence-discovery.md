---
id: epic-recurrent-stable-era-evidence-discovery
kind: feature
stage: drafting
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Outcome-firewalled recurrent-state discovery

## Brief

Build an inspectable parent-archetype segmentation and fingerprint pipeline that can nominate older
configuration periods as candidates for recurrence. Discovery may use mainboard and sideboard
composition, deck-level mixture shape, legality, taxonomy, provenance, event support, and field
context at an explicit cutoff. Its input contract must make matchup wins, standings, conversion, and
other outcomes unavailable rather than merely unused by convention.

This feature produces candidates and their evidence; it does not certify equivalence, select matchup
rows, or alter a production ranking. Camps remain outside the first certification surface and retain
their current-only behavior.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: foundation feature; certification depends on its cutoff-safe candidate and
  fingerprint contracts.

## Inherited design decisions

- Parent archetypes are the first certification surface; camps do not inherit parent certainty.
- The initial method is inspectable segment/fingerprint comparison with complete-link grouping.
- Discovery is outcome-firewalled and deterministic at an explicit cutoff.
- Complex sticky-state methods remain benchmark challengers rather than production defaults.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — discovery contract and selected
  first-pass method.
- `.research/analysis/campaigns/recurrent-era-intervals/specialists/discover.md` — candidate methods,
  assumptions, and challenger analysis.
- `docs/briefs/change-point-detection.md` — existing stable-era detector grounding and corpus shape.

## Foundation references

- `docs/VISION.md` — certified per-entity interval evidence.
- `docs/SPEC.md` — recurrent stable-era evidence capability.
- `docs/ARCHITECTURE.md` — `analytics/eras/` discovery and certificate boundaries.


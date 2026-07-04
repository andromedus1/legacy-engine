---
id: epic-deck-prep-arc-dimir-boards
kind: feature
stage: drafting
tags: [advisory, analysis, dogfooding]
parent: epic-deck-prep-arc
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# Dimir Tempo sideboard refresh — two collection-aware boards

## Brief

Fresh optimized sideboard for Andrew's Dimir Tempo (Build B, `decks/dimir-tempo-current.txt`;
prior optimized board + analysis: `decks/dimir-tempo-optimized.txt` + `-analysis.md`), using
the post-sweep engine (deterministic ILP, PR #35). Produce TWO boards per meta lens where
they differ: **Board A** unconstrained — may include cards Andrew doesn't own, and those
unowned inclusions double as the acquisition-target list (paired-swap presentation: every
add names its cut); **Board B** constrained to the current collection (`decks/binder.txt`
is confirmed accurate). Deliverable: updated board files + analysis doc in `decks/` per the
established pattern (frequency-distribution-detail: show full 0x-4x copy histograms vs
winners, now available natively from the sweep/backtest copy surfaces).

Does NOT cover: other archetypes, meta-specific 60s (next feature), scorer changes. Apply
session-1 judgment overrides where still mechanically justified (Defense Grid / Damping
Sphere exclusions — both now confirmed systematic by the sweep).

## Epic context

- Parent epic: `epic-deck-prep-arc`
- Position: foundation stride — establishes the refreshed Dimir reference the comparison
  feature consumes.

## Inherited design decisions

- Collection data is CURRENT; Board A unconstrained (= acquisition targets), Board B
  owned-only. If the solver lacks a hard owned-only mode, restrict the candidate pool to
  owned cards and label the constraint honestly (feature-design call).
- Boulder field = `decks/boulder-field-since-518.txt`; online = `provenance='online'`,
  current-regime window.

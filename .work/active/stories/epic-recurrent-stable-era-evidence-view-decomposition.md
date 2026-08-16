---
id: epic-recurrent-stable-era-evidence-view-decomposition
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-interval-consumption
depends_on: [epic-recurrent-stable-era-evidence-interval-selection]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Typed evidence decomposition, concentration, and prior isolation

## Brief

Implement Unit 3 from the parent feature: exact current-only/certified-expanded/added-history views,
auditable component and event/source concentration, effective support, view-local estimates, and a
hard no-double-count invariant between admitted observations and priors.

## Implementation

See `epic-recurrent-stable-era-evidence-interval-consumption` Unit 3 for exact interfaces, decisions,
notes, and acceptance criteria. Build added history from match ids, not rounded estimates. Expanded
and added views use hierarchy-only priors; current pre-disturbance borrowing remains allowed only
with proven empty observation/prior intersection.

## Acceptance

- Current plus added raw records exactly partition expanded records and counts.
- Concentration exposes event/source/component dominance and effective events, with honest nullable
  pilot identity.
- No admitted historical match can enter its estimate twice through a pre-disturbance prior.

## Tests

Run focused decomposition/concentration/prior tests, existing matchup tests, Ruff on touched files,
and compileall as specified by the parent feature.

---
id: feature-player-effect-diagnostic
kind: feature
stage: drafting
tags: [analytics, players, experimental]
parent: epic-best-deck-decision-trust
depends_on: [feature-ranking-future-only-benchmark]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Player-effect diagnostic — pilot stickiness and earned adjustment

## Brief

Measure whether player identity can clarify deck taxonomy and improve prediction without turning
thin or unstable handles into false precision. First report identity/alias/repeat-event coverage and
pilot overlap between candidate configurations. Then test a strictly pre-match, partially pooled
player effect—and, only where supported, player-by-archetype familiarity—inside the future-only
benchmark. Default ranking output remains unchanged unless the adjusted model demonstrates durable
out-of-sample improvement.

The pilot-stickiness interpretation references backlog item
`idea-decision-unit-taxonomy-heterogeneity-gate`: shared pilots suggest one deck with a tuning knob;
disjoint pilot populations support distinct decision units. This feature does not absorb or
implement the broader taxonomy gate.

## Strategic decisions

- Online and paper identity coverage are reported separately; an empty curated alias table is an
  explicit limitation, not an invitation to auto-merge people.
- Player ratings used for a match are snapshots from before that match.
- Divergence between adjusted and unadjusted deck estimates is diagnostic until future-only scores
  justify changing the headline.

## Simplification opportunity

Reuse the existing identity, strength, and archetype-history modules. Replace threshold-only
“strong player” use only if the new model proves superior; do not maintain two headline adjustment
systems.

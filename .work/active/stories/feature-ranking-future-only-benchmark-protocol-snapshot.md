---
id: feature-ranking-future-only-benchmark-protocol-snapshot
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: feature-ranking-future-only-benchmark
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Preregistered protocol and leakage-safe origin snapshot

## Brief

Define the frozen benchmark protocol and whole-event-date walk-forward folds, then build an
auditable cutoff-safe corpus snapshot that recomputes eras and excludes future taxonomy, B&R,
player, card, and outcome state.

## Implementation

Implement Unit 1 in the parent feature's `## Implementation Units` section. This is the trickiest
unit and must prove the leakage boundary before predictions or scores are allowed to exist.

---
id: feature-ranking-honesty-guards-regime-currency
kind: story
stage: implementing
tags: [advisory, analytics]
parent: feature-ranking-honesty-guards
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Typed field regime currency

## Brief

Measure the share of a global field backed by current-regime observations, accept an exact custom
current-regime numerator only when count-backed, and emit named informational/warning audit lines.
Undated custom aggregates degrade to an explicit unavailable reason rather than a fabricated rate.

## Implementation

Implement Unit 3 in the parent feature's `## Implementation Units` section. Do not add refresh,
card-dimension, monitoring, reweighting, or other `feature-decision-data-currency` responsibilities.

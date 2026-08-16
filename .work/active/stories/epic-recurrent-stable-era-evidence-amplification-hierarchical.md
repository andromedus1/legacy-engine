---
id: epic-recurrent-stable-era-evidence-amplification-hierarchical
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-amplification
depends_on: [epic-recurrent-stable-era-evidence-amplification-contract]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Current-target hierarchical component pooling challenger

## Brief

Implement Unit 2 from the parent feature: a transparent era-component hierarchy that targets the
current pair logit, models certified component variation, emits event-block uncertainty and
deletion/ablation diagnostics, and refuses conflict or unstable computation honestly.

## Implementation

See `epic-recurrent-stable-era-evidence-amplification` Unit 2 for exact interfaces, model, notes, and
acceptance criteria. Learned commensurability is explicitly outcome-adaptive challenger evidence and
must never feed certification or baseline authority.

## Acceptance

- Component agreement/conflict changes historical influence without changing the direct baseline.
- Current/history/no-pair ablations and component influence remain explicit.
- Concentrated or unreliable fits retain diagnostics but cannot serve a supported magnitude.

## Tests

Run focused synthetic hierarchy, concentration, determinism, and computation-failure tests plus the
shared amplification contract suite.

## Implementation evidence

- Added deterministic `ComponentHierarchyFit` and current-target prediction adapter over canonical
  rows, with explicit ablations and typed imputation/service state.
- Ruff and import/compile checks pass; no database or aggregate-selection path exists.

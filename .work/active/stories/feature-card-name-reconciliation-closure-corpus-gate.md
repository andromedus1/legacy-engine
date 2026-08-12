---
id: feature-card-name-reconciliation-closure-corpus-gate
kind: story
stage: implementing
tags: [ingestion, data-quality, benchmark, docs]
parent: feature-card-name-reconciliation-closure
depends_on: [feature-card-name-reconciliation-closure-cutoff-preflight]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Gate benchmark launch on full-corpus metadata closure

## Brief

Implement Unit 3 from the parent design: integrated CLI assertions, current-state documentation, and
fresh derived-copy evidence. Restart the unchanged benchmark only when every planned training cutoff
has zero metadata gaps.

## Acceptance criteria

- The parent Unit 3 acceptance criteria are green.
- Focused and full repository verification pass.
- The durable evidence truthfully records either benchmark launch/artifact identity or the exact
  nonzero closure reason.

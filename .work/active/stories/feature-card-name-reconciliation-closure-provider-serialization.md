---
id: feature-card-name-reconciliation-closure-provider-serialization
kind: story
stage: implementing
tags: [ingestion, data-quality, benchmark]
parent: feature-card-name-reconciliation-closure
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Resolve verified provider serialization shapes

## Brief

Implement Unit 1 from the parent design: evidence-scoped deterministic candidates for verified
set-prefix, duplicated-name, duplicated-final-face, and localized-face serialization, with exact
canonical-target and provider guards. Preserve every ambiguous, unsupported, or speculative value.

## Acceptance criteria

- The parent Unit 1 acceptance criteria are green.
- Focused reconciliation tests cover each positive class and every named safety boundary.
- Implementation notes record the admitted rule registry and any corpus discrepancy.

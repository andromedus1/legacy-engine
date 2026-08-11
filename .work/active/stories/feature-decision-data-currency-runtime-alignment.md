---
id: feature-decision-data-currency-runtime-alignment
kind: story
stage: implementing
tags: [infra]
parent: feature-decision-data-currency
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Align the local and CI Python runtime contract

## Brief

Pin the maintainer checkout to Python 3.13, bound package support to Python 3.11–3.13, test both
the lower bound and maintainer pin in CI, and document the optional discovery stack honestly so a
fresh contributor checkout has the same definition of green as CI.

## Implementation

Implement Unit 1 in the parent feature's `## Implementation Units` section. Preserve unrelated
`uv.lock` edits; only reconcile its Python constraint if the package tool requires it and the
existing change can be retained.

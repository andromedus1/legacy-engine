---
id: story-fix-resolved-match-timestamp-dates
kind: story
stage: implementing
created: 2026-08-16
updated: 2026-08-16
tags: [analytics, bug]
parent: null
depends_on: []
release_binding: null
gate_origin: null
---

# Accept timestamp-shaped tournament dates in resolved match evidence

## Brief

Make the resolved-match evidence path accept the production corpus' supported date and timestamp
storage shapes so localized-evidence refresh can select physical matches without changing date
cutoff or identity semantics.

## Simplification opportunity

Reuse the ingestion layer's existing date normalization shape if available; do not add a parallel
timestamp authority or change the stored corpus.

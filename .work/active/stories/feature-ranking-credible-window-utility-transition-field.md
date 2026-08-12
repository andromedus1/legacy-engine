---
id: feature-ranking-credible-window-utility-transition-field
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: feature-ranking-credible-window-utility
depends_on: [feature-ranking-credible-window-utility-horizon-clamp]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Cold-start transition field

## Brief

Implement Unit 2 of the parent feature: construct the exact observed post-ban field plus a bounded,
decaying, affectedness-filtered preceding-regime prior with fully reconciled provenance.

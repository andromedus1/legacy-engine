---
id: feature-ban-localized-evidence-recovery-exposure-authority
kind: story
stage: drafting
tags: [analytics, testing]
parent: feature-ban-localized-evidence-recovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-17
updated: 2026-08-16
---

# Exposure-boundary authority and localized clean-interval atoms

## Brief

Implement Unit 1 of the parent feature: add a typed exposure-boundary authority for localized bans
so materially affected entities can contribute clean pre-exposure and post-ban intervals while the
contaminated exposure span remains explicitly excluded.

For the forcing case, Fantasticar exposure is `2026-06-20` through the `2026-08-10` ban. The
implementation must generalize beyond that one card and preserve deterministic provenance for how
each bound was chosen.

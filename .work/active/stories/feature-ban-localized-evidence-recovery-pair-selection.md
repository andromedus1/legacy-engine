---
id: feature-ban-localized-evidence-recovery-pair-selection
kind: story
stage: drafting
tags: [analytics, advisory, testing]
parent: feature-ban-localized-evidence-recovery
depends_on: [feature-ban-localized-evidence-recovery-exposure-authority]
release_binding: null
gate_origin: null
created: 2026-08-17
updated: 2026-08-16
---

# Pairwise localized selection and evidence-view recovery

## Brief

Implement Unit 2 of the parent feature: feed localized clean-interval authority into exact
pairwise selection and report evidence views so unaffected parent pairs keep compatible history,
affected edges exclude only contaminated exposure intervals, and camps remain current-only.

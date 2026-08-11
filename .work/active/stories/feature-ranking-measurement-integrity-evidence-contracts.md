---
id: feature-ranking-measurement-integrity-evidence-contracts
kind: story
stage: implementing
tags: [analytics, advisory, honesty]
parent: feature-ranking-measurement-integrity
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Pair-window and concentration evidence contracts

## Brief

Make current build/camp comparison windows outcome-blind and attach additive event/month
concentration evidence to the exact matchup cells selected from those windows.

## Implementation

Implements Unit 1 of the parent feature's `## Implementation Units`: pair-window clamping,
directed event/month tallying, concentration metadata, and single/multi adaptive parity.

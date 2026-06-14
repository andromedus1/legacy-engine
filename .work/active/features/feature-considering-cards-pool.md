---
id: feature-considering-cards-pool
kind: feature
stage: drafting
tags: [generation, advisory]
parent: epic-bigmana-coverage-sideboard-fidelity
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Emit a ~30-card "considering" pool, not just the final 15

## Brief
Deck/sideboard generation emits only the final 15. Surface a larger (~30-card) "considering" pool — the
flex options and meta-call alternatives the engine weighed (next-best by coverage/value, ranked, labeled)
— so the user sees what was on the bubble. Additive output on the sideboard recommender / `advise refresh`
/ `advise acquire` surfaces; the chosen 15 is unchanged.

---
id: gate-patterns-fix-gate-predicate-style
kind: story
stage: drafting
tags: [refactor]
parent: null
depends_on: []
release_binding: null
gate_origin: patterns
created: 2026-07-04
updated: 2026-07-04
---

# Normalize maindeck_coverage gate to the 'is not None' predicate convention

## Divergence
sideboard.py:1842 uses `if maindeck_coverage:` (truthiness) while sibling gated steps (matchup_pressure :1823, opponent_linchpins :1742) use `if X is not None:`. Functionally equivalent (empty dict no-ops) but style-divergent within one pipeline.

## Fix
Normalize to the documented predicate form (behavior-preserving; black-box test passes). One-line change + no test churn.

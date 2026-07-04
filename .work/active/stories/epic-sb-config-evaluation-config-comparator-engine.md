---
id: epic-sb-config-evaluation-config-comparator-engine
kind: story
stage: done
tags: [advisory]
parent: epic-sb-config-evaluation-config-comparator
depends_on: []
release_binding: v0.2.0
gate_origin: null
created: 2026-06-29
updated: 2026-06-29
---

# Config comparator engine (model + point EV + MC base + slot-lift pull)

## Brief
The pure(-ish) engine in `src/legacy_engine/advisory/compare.py`: the `ConfigMode` / `DeckConfig`
model, `compare_configs(matrix, field, a, b)` returning a `ComparisonResult` (point-estimate field
EV per config, per-matchup contribution diff, the Bayesian-MC base layer with CIs + P(A>B), and the
break-even solve), plus the `slot_lift` helper that pulls a measured diff from Piece 1's
`card_matchup_contrast`. The slot-test dependency is already merged to main.

## Implementation
Covers Units 1-3 of the parent feature
`.work/active/features/epic-sb-config-evaluation-config-comparator.md`:
- Unit 1: config model + point-estimate engine (max-over-modes base WR, lift overlay, break-even).
- Unit 2: Bayesian-MC base layer (generalizes positioning's `_sample_S` to multi-mode `max` + two
  configs with shared per-draw cell draws; P(A>B), CIs).
- Unit 3: `slot_lift` auto-pull helper.

Tests: `tests/advisory/test_compare.py` (hand-built matrix/field; point EV, transform max +
chosen_mode, lift mode-flip, break-even ahead/feasible/infeasible, coverage/imputation; seeded MC
determinism, dominating→P≈1, identical→P≈0.5, CI shrinks with n; `slot_lift` diff + None).

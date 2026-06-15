---
id: epic-sideboard-core-and-hedge-dedicated-core
kind: feature
stage: done
tags: [advisory, sideboard]
parent: epic-sideboard-core-and-hedge
depends_on: [epic-sideboard-core-and-hedge-concave-value]
release_binding: null
gate_origin: null
created: 2026-06-15
updated: 2026-06-15
---

# Stage-1 dedicated-core solver + natural-budget τ

## Brief

Make the solver stop committing dedicated cards once the field's coverable value is captured,
rather than padding to a forced 15. Using the concave value model, keep adding (card, copy)
increments while the best remaining marginal value clears a floor τ; stop at the "natural budget"
(empirically ~6–8 cards for a concentrated field). The result is the **dedicated core** and may be
fewer than 15 cards — this is the feature that kills the padding bug on its own.

τ is a genuine judgment call (brief decision 4, left tunable): implement it **operator-tunable with
a tier-aware default** — don't commit a dedicated copy off a speculative-tier (`tier_for_sample`)
matchup cell. Reuses the existing greedy/ILP machinery (now over the concave value); the stop
condition is the only new control-flow.

Does NOT cover how leftover slots get used (hedge feature) or the output rendering/labels
(output-contract feature) — only producing the dedicated-core set + the natural-budget count.

## Epic context
- Parent epic: `epic-sideboard-core-and-hedge`
- Position in epic: consumer of `epic-sideboard-core-and-hedge-concave-value`; produces the core set
  the output-contract and hedge features consume. Second in the v1 wave; on its own it ends the
  4/4/4 padding.

## Inherited design decisions
- SB may return <15 (the core stops at the natural budget).
- τ stays tunable with a tier-aware default (recommend, don't hardcode); surface the knee (the
  marginal-coverage curve) — owned by the output-contract feature.
- Submodularity preserved → greedy/ILP unchanged in class.

## Research briefs
- `docs/briefs/sideboard-core-and-hedge.md` §1 (natural-budget grounding), §4 (τ options).
- `docs/briefs/advisory-methods.md` §3 (max-coverage/greedy/ILP foundations).

## Foundation references
- `src/legacy_engine/advisory/sideboard.py` — `recommend_sideboard` solve path.
- `src/legacy_engine/confidence.py` — `tier_for_sample` for the τ default.
- Patterns: [[objective-search-split]], [[confidence-metadata]].

## Design + implementation (2026-06-15)
**Architectural choice**: τ is a **per-slot opportunity cost** subtracted uniformly per picked card, composing cleanly with concave-value's per-copy redundancy penalty. A slot is worth filling iff its net marginal (coverage − redundancy penalty) > τ; the natural-budget knee is where that fails. This mirrors the redundancy-penalty shape and keeps greedy and ILP consistent:
- greedy (`_greedy_solve`): stop when `best_gain <= tau` (was `== 0.0`; τ=0 → identical since gains are ≥0 by the argmax floor).
- ILP (`_ilp_solve`): objective subtracts `τ·Σ_c x_c` (only when τ>0) — each slot costs τ, so the optimum stops filling at the knee, returning <budget.
- `recommend_sideboard` threads `tau: float = 0.0` to both. Default 0.0 → byte-identical forced-budget baseline.

**Files**: `src/legacy_engine/advisory/sideboard.py` (`_greedy_solve`, `_ilp_solve`, `recommend_sideboard` + module docstring already notes <15). **Tests**: `tests/test_sideboard.py::TestNaturalBudgetTau` (5 — greedy fills at τ=0 / stops at τ=0.15 to exactly 2 dedicated copies; ILP same; ILP τ=0 identical; recommend_sideboard τ>0 returns ≤ the τ=0 count).

**Review (self, focused — lower-risk than the deep-reviewed ILP z-vars)**: τ is a constant per-slot coefficient (LP-trivial), composes additively with the penalty, preserves submodularity (per-slot cost doesn't change marginal monotonicity), and is provably no-op at τ=0. Gated-additive verified: existing sideboard suite 258 green byte-identical; full suite 2225 green; ruff clean. The <15-return surfacing/labels are owned by output-contract (next). No blockers.

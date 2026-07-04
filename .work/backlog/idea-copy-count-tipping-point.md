---
id: idea-copy-count-tipping-point
created: 2026-07-04
tags: [advisory, sideboard, analytics]
---

# Copy-count tipping point — winners run fixers at 0 or 2+, our solver produces 1-ofs

Andrew's observation (2026-07-04, reviewing the optimized-board analysis): winners don't usually run
**1-of "fixers"** (reactive answers like Dauthi Voidwalker, Engineered Explosives, Toxic Deluge).
Hypothesis: humans apply a **tipping point** — once a card is worth including at all, 1 copy is too
hard to draw to meaningfully impact the outcome, so the real decision is 0 vs 2+. Our board carries
many engine-produced 1-ofs (the natural-budget flexible tier), a visible divergence from winning
boards.

**Why our model would systematically produce this:** the per-copy value curve
(`_u_redundancy` from the hypergeometric marginal: 1.0, 0.61, 0.37, 0.22) is **purely concave** —
the 1st copy is always the best buy — so the solver spreads 1-ofs across axes. If the true value of
REACTIVE answers is **thresholded/S-shaped** (you must draw it in the ~2-3 games where it's live,
on time), copy 1 may sit below a usefulness cliff and copy 2 above it. Likely **category-dependent**:
domain literature (sb-construction-fusco attestation) says dedicated swap packages run 3-4-of while
*flexible* one-ofs are legitimate — so the threshold may apply to time-sensitive fixers but not to
broad insurance (FoN-style). Also interacts with the option-value bonus (first-copy-only), which
further subsidizes 1-ofs.

**The data test (Andrew: "this should be visible in our data"):**
- Per SB card (or per category: reactive-fixer vs broad-counter vs dedicated-hate), compute the
  **copy-count histogram among top-finisher boards** — 0x/1x/2x/3x/4x, per the
  frequency-distribution-detail presentation preference — and test for bimodality (a valley at 1).
- Compare against the solver's produced copy distribution on the same fields (the archetype sweep
  generates exactly this corpus) — divergence-as-diagnostic, per the codified pattern.
- The backtest's `observed_frequency` is presence-only today; extend it (or the sweep report) to
  copy-count distributions so this class of divergence is visible at all.

**Modeling implication if confirmed:** a per-category minimum-viable-count (integer constraint: x_c
∈ {0} ∪ [k_min, max]) or an S-shaped per-copy curve for fixer-class cards, replacing pure concavity.
Keep pure-mechanics: derive the threshold from draw-math (P(draw by the turn the answer must land)
in live games), not from copying winners.

**Home:** natural sub-question of [[feature-archetype-sweep-backtest]] (the sweep should collect
copy-count histograms, not just presence) feeding the scorer as a follow-up fix. Related:
idea-ilp-tiebreak-nondeterminism (determinism for reproducible sweeps).

---
description: Read when modeling per-copy sideboard value or questioning the concave taper — the distribution-first empirical study of winners' copy-count histograms from the archetype sweep.
type: brief
kind: research
status: complete
updated: 2026-07-04
summary: |
  Distribution-first study of per-card sideboard copy-count distributions among top-finisher
  boards (archetype-sweep payloads, 2026-07-04: 26 archetypes, 293 top-finisher decks global /
  153 local-field-scoped). Tests idea-copy-count-tipping-point's "winners run fixers at 0 or 2+"
  hypothesis against the solver's pure-concave per-copy taper.
key_findings:
  - "The 0-or-2+ tipping point is CARD-MECHANIC-SPECIFIC, not category-wide: the hypothesis as stated is NOT supported for reactive fixers as a class (winners run them 53-60% as 1-ofs, concave-decreasing — engine 1-ofs are legitimate there)."
  - "Hard valley-at-1 exists for pitch-fueled counters — Consign to Memory P(1)=0.04-0.06 vs P(2)=0.59-0.65; Force of Negation & Mindbreak Trap mode-at-2 — cards whose alternate cost pitches a copy mechanically want a second copy as fuel; derivable from oracle text (pure-mechanics compliant)."
  - "Threshold cards are near-degenerate at the top: Leyline of the Void P(4)=0.83 ('begin the game in play' = opening-hand math wants 4); sideboard Show and Tell 100% 4-of (plan cards, not answers)."
  - "Category PMFs conditional on inclusion (global): broad-counter mode-at-2plus (P2=.54); color-blast, reactive-fixer, dedicated-hate concave-decreasing — the current concave taper is empirically right for 3 of 4 classified categories."
  - "Solver-vs-winners divergence concentrates where predicted: 42-45% of solver broad-counter picks are 1-ofs where winners' mode is 2+; only 17% for color-blasts."
  - "Modeling implication: per-card minimum-viable-count derived from MECHANICS (pitch-cost cards k_min=2; opening-hand threshold cards k_min≈4), not a category S-curve and never copied from winners' frequencies — feeds the rules-engine arc (idea-card-semantics-rules-layer)."
  - "Shapes replicate across the global and local-field-scoped payloads (robustness); most archetype winner samples are speculative-tier (n<30), honestly labeled — treat per-card PMFs with n>=20 as the reliable floor."
---

# Copy-count distribution study — winners' sideboard copy histograms vs the concave taper

**Question** ([[idea-copy-count-tipping-point]]): winners allegedly run reactive "fixers" at 0
or 2+ copies while our solver produces 1-ofs — is the per-copy value curve's pure concavity
(`_u_redundancy`: 1.0, 0.61, 0.37, 0.22) empirically wrong?

**Method** (distribution-first, per the idea's methodology addendum + ds-engine EDA
inventory §2 caveats): characterize the OBSERVED distributions before choosing any model
form. Inputs: the archetype-sweep `--json` payloads (2026-07-04; determinism-fixed solver,
PR #35): 26 swept archetypes, 293 top-finisher decks (global field) / 153 (local-field-scoped).
Copy-count PMFs are conditional on running the card at all (0x reported separately as
zero-inflation); no normality/dip p-values on support {1..4} — shapes are tabulated
directly, per-category and per-card (n≥20 floor). Study script:
`scratchpad/copy_count_study.py` (session artifact; reproducible from any sweep JSON).

## Results

### Category level (conditional on inclusion, global payload)

| category | n_decks | P(1) | P(2) | P(3) | P(4) | shape |
|---|---|---|---|---|---|---|
| broad-counter | 389 | .257 | **.535** | .157 | .051 | mode-at-2plus |
| color-blast | 234 | **.474** | .342 | .158 | .026 | concave-decreasing |
| dedicated-hate | 592 | **.534** | .314 | .069 | .083 | plateau (4x bump = Leyline) |
| reactive-fixer | 116 | **.603** | .353 | .043 | .000 | concave-decreasing |

The hypothesis as stated — reactive fixers are 0-or-2+ — is **not supported**: winners run
reactive fixers as 1-ofs 60% of the time they run them at all. The engine's 1-of flexible
tier is *legitimate* for that class. The concave taper is empirically right for 3 of 4
classified categories.

### Card level — where the valley at 1 is real

| card | n | P(1) | P(2) | P(3) | P(4) | mechanism |
|---|---|---|---|---|---|---|
| Consign to Memory | 136 | .044 | .647 | .235 | .074 | pitch-adjacent redundancy (the local meta: .062/.593) |
| Dismember | 57 | .140 | .684 | .175 | .000 | cheap-life-cost redundancy |
| Force of Negation | 96 | .302 | .667 | .031 | .000 | pitch cost — a copy IS the fuel |
| Mindbreak Trap | 57 | .281 | .509 | .211 | .000 | free-window timing wants multiples |
| Leyline of the Void | 42 | .000 | .071 | .095 | **.833** | opening-hand-only effect → 4-of or bust |
| Show and Tell (SB) | 24 | .000 | .000 | .000 | **1.000** | plan card, not an answer |

### Solver vs winners (same card, n≥20; per archetype recommendation)

| category | pairs | solver 1-of where winners' mode ≥2 |
|---|---|---|
| broad-counter | 31 | **42%** (the local meta payload: 45%) |
| dedicated-hate | 31 | 29% |
| unclassified | 10 | 30% |
| color-blast | 18 | 17% |

The divergence concentrates exactly where the observed valley-at-1 lives: free/pitch
counters. Examples: Mindbreak Trap solver=1x everywhere vs winners' mode 2; Dauthi
Voidwalker solver=1x vs mode 2; Force of Vigor (pitch!) solver=1x vs mode 2-3. Counter-
example validating the solver: Consign to Memory is already mostly recommended at 2 (the
option-value bonus + coverage stack there), matching winners.

## Modeling implication (for the follow-up feature, not applied here)

A per-card **minimum-viable-count** integer constraint (x_c ∈ {0} ∪ [k_min, cap]) where
k_min is derived from MECHANICS, never from winners' frequencies (pure-mechanics
guardrail — winners' PMFs above are the diagnostic that motivated the mechanic hunt, not
the parameter source):

- **Pitch/alternate-cost cards** ("you may exile a blue card from your hand" /
  "rather than pay") → k_min = 2 — the second copy is the fuel; P(draw both) math.
- **Opening-hand threshold cards** ("begin the game … in your opening hand") → k_min ≈ 4
  from the hypergeometric opening-hand probability the card's whole function depends on.
- Everything else keeps the existing concave taper — empirically correct.

Both triggers are oracle-text-derivable → natural early consumer of the rules-engine arc
([[idea-card-semantics-rules-layer]]); tracked as the promoted feature
`feature-min-viable-copy-count`.

## Honesty notes

- Most archetype winner samples are speculative-tier (n<30); per-card PMFs use a n≥20
  pooled floor and are listed with n. Self-selection + metagame-lag confounds apply (see
  `advisory/backtest.py` module docstring) — these distributions describe what winners
  RAN, not what is correct.
- Shapes replicate across global and local-field-scoped payloads (field-scoping robustness).
- The `unclassified` category (1210 deck-entries — the largest) reflects the hoser-catalog
  tag gap, tracked separately; its aggregate shape (concave) may mask subgroup structure.

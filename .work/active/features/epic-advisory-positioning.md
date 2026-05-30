---
id: epic-advisory-positioning
kind: feature
stage: drafting
tags: [advisory]
parent: epic-advisory
depends_on: [epic-advisory-field-model]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Meta-Positioning Score (Bayesian Monte-Carlo)

## Brief
The differentiator metric: **`S(D) = Σ_a w_a · winrate(D vs a)`** — a deck's expected win rate against the
weighted field (the best response to a fixed field). Compute it with **Bayesian Monte-Carlo** as the primary
uncertainty method: per draw, sample each matchup cell `p_a ~ Beta(x_a+½, (n_a−x_a)+½)` (mirror fixed 0.5),
sample shares `w ~ Dirichlet(counts+γ)`, recompute `S = Σ w_a p_a`; report posterior **mean + percentile
credible interval**. Keep the closed-form delta-method `Var(S)=Σ w_a²·p̂(1−p̂)/n` as a fast inline sanity
check. Always report `S(D)` **alongside** the unweighted aggregate `Ū(D)` (the best-deck-vs-best-call
payload). Rank candidate decks under uncertainty via **shared-field MC draws** (one sampled field per
iteration, score all decks against it) → **probability-of-being-best `P(S_D=max)`**, plus `S±CI` and
pairwise `P(S_A>S_B)`; offer a `--risk-averse` lower-quantile ranking.

Consumes the done `matchup-matrix` (`MatchupCell` `{wins, n, ...}`) for the Beta cells and the
`field-model` `FieldDistribution` for `w`/Dirichlet counts. Honors the n<30 display gate and confidence
tiers on reported numbers.

Does NOT recommend a sideboard (`sideboard`), classify proactivity/vulnerability (`whattoplay`), or render
the combined report (`report`).

## Epic context
- Parent epic: `epic-advisory`
- Position in epic: consumer of `field-model` + the done `matchup-matrix`; producer of `S`/ranking that
  `report` surfaces. Parallel to `whattoplay`.

## Inherited design decisions
- **Bayesian MC primary** (Beta cells + Dirichlet shares), delta-method as fast check; rank by
  **P(best)** from shared-field draws; report `S` **and** unweighted `Ū` (best-call vs best-deck).
- **Mirror at field share, p=0.5 zero-variance** in the headline score; offer an exclude-self secondary view.
- **Confidence-gate everything**; matchup cells already carry Wilson CI + shrinkage + n<30 gate (reuse, don't recompute).

## Research briefs
- `docs/briefs/advisory-methods.md` — §2 (the full positioning method: S(D), MC uncertainty, custom field,
  best-deck vs best-call worked example, ranking by P(best)).

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/positioning.py`; `PositioningResult` model; `analytics/matchup.py`.
- `docs/PRINCIPLES.md` — #7 confidence-gate every stat.

<!-- feature-design fills in: positioning_score/rank_decks signatures, the MC engine, PositioningResult, test approach. -->

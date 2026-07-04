---
id: feature-sfv-weights
kind: feature
stage: drafting
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Element-weight repair: remove draw-prob deflation; make _hate self-protection coverable

## Brief

Repair the element-weight distortions that deflate real coverage and let uncoverable needs crowd it out. (1) Remove the uniform `draw_prob(1)≈0.4` deflation from the *element weight* impact multiplier (it belongs only in the per-copy taper, not in the element's base weight) — folds idea-scorer-element-weight-drawprob. (2) Represent protective/counter-hoser cards (Veil of Summer, Defense Grid, Carpet of Flowers, …) so the dominant `_hate:` self-protection pseudo-elements become **coverable** — turning dead crowding weight into real, servable coverage. Preserve byte-identical behavior where inputs are absent (honest-degrade). Prerequisite for breadth-objective: aggregation is meaningless while the weights it sums are deflated/crowded.

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: foundation — no deps; prerequisite for breadth-objective; parallel with attachments

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). Addresses root causes #2 (deflation) and #3 (_hate crowding). Folds idea-scorer-element-weight-drawprob.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + Boulder field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

---
id: feature-sfv-option-value
kind: feature
stage: drafting
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: [feature-sfv-breadth-objective]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Option value: CVaR tail-robustness over the Dirichlet field

## Brief

Add the pure-mechanics flexibility-under-uncertainty lever: a card that answers many archetypes hedges *which* matchups actually appear, so it has lower-variance value across draws of the uncertain (Dirichlet) field. Add a **CVaR-style tail-robustness objective term** — score a board/card by its coverage in the worst-tail field draws (reuse the Dirichlet from advisory/positioning.py; closed-form Beta-marginal preferred over Monte-Carlo for determinism) — with a tunable risk-appetite dial α (α→1 = tune to the expected field; small α = hedge the field you fear). This is the mechanism that lets the engine value flexibility from uncertainty (not just observed breadth) and **see past consensus** — with zero empirical winning-board input. Keep it a strictly separate axis from the copy-count draw-probability taper to avoid re-introducing deflation.

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: additive modeling term on the repaired objective — depends on breadth-objective

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). The novel 'see-further' lever; grounds on the brief's CVaR / expected-shortfall section. Keep separate from the copy-taper axis.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + Boulder field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

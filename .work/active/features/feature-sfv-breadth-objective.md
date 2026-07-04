---
id: feature-sfv-breadth-objective
kind: feature
stage: drafting
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: [feature-sfv-attachments, feature-sfv-weights]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Breadth aggregation: reformulate the coverage objective to true submodular marginal-gain (TRICKIEST)

## Brief

The core, highest-leverage change: reformulate `_build_coverage_model` + the ILP/greedy objective so a card is credited by its **total marginal coverage across every element it answers** (true submodular marginal gain), rather than the current per-element form that fragments a flexible card's value into tiny pieces. This is where a flexible catch-all like Force of Negation earns a slot on breadth, as submodular coverage theory prescribes (inherits the 1−1/e greedy guarantee). **feature-design must force 2-3 concrete architectural sub-options** (e.g. recompute greedy marginal-gain as a sum over newly-covered elements vs restructure the ILP linearization vs a coverage-set reformulation) and pick one with rationale. Keep the natural-budget τ / hedge machinery; do not regress the reviewed scorer where breadth isn't the issue.

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: the epic's core — depends on attachments (cards must attach) + weights (weights must not be deflated) before breadth can aggregate

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). Addresses root cause #1 (breadth never aggregates) + the locked 'reformulate to true submodular marginal-gain' decision. The trickiest unit; design it first and most carefully.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + Boulder field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

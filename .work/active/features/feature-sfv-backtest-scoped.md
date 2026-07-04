---
id: feature-sfv-backtest-scoped
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

# Field/window-scoped backtest as the acceptance harness

## Brief

Enhance `advise backtest` (advisory/backtest.py) to be filterable to a **field + time window** so validation is Boulder-specific rather than global all-time Dimir (670 decks polluted by graveyard-meta tech like Surgical/Grafdigger's that isn't right for Boulder). This is the epic's **acceptance/regression oracle**: it should let us confirm FoN/Consign move winners-only→overlap and the Damping Sphere false-positive drops, scoped to the actual field the fixes target. Land early (no deps) so the other features validate against it. Frame divergence as a signal to investigate, never a pass/fail verdict (unchanged from the shipped backtest ethos).

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: acceptance harness — no deps; land early so attachments/weights/breadth/option-value validate against it

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). Sharpens the backtest from global-Dimir to field-scoped (the brief's caveat). The epic's acceptance gate.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + Boulder field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

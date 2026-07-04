---
id: feature-sfv-attachments
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

# Attachments: plays-<color> as opponent vulnerability + broad-interaction attribution + missing counters

## Brief

Make flexible cards actually *attach* to the field needs they answer — coverage credit requires connection. Fix `_color_contingent_tags` (advisory/whattoplay.py) so `plays-<color>` fires as an **opponent** vulnerability (a blue opponent is vulnerable to `plays-blue` interaction), not only for the deck's own protection. Add a **broad-interaction attribution** so free/flexible counters attach to the whole combo/control plurality they answer rather than a couple of tiny `combo` elements. Add the missing catalog entries (Force of Negation, Spell Pierce, Mystical Dispute) to `data/hosers/legacy.json` with correct attribution against the new axis. Foundation for the breadth-objective feature — without correct attachments, submodular marginal-gain has nothing to aggregate.

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: foundation — no deps; prerequisite for breadth-objective

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). Addresses root causes #1 (missing attribution) and #2 (plays-blue never fires as opponent vuln). Folds idea-hoser-catalog-missing-blue-and-fon.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + Boulder field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

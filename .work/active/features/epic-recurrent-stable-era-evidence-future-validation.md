---
id: epic-recurrent-stable-era-evidence-future-validation
kind: feature
stage: drafting
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence
depends_on: [epic-recurrent-stable-era-evidence-amplification]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Future-only recurrent and amplified methodology validation

## Brief

Create a new immutable benchmark protocol version that refits discovery, certification, interval
consumption, and every challenger strictly inside each historical origin. Compare current-only,
contiguous-era, recurrent-expanded, and amplified estimators over identical future events using
proper scores, calibration, coverage, interval behavior, and decision regret.

Define promotion as useful coverage gain without material degradation in predictive or decision
quality. Historical protocols and their exact estimator registries remain immutable; negative,
inconclusive, and support-censored results are valid outcomes. Promotion changes configuration only
through explicit operator authority and never occurs because a challenger merely reports more data.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: independent falsification and promotion gate over the shared challenger
  contracts; can proceed in parallel with report integration.

## Inherited design decisions

- Every origin discovers and certifies using only cutoff-available information.
- The objective is improved future calibration/proper score/decision regret, not nominal sample size.
- Sticky-state and other complex recurrence models participate only as explicit challengers.
- Methodology promotion is operator-controlled and creates a new versioned production configuration.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — chained validation and promotion
  requirements.
- `.research/analysis/campaigns/recurrent-era-intervals/specialists/consume-validate.md` — cutoff-refit
  validation design.
- `docs/analysis/best-call-ranking.md` — frozen benchmark protocol and current evidence status.

## Foundation references

- `docs/SPEC.md` — future-only ranking benchmark and recurrent promotion boundary.
- `docs/ARCHITECTURE.md` — immutable benchmark artifacts and cutoff-safe workflows.
- `docs/PRINCIPLES.md` — confidence gating and data-driven claims.


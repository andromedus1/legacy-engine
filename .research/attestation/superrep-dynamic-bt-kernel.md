---
source_handle: superrep-dynamic-bt-kernel
fetched: 2026-08-01
source_url: https://proceedings.mlr.press/v108/bong20a/bong20a.pdf
provenance: source-direct
substrate_confidence: source-direct
---

# Nonparametric Estimation in the Dynamic Bradley-Terry Model

## Summary

Bong, Li, Shrotriya, and Rinaldo construct a time-varying Bradley–Terry estimator by kernel-smoothing
pairwise observations over time before fitting a ranking at each time point. The bandwidth controls
the amount of temporal borrowing. Their analysis permits sparse and irregular comparison designs,
but consistency depends on design regularity and smooth temporal change. Experiments tune bandwidth
by leave-one-out cross-validation and show smoother, more accurate rankings than static alternatives
in their simulated sparse settings, including a model-agnostic setting.

The authors also state an important limitation: an estimator optimized for smooth paths and
predictive accuracy may miss changes in rankings. The construction smooths observations from all
time periods around an evaluation time, so it is a retrospective smoother as written rather than a
causal boundary forecast.

## Key passages

> “Kernel smooth the pairwise comparison data across all time periods.” — §2, step 1, PDF p. 2

> “The higher the value of h is, the smoother” — §2, bandwidth description, PDF p. 2

> “the impact of the design on the estimation accuracy needs to be assessed on a case-by-case basis.” — Remark 3, PDF p. 5

> “it may fail to capture some changes in rankings” — Remark 6, PDF p. 7

## Structural metadata

Primary conference paper, AISTATS 2020, PMLR volume 108, pages 3317–3326. Full PDF fetched. The
paper models time-varying global rank, not non-transitive matchup-specific effects or changing group
membership.

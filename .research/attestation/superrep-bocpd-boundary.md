---
source_handle: superrep-bocpd-boundary
fetched: 2026-08-01
source_url: https://arxiv.org/abs/0710.3742
provenance: source-direct
substrate_confidence: source-direct
---

# Bayesian Online Changepoint Detection

## Summary

Adams and MacKay derive an online Bayesian filter over run length, the elapsed time since the most
recent changepoint. At each boundary it combines run-length-specific predictive distributions using
the posterior probability of those run lengths. The formulation consumes only observations through
the present boundary and represents uncertainty about whether a new regime has begun rather than
forcing a single retrospective segmentation.

The paper assumes that generative parameters on opposite sides of a changepoint are independent.
That reset assumption is useful for guarding against obsolete evidence, but it is not automatically
appropriate when some parameters should persist through a regime change.

## Key passages

> “exact inference of the most recent changepoint.” — Abstract

> “probability distribution of the length of the current ‘run’” — Abstract

> “parameters before and after the changepoint are independent” — Abstract

> “integrate over the posterior distribution on the current run length” — equation (1) discussion, §2

## Structural metadata

Primary methods paper by Ryan Prescott Adams and David J. C. MacKay, arXiv:0710.3742. Full arXiv
HTML was fetched. The paper supplies a temporal filtering construction, not a paired-comparison or
taxonomy model.

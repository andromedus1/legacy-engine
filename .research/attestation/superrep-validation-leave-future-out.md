---
source_handle: superrep-validation-leave-future-out
fetched: 2026-08-01
source_url: https://arxiv.org/pdf/1902.06281
provenance: source-direct
substrate_confidence: source-direct
---

# Approximate leave-future-out cross-validation for Bayesian time series models

## Summary

Bürkner, Gabry, and Vehtari formulate leave-future-out cross-validation for the task of predicting
future observations from past observations. Ordinary leave-one-out cross-validation can use future
information when assessing a prediction for an earlier time and therefore overstate future
predictive accuracy. Exact leave-future-out validation refits at successive historical cutoffs; the
paper's computational contribution is an importance-sampling approximation with diagnostics.

## Key passages

1. When the task is future prediction from the past, ordinary LOO-CV can be overly optimistic because
   future observations influence predictions of the past (p. 1, abstract).
2. Leave-future-out cross-validation preserves the intended temporal information order (pp. 1--2,
   abstract and introduction).
3. LFO-CV describes a family of prediction tasks rather than one universal split; the forecast origin
   and horizon must correspond to the intended use (p. 2, introduction).

## Structural metadata

Primary computational-statistics paper by Paul-Christian Bürkner, Jonah Gabry, and Aki Vehtari,
arXiv:1902.06281. Full twenty-eight-page PDF fetched.

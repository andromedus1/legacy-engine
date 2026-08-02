---
source_handle: superrep-leave-future-out
fetched: 2026-08-01
source_url: https://arxiv.org/abs/1902.06281
provenance: source-direct
substrate_confidence: source-direct
---

# Approximate leave-future-out cross-validation for Bayesian time series models

## Summary

Bürkner, Gabry, and Vehtari distinguish ordinary leave-one-out validation from the actual task of
predicting future observations using only the past. Ordinary LOO lets future observations influence
predictions for earlier points and therefore gives an optimistic performance estimate for temporal
forecasting. Leave-future-out validation preserves the intended information order. The paper also
develops an importance-sampling approximation, but the load-bearing lesson here is the temporal
validation contract rather than that computational shortcut.

## Key passages

> “LOO-CV provides an overly optimistic estimate” — Abstract

> “we can use leave-future-out cross-validation” — Abstract

> “information from future observations is available to influence predictions of the past.” — Abstract

## Structural metadata

Primary computational-statistics paper, arXiv 1902.06281. Abstract and publication metadata fetched.

---
source_handle: recur-certify-covariate-shift
fetched: 2026-08-13
source_url: https://jmlr.csail.mit.edu/papers/volume8/sugiyama07a/sugiyama07a.pdf
provenance: source-direct
substrate_confidence: source-direct
---

## Summary

Sugiyama, Krauledat, and Muller 2007 define covariate shift as a change in the input distribution
while the conditional output distribution given inputs remains unchanged. Under that assumption,
ordinary cross-validation is biased for target risk and importance-weighted cross-validation is
almost unbiased. The result assumes a known training-to-test density ratio in theory; experiments
estimate it, and the authors identify density-ratio estimation and estimator variance as unresolved
practical concerns. The method does not justify transport when the conditional relationship itself
changes.

## Key passages

- Abstract and Section 1, pages 0–1: covariate shift means different training and test input
  distributions but unchanged conditional output distribution; ordinary CV loses unbiasedness and
  importance weighting is proposed to restore it.
- Section 1, page 1: the theoretical development assumes the test-to-training density ratio is
  known; experiments replace it with an estimate.
- Section 3, pages 4–5: validation loss is weighted by the density ratio, and the leave-one-out
  importance-weighted estimator is almost unbiased under the stated conditional-invariance
  assumption.
- Discussion, page 13: almost-unbiased risk estimation does not guarantee good model selection
  because the estimator has variance.
- Discussion, page 13: the effect of replacing the true density ratio with an empirical estimate
  remains to be evaluated, and better density-ratio estimation is an open direction.

---
source_handle: superarchetype-meta-heterogeneity
fetched: 2026-07-31
source_url: https://doing-meta.guide/heterogeneity.html
provenance: source-direct
---

## Summary

The "Doing Meta-Analysis in R" (Harrer, Cuijpers, Furukawa & Ebert) heterogeneity chapter — the
computational recipe behind the Cochrane guidance. It gives Cochran's Q as the inverse-variance-
weighted sum of squared deviations of each unit's effect from the pooled fixed-effect estimate, I² as
(Q − (K−1))/Q, and τ² as the variance of the true underlying effects. Two caveats are stated
explicitly and both bite hard at our sample sizes: Q (and therefore its significance) grows with both
the number of units and their precision, so whether heterogeneity is "detected" depends on the size
of the analysis; and I² is not an absolute measure of heterogeneity because it depends on the
precision of the included units — as units get large, sampling error tends to zero and I² tends to
100% even if the underlying spread is unchanged. Together these mean a low I² on tiny cells is weak
evidence of exchangeability, while a high I² on tiny cells is strong evidence against it.

## Key passages

- Cochran's Q: "Q = ∑ᴷₖ₌₁wₖ(θ̂ₖ−θ̂)²" where wₖ is the inverse-variance weight and θ̂ the pooled
  fixed-effect estimate.
- Q depends on size of the analysis: "Q increases both when the number of studies K, and when the
  precision (i.e. the sample size of a study) increases. Therefore, Q and whether it is significant
  highly depends on the size of your meta-analysis."
- I² formula and meaning: "I² = (Q−(K−1))/Q" representing "the percentage of variability in the
  effect sizes that is not caused by sampling error."
- τ² definition: "τ² quantifies the variance of the true effect sizes underlying our data."
- I² is not absolute: "I² is not an absolute measure of heterogeneity, and its value still heavily
  depends on the precision of the included studies. If our studies become increasingly large, the
  sampling error tends to zero, while at the same time, I² tends to 100%."

---
source_handle: superarchetype-meta-pooling
fetched: 2026-07-31
source_url: https://doing-meta.guide/pooling-es.html
provenance: source-direct
---

## Summary

The "Doing Meta-Analysis in R" chapter on pooling effect sizes — the aggregation estimator itself.
Fixed-effect (common-effect) pooling weights each unit by the inverse of its sampling variance,
w_k = 1/s²_k, and the pooled estimate is the weighted mean of the unit estimates. The random-effects
model adds the between-unit variance to every denominator, w*_k = 1/(s²_k + τ²). The consequence is
the load-bearing behavioural property for a cluster whose matches are dominated by one member: adding
τ² to every denominator compresses the weight ratio between a large unit and a small one, so a
random-effects pool "pays more attention to small studies", and in the limit of large τ² the weights
approach equality regardless of unit size. The chapter also states the model-choice convention — a
fixed-effect model is only defensible when no between-unit heterogeneity is detected AND there is a
strong reason to believe the true effect is identical across units; otherwise use random effects.

## Key passages

- Fixed-effect weight: "w_k = \frac{1}{s^2_k}".
- Pooled estimate: "\hat{\theta} = \frac{\sum^{K}_{k=1} \hat{\theta}_kw_k}{\sum^{K}_{k=1} w_k}".
- Random-effects weight: "w^*_k = \frac{1}{s^2_k+\tau^2}".
- Weight compression: "The random-effects model pays more attention to small studies when calculating
  the overall effect of a meta-analysis."
- Model-choice convention: "In many fields, including medicine and the social sciences, it is
  therefore conventional to **always** use a random-effects model, since some degree of between-study
  heterogeneity can virtually always be anticipated." Fixed-effect use is limited to situations "when
  we could not detect any between-study heterogeneity **and** when we have very good reasons to
  assume that the true effect is fixed."

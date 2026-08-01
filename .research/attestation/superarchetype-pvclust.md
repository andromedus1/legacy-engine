---
source_handle: superarchetype-pvclust
fetched: 2026-07-31
source_url: https://github.com/shimo-lab/pvclust
provenance: source-direct
---

## Summary

pvclust — the reference method for attaching per-branch uncertainty to a hierarchical clustering. It
assesses the uncertainty of a dendrogram by multiscale bootstrap resampling and reports two
quantities per cluster: the BP (bootstrap probability) from ordinary bootstrap resampling and the AU
(approximately unbiased) p-value from multiscale bootstrap resampling, of which AU is the better
approximation to an unbiased p-value. The interpretation rule is explicit: for a cluster with AU
above 0.95, the hypothesis that the cluster does not exist is rejected at the 0.05 level, meaning the
branch is unlikely to be an artefact of sampling error. Crucially for a small-N clustering problem,
the resampling is over the DATA MATRIX ROWS (the variables/features), not over the objects being
clustered — so a dendrogram over a few dozen objects can still be validated as long as the feature
vocabulary is large.

## Key passages

- Purpose: "pvclust is an R package for assessing the uncertainty in hierarchical cluster analysis."
- Two p-values: "pvclust provides two types of p-values: AU (Approximately Unbiased) p-value and BP
  (Bootstrap Probability) value."
- AU superiority: "AU p-value, which is computed by multiscale bootstrap resampling, is a better
  approximation to unbiased p-value than BP value computed by normal bootstrap resampling."
- Interpretation rule: "For a cluster with AU p-value > 0.95, the hypothesis that 'the cluster does
  not exist' is rejected with significance level 0.05; roughly speaking, we can think that these
  highlighted clusters does not only 'seem to exist' caused by sampling error, but may stably be
  observed if we increase the number of observation."

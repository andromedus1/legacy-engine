---
source_handle: cluster-stability-review
fetched: 2026-07-11
source_url: https://pmc.ncbi.nlm.nih.gov/articles/PMC9787023/
provenance: source-direct
---

## Summary

Review of stability estimation for unsupervised clustering. A clustering is represented by a binary
co-membership matrix (1 if two items share a cluster, else 0); a stable clustering preserves its
clusters under resampling/perturbation of the data. Load-bearing numeric thresholds a candidate
split should clear: stability values above 0.9 (Yu et al. 2019; also Tibshirani & Walther 2005), and
prediction-strength thresholds of 0.80–0.90. This is the resampling-based guard against spurious
splits.

## Key passages

- Co-membership: "A clustering can be represented mathematically using a binary co-membership matrix
  with entries of 1 if items i and j belong to the same cluster, and 0 otherwise."
- Stability meaning: "If the clustering is stable, then the clusters from the original data will be
  preserved in the perturbed data clustering."
- Thresholds: "Yu et al. (2019) suggest using stability values above 0.9 for the selection of k
  resulting in k=3 as optimal." and "Empirically, the choice of [prediction-strength] threshold was
  suggested to fall above 0.80 or 0.90."

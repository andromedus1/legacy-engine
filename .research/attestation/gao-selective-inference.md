---
source_handle: gao-selective-inference
fetched: 2026-07-11
source_url: https://arxiv.org/abs/2012.02936
provenance: source-direct
---

## Summary

Gao, Bien & Witten (2024), "Selective Inference for Hierarchical Clustering" (JASA 119(545)). The
load-bearing "double-dipping" warning for validation design: a classical test for a difference in
means controls type I error only when groups are defined a priori; when groups are instead defined
by clustering, the same test's type I error rate is extremely inflated — and this persists even
using two separate independent datasets to define groups vs. test. Directly relevant to "don't
over-split noise": testing whether discovered camps differ on card X with a naive test on the
clustered data overstates significance.

## Key passages

- A priori groups: "Classical tests for a difference in means control the type I error rate when the
  groups are defined a priori."
- Inflation under clustering: "However, when the groups are instead defined via clustering, then
  applying a classical test yields an extremely inflated type I error rate."
- Persists across splits: "Notably, this problem persists even if two separate and independent data
  sets are used to define the groups and to test for a difference in their means."

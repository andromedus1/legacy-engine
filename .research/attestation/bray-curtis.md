---
source_handle: bray-curtis
fetched: 2026-07-11
source_url: https://en.wikipedia.org/wiki/Bray%E2%80%93Curtis_dissimilarity
provenance: source-direct
---

## Summary

Bray-Curtis dissimilarity reference — a count/abundance-aware dissimilarity from ecology, designed
for "count vectors over a shared vocabulary with abundance differences", which maps closely onto
"1x vs 4x of the same card matters". Bounded in [0,1]. Load-bearing caveat: it is NOT a true metric
(fails the triangle inequality), so it must be paired with algorithms that accept a dissimilarity
matrix (agglomerative average/complete linkage, k-medoids) rather than metric-assuming methods.

## Key passages

- Purpose: "the Bray–Curtis dissimilarity is a statistic used to quantify the dissimilarity in
  species composition between two different sites, based on counts at each site."
- Formula: "BC_jk = 1 − 2C_jk/(S_j + S_k) = 1 − 2∑min(N_ij, N_ik)/∑(N_ij + N_ik)".
- Not a metric: "It is not a distance since it does not satisfy triangle inequality, and should
  always be called a dissimilarity to avoid confusion."

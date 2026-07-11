---
source_handle: silhouette-clustering
fetched: 2026-07-11
source_url: https://en.wikipedia.org/wiki/Silhouette_(clustering)
provenance: source-direct
---

## Summary

Silhouette-coefficient reference (internal cluster-validity index). The silhouette value ranges from
-1 to +1, higher meaning better-matched to its own cluster. The Kaufman & Rousseeuw rule of thumb:
average silhouette width over 0.7 is "strong", over 0.5 "reasonable", over 0.25 "weak". The
load-bearing caveat: silhouette is biased toward convex clusters and performs poorly on irregular
shapes / varying sizes — so it is a weak validator for density-based (HDBSCAN) output and a better
fit for k-means/GMM/Ward output.

## Key passages

- Range: "The silhouette value ranges from -1 to +1, where a high value indicates that the object is
  well matched to its own cluster and poorly matched to neighboring clusters."
- Thresholds: "A clustering with an average silhouette width of over 0.7 is considered to be
  'strong', a value over 0.5 'reasonable', and over 0.25 'weak'."
- Convexity bias: "The silhouette score is specialized for measuring cluster quality when the
  clusters are convex-shaped, and may not perform well if the data clusters have irregular shapes or
  are of varying sizes."

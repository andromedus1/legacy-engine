---
source_handle: umap-clustering
fetched: 2026-07-11
source_url: https://umap-learn.readthedocs.io/en/latest/clustering.html
provenance: source-direct
---

## Summary

UMAP-for-clustering reference. UMAP can be an effective preprocessing step to boost density-based
clustering, and for clustering (unlike visualization) one can reduce to ~10 dimensions rather than
2. The load-bearing caution: UMAP does not completely preserve density and can create "false tears"
in clusters — manufacturing finer structure than truly exists. This is the direct reason a
UMAP+HDBSCAN split must clear an independent statistical validation bar before being trusted.

## Key passages

- Preprocessing: "UMAP can be used as an effective preprocessing step to boost the performance of
  density based clustering."
- Density: "The most notable is that UMAP, like t-SNE, does not completely preserve density."
- False tears: "UMAP, like t-SNE, can also create false tears in clusters, resulting in a finer
  clustering than is necessarily present in the data."
- Dimensions for clustering: "One advantage of UMAP for this is that it doesn't require you to
  reduce to only two dimensions – you can reduce to 10 dimensions instead since the goal is to
  cluster, not visualize."

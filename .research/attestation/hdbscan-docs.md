---
source_handle: hdbscan-docs
fetched: 2026-07-11
source_url: https://hdbscan.readthedocs.io/en/latest/parameter_selection.html
provenance: source-direct
---

## Summary

HDBSCAN parameter and behavior reference for the discovery engine. HDBSCAN is a density-based
clustering algorithm that self-determines the number of clusters and labels low-density points as
noise, which is why it is the recommended primary algorithm for subarchetype discovery. Two tuning
parameters govern it. `min_cluster_size` is the smallest grouping to be considered a cluster;
splits producing a smaller group are absorbed rather than promoted. `min_samples` governs
conservatism: larger values push more points to noise and restrict clusters to denser regions, and
it defaults to `min_cluster_size`. A separate FAQ page documents the load-bearing limitation that
HDBSCAN degrades on high-dimensional data (good to ~50-100 dims), which is why it should be run on a
reduced embedding rather than the raw card-vocabulary space.

## Key passages

- min_cluster_size (parameter_selection.html): "set it to the smallest size grouping that you wish
  to consider a cluster".
- min_samples effect (parameter_selection.html): "The larger the value of `min_samples` you
  provide, the more conservative the clustering – more points will be declared as noise, and
  clusters will be restricted to progressively more dense areas".
- min_samples default (parameter_selection.html): "The implementation defaults this value (if it is
  unspecified) to whatever `min_cluster_size` is set to".
- High-dimensional limitation (faq.html — https://hdbscan.readthedocs.io/en/latest/faq.html): "While
  HDBSCAN can perform well on low to medium dimensional data the performance tends to decrease
  significantly as dimension increases." and "In general HDBSCAN can do well on up to around 50 or
  100 dimensional data, but performance can see significant decreases beyond that."

---
source_handle: sklearn-clustering
fetched: 2026-07-11
source_url: https://scikit-learn.org/stable/modules/clustering.html
provenance: source-direct
---

## Summary

scikit-learn clustering reference for four load-bearing facts. (1) The curse of dimensionality:
Euclidean distances inflate in high-dimensional spaces, and running PCA (dimensionality reduction)
before k-means alleviates it. (2) DBSCAN assumes globally homogeneous density and struggles with
clusters of differing density; HDBSCAN removes that assumption by exploring all density scales
(motivating HDBSCAN over DBSCAN). (3) The silhouette coefficient definition. (4) The agglomerative
linkage criteria (Ward, complete, average, single).

## Key passages

- Curse of dimensionality: "in very high-dimensional spaces, Euclidean distances tend to become
  inflated (this is an instance of the so-called \"curse of dimensionality\"). Running a
  dimensionality reduction algorithm such as Principal component analysis (PCA) prior to k-means
  clustering can alleviate this problem and speed up the computations."
- DBSCAN vs HDBSCAN: "DBSCAN assumes that the clustering criterion (i.e. density requirement) is
  globally homogeneous. In other words, DBSCAN may struggle to successfully capture clusters with
  different densities. HDBSCAN alleviates this assumption and explores all possible density scales
  by building an alternative representation of the clustering problem."
- Silhouette: "The Silhouette Coefficient s for a single sample is then given as: s = (b - a) /
  max(a, b)" where "a: The mean distance between a sample and all other points in the same class."
  and "b: The mean distance between a sample and all other points in the next nearest cluster."
- Linkage: "Ward minimizes the sum of squared differences within all clusters. ... Maximum or
  complete linkage minimizes the maximum distance between observations of pairs of clusters. Average
  linkage minimizes the average of the distances between all observations of pairs of clusters.
  Single linkage minimizes the distance between the closest observations of pairs of clusters."

---
source_handle: luckypaper-commander-map
fetched: 2026-07-11
source_url: https://luckypaper.co/articles/mapping-the-magic-landscape/
provenance: source-direct
---

## Summary

Lucky Paper's Commander/Cube Map — the strongest real-world precedent for unsupervised discovery of
play-pattern groups WITHIN a shared context (a commander or cube), fully unsupervised and
human-labeled after the fact. The pipeline is: build a deck-by-card matrix, use Jaccard distance,
reduce with UMAP, cluster with HDBSCAN (chosen for handling clusters of different densities), and
validate qualitatively by checking whether the lists in a cluster share design goals. This is the
exact representation → distance → reduce → density-cluster → human-validate shape recommended for
legacy-engine's discovery engine.

## Key passages

- Matrix: "I constructed a matrix for each dataset, where the rows represent each list and the
  columns represent each card."
- Jaccard: "Eventually, I decided on Jaccard distance, which defines similarity as the number of
  cards shared between two lists divided by the total number of unique cards they contain."
- UMAP: "I settled on Uniform Manifold Approximation and Projection (UMAP) for this project".
- HDBSCAN: "After some tinkering, I settled on an algorithm called HDBSCAN, which is designed to
  handle clusters of different densities."
- Validation: "Luckily for us, it is easy to validate clusters by seeing if the lists share design
  goals."

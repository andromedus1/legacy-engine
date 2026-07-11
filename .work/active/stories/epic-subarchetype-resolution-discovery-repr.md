---
id: epic-subarchetype-resolution-discovery-repr
kind: story
stage: implementing
tags: [analytics, archetype]
parent: epic-subarchetype-resolution-discovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Discovery: flex-band representation + reduction

## Brief
Units 1-2 of the discovery engine (see parent feature body). The DB-free flex-band feature-matrix
builder (`DeckVector`/`FeatureMatrix`, TF-IDF over `[flex_lo, flex_hi]` counts, L2-normalized, sorted
row order) and the injectable `reduce_dims` (TruncatedSVD default seeded; UMAP opt-in). Add
`scikit-learn` + `umap-learn` to `pyproject.toml`.

## Implementation
Parent feature `## Implementation Units` → Unit 1 (build_feature_matrix) + Unit 2 (reduce_dims), in
`src/legacy_engine/analytics/discovery.py`. Tests: `tests/analytics/test_discovery.py` — flex-band
selection, L2 norms, deterministic SVD shape/values (no DB).

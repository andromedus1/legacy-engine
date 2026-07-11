---
id: epic-subarchetype-resolution-discovery-cluster
kind: story
stage: implementing
tags: [analytics, archetype]
parent: epic-subarchetype-resolution-discovery
depends_on: [epic-subarchetype-resolution-discovery-repr]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Discovery: HDBSCAN clustering + two-gate validation + naming

## Brief
Units 3-4 — the trickiest core. `cluster_and_validate` (HDBSCAN on the reduced embedding; Gate A
bootstrap co-membership stability ≥0.9 + silhouette diagnostic; Gate B both-camp evolving tier +
signature divergence via reused `subgroup.diff_compositions`, ≥2 cards |Δ|≥0.75; double-dipping guard;
auto-naming) and the thin DB wrapper `discover_subarchetypes(con, archetype, …)`.

## Implementation
Parent feature `## Implementation Units` → Unit 3 (cluster_and_validate, `DiscoveredSplit`/`Camp`) +
Unit 4 (DB wrapper), in `src/legacy_engine/analytics/discovery.py`. Tests (no DB for Unit 3): clean
2-camp split passes; blob → FAIL "single cluster"; 300/12 → FAIL "below evolving floor"; determinism.
Unit 4 hermetic with a seeded two-camp pool.

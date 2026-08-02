---
source_handle: superrep-evolutionary-clustering
fetched: 2026-08-01
source_url: https://faculty.mccombs.utexas.edu/deepayan.chakrabarti/mywww/papers/kdd06-evolutionary.pdf
provenance: source-direct
substrate_confidence: source-direct
---

# Evolutionary Clustering

## Summary

Chakrabarti, Kumar, and Tomkins formulate clustering over time as a trade-off between snapshot
quality and historical quality. A result should represent current data while avoiding gratuitous
movement from the prior clustering. Their framework modifies k-means and agglomerative clustering
to incorporate temporal history and provides correspondence between clusters at adjacent times.

This establishes temporal continuity as an explicit objective rather than an incidental property.
It also makes the trade-off visible: excessive historical weight can conflict with fidelity to a
real present-day structural change.

## Key passages

> “two potentially conflicting criteria” — Abstract, PDF p. 1

> “faithful to the current data” — Abstract, PDF p. 1

> “should not shift dramatically from one timestep to the next.” — Abstract, PDF p. 1

> “if the structure of the data changes significantly, the clustering must be modified” — §1, PDF p. 1

## Structural metadata

Primary conference paper from KDD 2006, pages 554–560. Author-hosted full PDF fetched. The source
addresses general temporal clustering, not card-game taxonomy or outcome estimation.

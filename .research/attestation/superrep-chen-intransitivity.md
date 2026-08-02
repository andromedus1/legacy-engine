---
source_handle: superrep-chen-intransitivity
fetched: 2026-08-01
source_url: https://www.cs.cornell.edu/people/tj/publications/chen_joachims_16a.pdf
provenance: source-direct
substrate_confidence: source-direct
---

# Modeling Intransitivity in Matchup and Comparison Data

## Summary

Chen and Joachims replace a competitor's single scalar ability with paired multidimensional
representations that encode how its strengths interact with an opponent's vulnerabilities. The
resulting skew-symmetric matchup function preserves the probability-complement relation while
representing cyclic preferences that a scalar Bradley–Terry ordering cannot. The paper proves that
the representation can express any matchup matrix when its dimension is sufficiently large, then
selects dimension and regularization on held-out data and evaluates predictive log likelihood on a
separate test partition.

## Key passages

> “using a single number to represent a player/item can be an oversimplification.” — p.1, Introduction

> “can represent any matchup matrix M” — p.3, Theorem 1

> “M(a, b) = −M(b, a).” — p.2, §3.1

> “the blade and chest vectors are used to capture different styles ... in their offense and defense.” — p.3, §3.2

## Structural metadata

Peer-reviewed WSDM 2016 paper. Full ten-page PDF fetched with page and line anchors.

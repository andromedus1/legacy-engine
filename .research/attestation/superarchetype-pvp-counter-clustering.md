---
source_handle: superarchetype-pvp-counter-clustering
fetched: 2026-07-31
source_url: https://arxiv.org/html/2408.17180v1
provenance: source-direct
substrate_confidence: source-direct
---

## Summary

"Identifying and Clustering Counter Relationships of Team Compositions in PvP Games for Efficient
Balance Analysis" (arXiv 2408.17180) — the closest published analogue to a superarchetype layer over
a metagame matchup matrix. The paper's premise is that the full N×N matrix of pairwise strength
relations between competitor configurations is intractable to build and to read: in their League of
Legends data the space of possible compositions reaches 359,933,112 while only 348,498 distinct
compositions were actually observed, so most pairwise cells are never populated. Their remedy is
structurally identical to the one this epic proposes — quantize the N configurations into M discrete
categories and work with an M×M counter table that approximates the full N×N relationship, reducing
the analysis from O(N²) to O(N+M²). The paper also motivates why a single scalar rating cannot replace
the table: cyclic dominance/intransitivity is a first-class feature of these systems, so grouping must
preserve pairwise structure rather than collapse to a ranking. The paper's claimed gain is
computational tractability of the analysis; it does not itself claim clustering improves estimation
under limited samples.

## Key passages

- Combinatorics of the pairwise table: "the time complexity of validating Proposition 2.2 is 𝒪(N³)
  over N team compositions with a pairwise win value estimation"; direct pairwise prediction "incurs a
  high space complexity, making it challenging to check these ratings and analyze balance, especially
  with a large N."
- Sparsity in real data: in League of Legends the maximum possible compositions reaches 359,933,112,
  yet only 348,498 unique compositions appeared in their dataset.
- The grouped table: "we propose a more manageable M×M counter table that serves as an approximation
  of the full N×N relationships, where M represents a manageable number of discrete categories".
- Complexity reduction: "This approach reduces the space complexity of analyzing strength relations
  for N compositions from 𝒪(N²) to 𝒪(N+M²)".
- Intransitivity: "The phenomenon of cyclic dominance or intransitivity of win values, a common
  challenge in analyzing game balance, introduces further complications".

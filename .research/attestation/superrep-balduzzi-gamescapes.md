---
source_handle: superrep-balduzzi-gamescapes
fetched: 2026-08-01
source_url: https://proceedings.mlr.press/v97/balduzzi19a.html
provenance: source-direct
substrate_confidence: source-direct
---

# Open-ended Learning in Symmetric Zero-sum Games

## Summary

Balduzzi and collaborators treat symmetric zero-sum interactions as antisymmetric functions and
show that such a game decomposes into transitive and cyclic components. A scalar rating difference
describes the transitive component, but it cannot describe the cyclic component. Their empirical
“gamescape” is the convex hull of the rows of a population's evaluation matrix: it preserves each
agent's response profile against the population and represents mixtures as convex combinations.
The construction is invariant to an agent that is behaviorally identical to a mixture of other
agents. Its dimension is controlled by the rank of the antisymmetric evaluation matrix, while long
strategic cycles can require high dimension. The paper uses this geometry to reason about population
performance rather than to estimate noisy binary match probabilities.

## Key passages

- §2, Theorem 1: every functional-form game decomposes into a transitive game and a cyclic game.
- §2.1: a transitive game's performance has the subtractive form `f(v) - f(w)`, making opponent
  choice irrelevant to the optimum; §2.2 contrasts this with cycles where wins against some agents
  are counterbalanced by losses against others.
- §3, Definition 2: the empirical gamescape is the convex set of mixtures of rows of the evaluation
  matrix.
- §3, Proposition 2: the gamescape is invariant to an agent that is behaviorally identical to a
  convex mixture of other agents.
- §3, Proposition 3 and Example 3: gamescape dimension is bounded by evaluation-matrix rank, and
  the longest strategic cycle supplies a lower bound that can approach the population size.
- §4.2: the authors identify a pathological mode with many highly local niches, where each agent
  has a specific exploit that does not generalize.

## Structural metadata

Peer-reviewed ICML 2019 paper in PMLR volume 97, pages 434–443. Full PDF and proceedings page
fetched.

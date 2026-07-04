---
source_handle: max-coverage
fetched: 2026-07-03
source_url: https://en.wikipedia.org/wiki/Maximum_coverage_problem
provenance: source-direct
---

## Summary

The (weighted) maximum coverage problem and its greedy approximation — the concrete template the
sideboard scorer instantiates (pick ≤k cards to maximize the covered weight of field "needs"). The
greedy rule picks, each step, the set covering the most currently-uncovered (weight); it achieves a
(1 − 1/e) approximation, which is essentially best-possible in polynomial time unless P=NP. The
weighted version attaches a weight w(e) to each element and maximizes covered weight — directly
mirroring our `field_share × swing`-weighted archetype/tag elements.

## Key passages

- Problem: "You must select at most k of these sets such that the maximum number of elements are
  covered, i.e. the union of the selected sets has maximal size."
- Greedy rule: "The greedy algorithm for maximum coverage chooses sets according to one rule: at
  each stage, choose a set which contains the largest number of uncovered elements." Weighted: "The
  greedy algorithm for the weighted maximum coverage at each stage chooses a set that contains the
  maximum weight of uncovered elements."
- Guarantee: "It can be shown that this algorithm achieves an approximation ratio of 1−1/e." And:
  "the greedy algorithm is essentially the best-possible polynomial time approximation algorithm for
  maximum coverage unless P=NP."
- Weighted def: "In the weighted version every element e_j has a weight w(e_j). The task is to find
  a maximum coverage which has maximum weight."

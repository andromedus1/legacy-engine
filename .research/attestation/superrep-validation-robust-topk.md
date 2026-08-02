---
source_handle: superrep-validation-robust-topk
fetched: 2026-08-01
source_url: https://jmlr.org/papers/v18/16-206.html
provenance: source-direct
substrate_confidence: source-direct
---

# Simple, Robust and Optimal Ranking from Pairwise Comparisons

## Summary

Shah and Wainwright analyze ranking and top-k recovery from pairwise-comparison probabilities. Their
Borda-style target ranks an item by its probability of beating a uniformly selected opponent. They
derive exact and approximate top-k recovery results without requiring Bradley--Terry--Luce or
stochastic-transitivity assumptions, and show that recoverability depends on the separation between
the kth and (k+1)th targets as well as observation density and repetition.

## Key passages

1. The paper studies both full ranking and top-k identification from pairwise comparisons (official
   abstract).
2. Its robustness guarantees do not require the pairwise matrix to satisfy a BTL model or stochastic
   transitivity (official abstract; PDF pp. 1--2).
3. Exact top-k recovery depends on the separation between the kth and (k+1)th targets relative to
   item count, observation probability, and repetition (PDF p. 6, Theorem 1 discussion).

## Structural metadata

Peer-reviewed *Journal of Machine Learning Research* article by Nihar B. Shah and Martin J.
Wainwright, 2018, volume 18, paper 199, pages 1--38. Official article page and PDF fetched.

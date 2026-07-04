---
source_handle: submodular-set-function
fetched: 2026-07-03
source_url: https://en.wikipedia.org/wiki/Submodular_set_function
provenance: source-direct
---

## Summary

Reference statement of submodular set functions and the key optimization result the
flexibility-valuation brief leans on. A set function f over ground set Ω is submodular iff it
exhibits diminishing marginal returns: adding an element to a smaller set gains at least as much
as adding it to a larger set. Coverage functions (f(S) = size of the union of chosen sets) are a
canonical monotone submodular example. The central algorithmic result: maximizing a monotone
submodular function under a cardinality constraint admits a (1 − 1/e) greedy approximation
(Nemhauser, Wolsey, Fisher 1978). This is what makes a coverage-maximizing scorer *already* the
right shape for crediting breadth — a card covering many needs has large marginal gain — provided
the objective is a genuine coverage function over the full need set.

## Key passages

- Diminishing marginal returns definition: "for every X , Y ⊆ Ω with X ⊆ Y and every x ∈ Ω ∖ Y we
  have that f ( X ∪ { x } ) − f ( X ) ≥ f ( Y ∪ { x } ) − f ( Y )".
- Coverage function: "The function f ( S ) = | ⋃ E i ∈ S E i | for S ⊆ Ω is called a coverage
  function." (listed under monotone submodular examples).
- Greedy guarantee: "The problem of maximizing a monotone submodular function subject to a
  cardinality constraint admits a 1 − 1 / e approximation algorithm." Cited to "Nemhauser, George;
  Wolsey, L. A.; Fisher, M. L. (1978). An analysis of approximations for maximizing submodular set
  functions I."

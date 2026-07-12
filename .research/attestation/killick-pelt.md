---
source_handle: killick-pelt
fetched: 2026-07-11
source_url: https://arxiv.org/abs/1101.1438
provenance: source-direct
---

## Summary

Killick, Fearnhead & Eckley's PELT paper (JASA 107(500):1590–1598, 2012; verified against the
ar5iv HTML render of arXiv:1101.1438). PELT minimizes a penalized sum-of-segment-costs objective
exactly — the pruning that makes it fast does not sacrifice optimality — and under mild conditions
(the number of change points growing linearly with series length) its cost is linear in the number
of observations. The paper is also the canonical citation for the linear penalty family (AIC
β=2p, SIC/BIC β=p·log n) and for the empirical finding that exact search beats Binary
Segmentation's greedy approximation on segmentation accuracy. For legacy-engine's short weekly
series (n≈30–130 points per entity) the complexity difference is irrelevant — the reason to use
PELT is exactness, and the reason to care about the penalty is that it is the false-positive
control knob.

## Key passages

- §1 (Introduction): "We introduce a new method for finding the minimum of such cost functions and
  hence the optimal number and location of changepoints that has a computational cost which, under
  mild conditions, is linear in the number of observations."
- §3: "This pruning reduces the computational cost of the method, but does not affect the
  exactness of the resulting segmentation."
- §2 (Background): "Examples of such penalties include Akaike's Information Criterion (AIC,
  Akaike) (β=2p) and Schwarz Information Criterion (SIC, also known as BIC; Schwarz, 1978)
  (β=p log n)".
- Abstract: "We also compare with the Binary Segmentation algorithm for identifying changepoints,
  showing that the exactness of our approach can lead to substantial improvements in the accuracy
  of the inferred segmentation of the data."
- §3.1 (assumption A3 context): "One important consequence of (A3) is that the expected number of
  changepoints will increase linearly with n."

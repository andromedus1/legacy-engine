---
source_handle: ruptures-docs
fetched: 2026-07-11
source_url: https://centre-borelli.github.io/ruptures-docs/user-guide/
provenance: source-direct
---

## Summary

The ruptures library documentation (user guide, centre-borelli.github.io/ruptures-docs) — the
reference Python implementation of the offline CPD methods in the Truong et al. review. Verified
pages: PELT (pruned exact search, average complexity O(CKn), `min_size` / `jump` /
`pen` controls), Binseg (sequential/greedy splitting, O(Cn log n), three predict modes: `n_bkps`,
`pen`, `epsilon`), kernel change-point detection (linear / Gaussian-RBF / cosine kernels; the
penalized formulation where a larger penalty yields fewer detected change points), and the CostRbf
cost page (non-parametric distribution-change detection; γ set by median heuristic). Load-bearing
negative checked across the cost-function index: ruptures ships NO Poisson/count-family cost —
its costs are L1, L2, Normal, RBF, Cosine, Linear, CLinear, Rank, Mahalanobis-metric,
autoregressive, and custom. Count-rate signals must therefore be variance-stabilized (or use a
custom cost) before an L2-family cost is meaningful.

## Key passages

- PELT page (user-guide/detection/pelt/): the method "relies on a pruning rule" so that "many
  indexes are discarded, greatly reducing the computational cost while retaining the ability to
  find the optimal segmentation"; "the avarage computational complexity is of the order of
  O(CKn), where K is the number of change points to detect, n the number of samples and C the
  complexity of calling the considered cost function on one sub-signal" [sic "avarage"].
- PELT page: "`min_size` controls the minimum distance between change points"; "`jump` controls
  the grid of possible change points"; usage `algo.predict(pen=3)` — `pen` is the penalty weight.
- Binseg page (user-guide/detection/binseg/): "It is a sequential approach: first, one change
  point is detected in the complete input signal, then series is split around this change point,
  then the operation is repeated on the two resulting sub-signals." Complexity: "of the order of
  O(Cn log n)". Predict modes: `predict(n_bkps=3)`, `predict(pen=np.log(n) * dim * sigma**2)`,
  `predict(epsilon=3 * n * sigma**2)`.
- KernelCPD page (user-guide/detection/kernelcpd/): kernels `k_linear(u,v)=u^T v`,
  `k_Gaussian(u,v)=exp(-γ‖u-v‖²)`, `k_cosine(u,v)=(u^T v)/(‖u‖‖v‖)`; penalized formulation
  "V(t_1,…,t_K) + βK" where β>0 is the smoothing parameter and "Higher values of β produce lower
  K̂".
- CostRbf page (user-guide/costs/costrbf/): "is able to detect changes in the distribution of an
  iid sequence of random variables"; "Because it is non-parametric, it is performs reasonably well
  on a wide range of tasks" [sic]; "γ is determined according to median heuristics (i.e. equal to
  the inverse of median of all pairwise distances)."
- Cost-function index (user-guide, costs section): available costs are CostL1, CostL2, CostNormal,
  CostRbf, CostCosine, CostLinear, CostCLinear, CostRank, CostMl, CostAR, plus custom — no
  Poisson-family cost exists.

---
source_handle: recurrent-hallac-ticc
fetched: 2026-08-13
source_url: https://web.stanford.edu/~boyd/papers/pdf/ticc.pdf
provenance: source-direct
source_class: primary-paper
substrate_confidence: source-direct
---

# Hallac et al. — Toeplitz inverse covariance-based clustering

## Summary

Hallac, Vare, Boyd, and Leskovec introduce TICC, a joint segmentation-and-clustering method for
multivariate time series with recurring states. Each cluster is a sparse Gaussian inverse-covariance
model over short windows; a switching penalty encourages adjacent observations to retain their
cluster. The procedure is an EM-like alternating optimization and can reach only a local solution to
the full non-convex objective.

## Key details

1. TICC simultaneously segments a multivariate series and clusters segments into a small set of
   states that may recur. Each state is characterized by a Markov random field over a short window.
   — p. 1, abstract and Figure 1.
2. Its objective combines sparse inverse-covariance likelihood with a penalty whenever adjacent
   windows receive different clusters. The switching penalty therefore controls temporal
   persistence. — pp. 2–3, problem setup, equations 1–2.
3. The inverse covariance is block Toeplitz, encoding a time-invariant dependency structure within
   the selected window. The method assumes Gaussian cluster models and requires choices for
   sparsity, switching penalty, window size, and number of clusters; the paper suggests BIC,
   cross-validation, or application knowledge for these choices. — pp. 2–3.
4. The complete objective is highly non-convex. Alternating minimization can find a locally optimal
   solution but is not guaranteed to find the global optimum. — pp. 1 and 3.
5. The paper's real-data demonstration has 36,000 observations of seven sensors; synthetic
   experiments supply known ground-truth clusters. — pp. 1 and 8.

## Structural metadata

David Hallac, Sagar Vare, Stephen Boyd, and Jure Leskovec, “Toeplitz Inverse Covariance-Based
Clustering of Multivariate Time Series Data,” KDD 2017, pp. 215–223. DOI
10.1145/3097983.3098060. Nine-page author-hosted conference paper.

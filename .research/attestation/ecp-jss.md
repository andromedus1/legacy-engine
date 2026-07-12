---
source_handle: ecp-jss
fetched: 2026-07-11
source_url: https://www.jstatsoft.org/index.php/jss/article/view/v062i07/v62i07.pdf
provenance: source-direct
---

## Summary

James & Matteson, "ecp: An R Package for Nonparametric Multiple Change Point Analysis of
Multivariate Data" (Journal of Statistical Software 62(7), 2014). Quotes verified by direct text
extraction from the JSS PDF. The E-Divisive method estimates multiple change points in
multivariate series by hierarchical bisection on an energy-statistic divergence, with NO
distributional assumptions beyond finite α-th absolute moments and independence — it detects "any
type of distributional change", not just marginal/mean shifts. Two properties are load-bearing for
legacy-engine: (1) significance of each candidate change point is decided by a PERMUTATION test
(approximate p-value #{r: q_r ≥ q_0}/(R+1)) — i.e., a per-change-point p-value exists, which is
what a fleet-level FDR correction needs; (2) the reference implementation's default minimum
segment size is 30 observations (`min.size=30`), an independent precedent for refusing to open a
segment below a defensible sample. Complexity O(kT²) is irrelevant at our T≈30–130. Strong
consistency of the divisive estimates is proven in the companion JASA paper (Matteson & James
2014).

## Key passages

- Abstract: "While many other changepoint methods are applicable only for univariate data, this R
  package is suitable for both univariate and multivariate observations." and "Both approaches are
  able to detect any type of distributional change within the data. This provides an advantage
  over many existing change point algorithms which are only able to detect changes within the
  marginal distributions."
- §2: "The procedures assume that observations are independent with finite αth absolute moments,
  for some α ∈ (0, 2]."
- §2.1: "Székely and Rizzo (2005, 2010) introduce a divergence measure that can determine whether
  two independent random vectors are identically distributed."
- §3 (E-Divisive): "Our approximate p value is then calculated as p̂ = #{r : q_r ≥ q_0}/(R + 1),
  where R is the total number of permutations performed."
- §3: "The signature of the method used to perform analysis based on this divisive approach is
  e.divisive(X, sig.lvl = 0.05, R = 199, k = NULL, min.size = 30, alpha = 1)".
- §3: "The time complexity of this method is O(kT²), where k is the number of estimated change
  points, and T is the number of observations in the series."
- §3: "In the case of independent observations, Matteson and James (2014) show that this procedure
  generates strongly consistent change point estimates."

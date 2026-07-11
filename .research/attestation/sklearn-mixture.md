---
source_handle: sklearn-mixture
fetched: 2026-07-11
source_url: https://scikit-learn.org/stable/modules/mixture.html
provenance: source-direct
---

## Summary

scikit-learn Gaussian-mixture reference. BIC selects the number of mixture components efficiently
but only recovers the true count asymptotically and under the assumption the data is i.i.d. from a
Gaussian mixture. Without an information criterion or held-out data, GMM uses all components it is
given. The load-bearing failure mode for small subarchetype samples: with too few points per
component, covariance estimation breaks down and the EM algorithm diverges to infinite likelihood
unless covariances are regularized.

## Key passages

- BIC component selection: "The BIC criterion can be used to select the number of components in a
  Gaussian Mixture in an efficient way. In theory, it recovers the true number of components only in
  the asymptotic regime (i.e. if much data is available and assuming that the data was actually
  generated i.i.d. from a mixture of Gaussian distributions)."
- Uses all components: "This algorithm will always use all the components it has access to, needing
  held-out data or information theoretical criteria to decide how many components to use in the
  absence of external cues."
- Small-sample divergence: "When one has insufficiently many points per mixture, estimating the
  covariance matrices becomes difficult, and the algorithm is known to diverge and find solutions
  with infinite likelihood unless one regularizes the covariances artificially."

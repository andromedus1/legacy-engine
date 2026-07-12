---
source_handle: bocpd-python-pkg
fetched: 2026-07-11
source_url: https://raw.githubusercontent.com/hildensia/bayesian_changepoint_detection/master/bayesian_changepoint_detection/online_likelihoods.py
provenance: source-direct
---

## Summary

Source-file check of the most commonly cited Python BOCPD package,
`hildensia/bayesian_changepoint_detection` (repo active, last pushed 2025-11; recently refactored
to PyTorch). Load-bearing NEGATIVE finding, verified directly against
`online_likelihoods.py` on master: the package implements ONLY Student-t likelihood models — the
class list is `BaseLikelihood(ABC)`, `StudentT(BaseLikelihood)`, and
`MultivariateT(BaseLikelihood)`. There is no Poisson, Gamma, Beta, Bernoulli, or binomial
likelihood class. Consequence for legacy-engine: do not plan to consume this package for
count/proportion BOCPD; the Poisson–Gamma / Beta–Binomial conjugate recursions must be implemented
in-project (they are small, and the project already carries scipy).

## Key passages

- Class definition lines in `online_likelihoods.py` (master): `class BaseLikelihood(ABC):`,
  `class StudentT(BaseLikelihood):`, `class MultivariateT(BaseLikelihood):` — and no other
  concrete likelihood classes exist in the file.
- Docstrings: "Univariate Student's t-distribution likelihood for online changepoint detection"
  and "Multivariate Student's t-distribution likelihood for online changepoint detection."

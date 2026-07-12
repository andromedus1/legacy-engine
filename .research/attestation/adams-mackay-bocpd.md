---
source_handle: adams-mackay-bocpd
fetched: 2026-07-11
source_url: https://arxiv.org/abs/0710.3742
provenance: source-direct
---

## Summary

Adams & MacKay 2007, "Bayesian Online Changepoint Detection" (arXiv:0710.3742) — the canonical
BOCPD paper; abstract verified against the arXiv abstract page. BOCPD maintains, online, an exact
posterior over the "run length" — the time since the most recent change point — via a simple
recursive message-passing algorithm, with a hazard function encoding the prior probability of a
change at each run length. The framework is modular in the predictive model: any
conjugate/exponential-family likelihood slots in, which is what makes it directly applicable to
weekly deck COUNTS (Poisson–Gamma) and win PROPORTIONS (Beta–Binomial) — the two data types
legacy-engine's disturbance signals produce — without a Gaussian approximation. Its per-week
posterior P(change) output is a natural fit for an honest-degrade surface (report the probability,
not a hard cut), at the cost of requiring a hazard prior and per-model conjugate bookkeeping.

## Key passages

- Abstract: "Here we examine the case where the model parameters before and after the changepoint
  are independent and we derive an online algorithm for exact inference of the most recent
  changepoint."
- Abstract: "We compute the probability distribution of the length of the current 'run,' or time
  since the last changepoint, using a simple message-passing algorithm."
- Abstract: "Our implementation is highly modular so that the algorithm may be applied to a
  variety of types of data."

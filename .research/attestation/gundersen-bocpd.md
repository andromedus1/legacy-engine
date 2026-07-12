---
source_handle: gundersen-bocpd
fetched: 2026-07-11
source_url: https://gregorygundersen.com/blog/2019/08/13/bocd/
provenance: source-direct
---

## Summary

Gregory Gundersen's 2019 tutorial "Bayesian Online Changepoint Detection" — a detailed,
equation-level walkthrough of Adams & MacKay's algorithm (the arXiv PDF body is not directly
quotable via the abstract page, so the mechanism-level statements are attested from this
reproduction). Verified passages cover the two mechanism details the brief leans on: (1) the
hazard function is the prior answer to "given no change point by run length τ, what is the
probability of one at τ" — the knob that encodes how often eras are expected to turn over; (2)
for exponential-family predictive models the algorithm reduces to keeping running conjugate
hyperparameters per run-length hypothesis — no integration is performed at run time, which is why
a Poisson–Gamma or Beta–Binomial BOCPD is a small amount of bookkeeping code rather than a
numerical-integration problem.

## Key passages

- Section "Changepoint prior": "The hazard function quantifies the answer to the question:
  'Provided a changepoint has not occurred by run length τ, what is the probability that it will
  occur at τ?'"
- Section "Posterior predictive for exponential family models": "Rather than computing the UPM
  predictive by computing the EF posterior and integrating out the parameters, we just need to
  keep track of the exponential family parameters by time t−1 to make a prediction at time t."
- Section "Recursive RL posterior estimation" (framing): "Ultimately, we want to infer both the
  run-length posterior distribution p(r_t|x_{1:t}) and the posterior predictive distribution
  p(x_{t+1}|x_{1:t}) so that we can predict the next data point given all the data we have seen so
  far."

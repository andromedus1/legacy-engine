---
source_handle: cvar-expected-shortfall
fetched: 2026-06-15
source_url: https://en.wikipedia.org/wiki/Expected_shortfall
provenance: source-direct
---

## Summary

The Expected Shortfall (ES) / Conditional Value-at-Risk (CVaR) Wikipedia article defines ES at the
q% level as the expected loss in the worst q% of cases — the conditional expectation of outcomes in
the tail beyond the Value-at-Risk threshold. Formally `ES_α(X) = (1/α) ∫₀^α VaR_γ(X) dγ`. ES is a
*coherent* risk measure (it satisfies subadditivity, so diversification never increases measured
risk), which Value-at-Risk is not; ES is more sensitive to the shape of the loss tail and is always
at least as large as VaR at the same level. For the sideboard hedge this is the candidate objective
for a worst-case/tail-aware hedge: instead of maximizing expected coverage over a field
distribution, maximize coverage in the worst tail of plausible fields (the metagame you fear most),
giving a tunable risk-appetite dial via α.

## Key passages

- "The 'expected shortfall at q% level' is the expected return on the portfolio in the worst q% of
  cases."
- Continuous form: "E[−X | X ≤ −VaR_α(X)]" — the conditional expectation of losses beyond the VaR
  threshold.
- "ES_α(X) = (1/α) ∫₀^α VaR_γ(X) dγ"
- "ES is a coherent ... measure of financial portfolio risk, while VaR is not."
- ES is "more sensitive to the shape of the tail of the loss distribution" and "always at least as
  big as VaR at the same level."

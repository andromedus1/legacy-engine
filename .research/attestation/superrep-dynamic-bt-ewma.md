---
source_handle: superrep-dynamic-bt-ewma
fetched: 2026-08-01
source_url: https://wrap.warwick.ac.uk/id/eprint/54660/1/WRAP_Firth_Dynamic_Bradley_j.1467-9876.2012.01046.x.pdf
provenance: source-direct
substrate_confidence: source-direct
---

# Dynamic Bradley–Terry modelling of sports tournaments

## Summary

Cattelan, Varin, and Firth model time-varying team abilities using exponentially weighted moving
averages of past results. The geometric weights form a causal decay process: the current ability
depends only on prior matches, with a smoothing parameter controlling memory. They evaluate
sequential forecasts by repeatedly fitting through one competition day and predicting the next.

On the NBA data, the compact EWMA model produced a mean predictive Brier score close to a much more
parameterized unstructured model and better than fixed empirical proportions. On the football data,
the EWMA and unstructured models had essentially equal mean predictive rank-probability scores.
These results support causal decay as a serious baseline, but they do not show a consistent advantage
over a flexible static comparator, and both examples concern scalar team ability rather than
matchup-specific non-transitivity.

## Key passages

> “abilities depend on past results through exponentially weighted moving average processes.” — Summary, PDF p. 2

> “geometrically decreasing to 0” — §3.1, decay-weight description, PDF p. 8

> “predict the results of the matches taking place in the following day” — §4.1, PDF p. 11

> “essentially equal: 0.450 and 0.451 respectively.” — §4.2, predictive RPS comparison, PDF p. 15

## Structural metadata

Primary peer-reviewed article in *Journal of the Royal Statistical Society: Series C* 62(1),
2013, pages 135–150. Published full text fetched from the Warwick repository.

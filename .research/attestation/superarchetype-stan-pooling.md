---
source_handle: superarchetype-stan-pooling
fetched: 2026-07-31
source_url: https://mc-stan.org/rstanarm/articles/pooling.html
provenance: source-direct
---

## Summary

The rstanarm vignette "Hierarchical Partial Pooling for Repeated Binary Trials" — the canonical
worked treatment of exactly our data shape: many units, each with a small number of binary trials
(the Efron & Morris 1975 baseball data, 18 players × 45 at-bats). It defines the three estimators
(complete pooling, no pooling, partial pooling) in one place, states the bias/variance mechanism of a
hierarchical model plainly, and — the load-bearing sentence for our design — states that the AMOUNT
of pooling is controlled by the estimated population variance: a more variable population means less
pooling. That is the mechanism by which a heterogeneity estimate (how much do cluster members
disagree?) can be turned directly into the strength of the prior a member cell shrinks toward,
instead of a hand-set constant.

## Key passages

- Complete pooling: "With _complete pooling_, each unit is assumed to have the same chance of
  success."
- No pooling: "With _no pooling_, each unit is assumed to have a completely unrelated chance of
  success."
- Partial pooling: "With _partial pooling_, each unit is assumed to have a different chance of
  success, but the data for all of the observed units informs the estimates for each unit."
- Bias/variance mechanism: "A hierarchical model introduces an estimation bias toward the population
  mean and the stronger the bias, the less variance there is in the estimates for the units."
- Group-level variance controls pooling: "The more variable the (estimate of the) population, the
  less pooling is applied."

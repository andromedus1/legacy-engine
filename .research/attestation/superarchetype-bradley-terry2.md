---
source_handle: superarchetype-bradley-terry2
fetched: 2026-07-31
source_url: https://cran.r-project.org/web/packages/BradleyTerry2/vignettes/BradleyTerry.html
provenance: source-direct
---

## Summary

The BradleyTerry2 package vignette (Turner & Firth; the package accompanying their JSS 48(9) paper) —
the reference implementation for paired-comparison models with structure above the individual
competitor. The standard "unstructured" model gives every player its own free ability parameter; the
structured variant replaces those free parameters with a linear predictor built from player-specific
explanatory variables, plus an optional player-level random effect. That random effect is exactly a
group/hierarchy term: it allows genuine variability between players that share the same covariate
values and induces correlation between all comparisons involving a common player. With the random
effect present the model is a GLMM, fitted by penalized quasi-likelihood. This is the paired-
comparison literature's own answer to "how do you put a group level above competitors in a matchup
model" — the parametric alternative to pooling raw counts.

## Key passages

- The base model (§1, Introduction): "The Bradley-Terry model assumes that in a 'contest' between any
  two 'players,' say player i and player j, the odds that i beats j are αᵢ/αⱼ, where αᵢ and αⱼ are
  positive-valued parameters which might be thought of as representing 'ability.'"
- Structured abilities (§3.1): "In some application contexts there may be 'player-specific'
  explanatory variables available, and it is then natural to consider model simplification".
- The random effect (§3.1): "The inclusion of the prediction error Uᵢ allows for variability between
  players with equal covariate values and induces correlation between comparisons with a common
  player."
- Fitting (§3.1): "The Bradley-Terry model is then a generalized linear mixed model, which the BTm
  function currently fits by using the penalized quasi-likelihood algorithm of Breslow and Clayton."

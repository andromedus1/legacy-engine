---
source_handle: superrep-validation-decision-regret
fetched: 2026-08-01
source_url: https://proceedings.mlr.press/v162/mandi22a.html
provenance: source-direct
substrate_confidence: source-direct
---

# Decision-Focused Learning: Through the Lens of Learning to Rank

## Summary

Mandi and colleagues study predict-then-optimize systems in which predictive outputs become inputs
to a downstream decision. They frame decision-focused learning as learning to rank feasible
solutions and evaluate the resulting decisions with regret. Their experiments explicitly show that
prediction error and decision regret can move differently: low mean-squared prediction error need
not imply low regret, and changing the training objective can trade prediction error against regret.

## Key passages

1. In predict-and-optimize settings, model predictions are used as coefficients in a downstream
   optimization problem (official abstract).
2. The authors frame the decision task as correctly ranking feasible solutions (official abstract).
3. Their MSE-versus-regret experiment reports cases in which low pointwise prediction error
   accompanies worse decision regret (PDF p. 7, Figure 2 discussion).

## Structural metadata

Peer-reviewed ICML 2022 paper in *Proceedings of Machine Learning Research*, volume 162, pages
14935--14947. Official article page and thirteen-page PDF fetched.

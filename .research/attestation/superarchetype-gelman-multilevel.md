---
source_handle: superarchetype-gelman-multilevel
fetched: 2026-07-31
source_url: https://people.eecs.berkeley.edu/~russell/classes/cs294/f05/papers/gelman-2005.pdf
provenance: source-direct
---

## Summary

Gelman's "Multilevel (hierarchical) modeling: what it can and can't do" (June 2005), worked through
the Minnesota home-radon example: houses nested within 85 counties, with a county-level predictor
(soil uranium). The paper contrasts three estimators of a group mean — complete pooling (one common
line for all counties), no pooling (a separate least-squares line per county), and the multilevel
partial-pooling estimate that shrinks each county toward the complete-pooling line in proportion to
how little data that county has. Its load-bearing content for a sparse grouped-estimation problem is
threefold. (1) The failure modes of the two extremes are named concretely: complete pooling gives
identical estimates for every group, which defeats the purpose of the analysis; no pooling overfits,
producing an implausible estimate for a county with only two observations. (2) The comparison is
settled empirically by cross-validation rather than argued: leave-one-point-out RMSE is 0.84 / 0.86 /
0.79 for complete pooling / no pooling / multilevel, and leave-one-GROUP-out RMSE at the group level
is 0.50 for complete pooling vs 0.40 for multilevel. (3) The no-pooling estimator cannot be
cross-validated at the group level at all, because it structurally cannot borrow information across
groups — the exact structural limitation that motivates adding a group level above a sparse
per-entity estimate.

## Key passages

- Overall verdict: "Compared to classical regression, multilevel modeling is almost always an
  improvement, but to different degrees: for prediction, multilevel modeling can be essential, for
  data reduction it can be useful, and for causal inference it can be helpful."
- Both extremes fail (§2.1, Data reduction): "Compared to the two classical estimates (no pooling and
  complete pooling), the inferences from the multilevel models are more reasonable. At one extreme,
  the complete-pooling method gives identical estimates for all counties, which is particularly
  inappropriate for this application, whose goal is to identify the locations in which residents are
  at high risk of radon. At the other extreme, the no-pooling model overfits the data, for example
  giving an implausibly high estimate of the average radon levels in Lac Qui Parle County, in which
  only two observations were available."
- Shrinkage target (§2.1): "whether they take into account the estimation uncertainty of the
  [group parameters], as is done in Figure 1 by shrinking toward the complete-pooling estimate."
- Cross-validated benefit (§2.1, Prediction): "When removing individual data points and re-fitting
  each model, the root-mean-squared cross-validation prediction errors are 0.84, 0.86, and 0.79 for
  complete pooling, no pooling, and multilevel modeling."
- Group-level prediction (§2.1, Prediction): "The root-mean-squared predictive errors at the county
  level are 0.50 and 0.40 for complete pooling and multilevel modeling, respectively."
- Structural limit of no-pooling (§2.1, Prediction): "Cross-validation cannot be performed at the
  county level for the no-pooling model since it is does not allow a county's radon level to be
  estimated using data from other counties."
- Overall claim (§2.1, Prediction): "The multilevel model gives more accurate predictions than the
  no-pooling and complete-pooling regressions, especially when predicting group averages."

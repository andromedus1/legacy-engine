---
source_handle: superrep-validation-proper-scores
fetched: 2026-08-01
source_url: https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf
provenance: source-direct
substrate_confidence: source-direct
---

# Strictly Proper Scoring Rules, Prediction, and Estimation

## Summary

Gneiting and Raftery define proper and strictly proper scoring rules for probabilistic forecasts.
Truthful reporting of a forecast distribution maximizes expected score under a proper rule, uniquely
so under a strictly proper rule. The paper identifies logarithmic and quadratic/Brier scores as
examples for categorical outcomes, distinguishes calibration from sharpness, warns that scores from
different sets of forecast situations are not directly comparable, and gives a proper interval score
that jointly penalizes interval width and misses.

## Key passages

1. Proper scoring rules encourage honest probabilistic forecasts; strict propriety makes the truthful
   forecast uniquely optimal (p. 359, abstract; p. 360, Section 2.1).
2. Forecast quality is framed as maximizing sharpness subject to calibration (p. 359, introduction).
3. Competing forecast scores are directly comparable only on the same forecast situations; otherwise
   differences in intrinsic predictability can confound the comparison (p. 362, Section 2.3).
4. The logarithmic score is strictly proper, while the paper also treats the quadratic/Brier score as
   a proper categorical score (pp. 363, 365, Sections 3.1 and 3.3).
5. The interval score rewards narrow intervals but penalizes observations falling outside them, with
   the penalty scaled by the nominal error rate (p. 370, Section 6.2).

## Structural metadata

Peer-reviewed methods and review article in the *Journal of the American Statistical Association*,
2007, volume 102, issue 477, pages 359--378. Full twenty-page author-hosted PDF fetched.

---
source_handle: recur-certify-fda-equivalence
fetched: 2026-08-13
source_url: https://www.fda.gov/media/163638/download
provenance: source-direct
substrate_confidence: source-direct
---

## Summary

The U.S. Food and Drug Administration's May 2026 final guidance, *Statistical Approaches to
Establishing Bioequivalence*, describes equivalence as a positive inferential claim: two one-sided
tests must both reject, or an equal-tails confidence interval must fit completely inside a declared
equivalence interval. It also treats sample size as design-specific and power-based, requires
eligibility and adaptive modifications to be prespecified, and requires error-rate control when
adaptation adds observations. Its numerical bioequivalence margins and minimum subject counts are
application-specific regulatory judgments, not general-purpose statistical constants.

## Key passages

- Section II.C.1, page 15: one test asks whether the parameter exceeds the lower limit and a second
  asks whether it is below the upper limit; both must succeed before concluding the parameter is in
  the interval. The equivalent confidence-interval implementation requires the entire equal-tails
  interval to lie within the equivalence bounds.
- Section II.A.3, pages 10–11: analysis eligibility, cohort additions, and adaptive modifications
  should be prespecified; an adaptive addition after analysis needs statistical methods that keep
  Type I error under its nominal level.
- Section II.A.3, page 11: sample size should be calculated for the proposed design, simulations may
  be used when analytic calculations are unavailable, assumptions used in the calculation should be
  recorded, and sensitivity to deviations from those assumptions should be investigated.
- Section II.C.1, page 9: equivalence is supported when a 90 percent confidence interval is wholly
  inside the application-specific bioequivalence margin, and alternative model-based approaches
  should reliably control the error of declaring equivalence for nonequivalent products.

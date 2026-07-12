---
source_handle: nist-count-charts
fetched: 2026-07-11
source_url: https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc331.htm
provenance: source-direct
---

## Summary

NIST/SEMATECH e-Handbook §6.3.3.1, "Counts Control Charts" (c-chart) — the standard control chart
for Poisson-distributed event counts, with k-sigma limits UCL/LCL = c ± k√c. The load-bearing
content for legacy-engine is the small-count caveat: the normal approximation behind those
symmetric ±k√c limits is only adequate when the Poisson mean is at least 5, and below a mean of ~9
there is no usable lower control limit at all. Legacy-engine's weekly deck counts sit at median
2–8.5 for mid-tier archetypes and 2–12 for camps — squarely in the regime where
normal-approximation count monitoring is unreliable, which is why the brief routes count-rate
change detection through exact-likelihood methods (Poisson/binomial models, BOCPD) or
share-of-field proportions rather than raw-count z-scores.

## Key passages

- §6.3.3.1: "defects occur in a given inspection unit according to the Poisson distribution, with
  parameter c".
- Control limits: "UCL = c + k√c, Center Line = c, LCL = c − k√c".
- Small-count caveat: "the normal approximation to the Poisson is adequate when the mean of the
  Poisson is at least 5."
- Low-mean limitation: "When applied to the c chart this implies that the mean of the defects
  should be at least 5" and when the mean is smaller than ~9 "there will be no lower control
  limit".

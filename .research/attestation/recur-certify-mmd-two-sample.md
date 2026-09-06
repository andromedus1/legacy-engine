---
source_handle: recur-certify-mmd-two-sample
fetched: 2026-08-13
source_url: https://www.jmlr.org/papers/volume13/gretton12a/gretton12a.pdf
provenance: source-direct
substrate_confidence: source-direct
---

## Summary

Gretton and coauthors' 2012 JMLR paper, *A Kernel Two-Sample Test*, develops maximum mean
discrepancy (MMD) tests of the point null that two samples come from equal distributions. The tests
can compare multivariate distributions without reducing the comparison to means. Their experiments
show that Type II error depends materially on sample size, test construction, computation, and the
data-generating problem. This is a difference detector, not an equivalence certificate: nonrejection
of its equality null does not reverse the inferential burden.

## Key passages

- Section 1, page 1: the paper tests the null that two distributions are equal against the
  alternative that they differ, with pooling across samples offered as a motivating use.
- Abstract and Section 2: MMD is the largest expectation difference over the unit ball of an RKHS;
  the paper gives distribution-free and asymptotic tests and quadratic- and linear-time estimators.
- Section 8.3, pages 28–30: Type II error changes with sample size and method; a linear-time variant
  needs more observations for a given error level, and one examined dataset does not reach zero
  Type II error even at its largest sample size.
- Section 8.3, page 28: a t-test can miss differences beyond the mean and fails on one multivariate
  dataset, while nonparametric MMD is sensitive to broader distributional change.
- Section 8.4, page 28: the authors caution that matching distributions alone need not establish
  real-world semantic correspondence.

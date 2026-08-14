---
source_handle: recur-certify-kernel-equivalence
fetched: 2026-08-13
source_url: https://arxiv.org/abs/2603.10886
provenance: source-direct
substrate_confidence: source-direct
---

## Summary

Liu and Gandy's 2026 preprint, *Kernel Tests of Equivalence*, reverses the usual goodness-of-fit
null: the null says two distributions differ by at least a prespecified discrepancy margin, while
the alternative says their discrepancy is within that margin. It proposes one- and two-sample
kernel equivalence tests, including an MMD-based two-sample test. The paper reports that its normal
approximation can inflate Type I error when the margin is small or the data are high-dimensional;
its bootstrap construction is more conservative and has better finite-sample Type I control in the
reported experiments. The work is recent and presented as an arXiv preprint, so project-specific
simulation and forward validation remain necessary.

## Key passages

- Abstract and Section 1, lines 3–5 and 20–28: failure to reject equality-vs-difference can be a
  Type II error; equivalence instead tests whether discrepancy is at least a predeclared margin and
  controls erroneous declarations of similarity.
- Section 2.1, lines 23–28 and 59–61: the equivalence null is the complement of a discrepancy ball
  of radius theta; rejecting it supplies evidence of practical similarity under controlled error.
- Section 2.2.2, lines 106–121: MMD is the maximum difference in expected RKHS functions and can be
  estimated as a two-sample V-statistic, making it a distribution-level rather than mean-only
  discrepancy.
- Sections 3.1–3.2, lines 207–220: small nonzero margins can degrade the normal approximation and
  inflate Type I error; the bootstrap alternative is designed to improve error control but is more
  conservative.
- Experiments and conclusion, lines 424–431: the high-dimensional MNIST example shows poor Type I
  control for the normal MMD equivalence test and better calibration for the bootstrap test; the
  authors describe margin selection by a prespecified power target.

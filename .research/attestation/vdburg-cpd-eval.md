---
source_handle: vdburg-cpd-eval
fetched: 2026-07-11
source_url: https://arxiv.org/abs/2003.06222
provenance: source-direct
---

## Summary

van den Burg & Williams, "An Evaluation of Change Point Detection Algorithms" (arXiv:2003.06222;
the Turing Institute TCPDBench benchmark — 14 algorithms over human-annotated real-world series;
verified against the ar5iv render). The benchmark's central sobering findings: CPD methods are
usually validated on simulation or a handful of series with unreliable ground truth; on real data
with DEFAULT parameters, the trivial "zero" detector (predict no change points at all) outperforms
many published methods, and plain binary segmentation is the best average performer among real
detectors. The gap between default-parameter and oracle-tuned performance is large. Consequences
the brief encodes: (a) never trust a CPD method's defaults — calibrate the penalty/threshold on
the project's own labeled disturbances (the ban/release ledger provides those labels); (b) a
conservative bias (fewer detected eras) is empirically respectable — a spurious change point costs
real data, silently.

## Key passages

- Abstract: "Algorithms are typically evaluated on simulated data and a small number of
  commonly-used series with unreliable ground truth."
- Abstract: "we consider it vastly more important to properly evaluate existing algorithms on
  real-world data".
- §5.2: "the binseg method of Scott and Knott (1974) achieves the highest average performance on
  the univariate time series".
- §5.2: "We note that the zero method outperforms many of the other methods, especially in the
  Default experiment."
- §6: "future work could focus on incorporating automated hyperparameter tuning methods to bridge
  the gap between the Default and Oracle performance".

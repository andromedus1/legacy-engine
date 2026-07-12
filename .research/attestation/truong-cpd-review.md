---
source_handle: truong-cpd-review
fetched: 2026-07-11
source_url: https://arxiv.org/abs/1801.00718
provenance: source-direct
---

## Summary

The standard survey of offline change-point detection (Truong, Oudre & Vayatis, published Signal
Processing 167, 2020; verified against the ar5iv HTML render of arXiv:1801.00718). It organizes
every offline CPD method as a combination of three interchangeable elements — a cost function
(what kind of change is measurable), a search method (how segmentations are explored: optimal
dynamic programming vs approximate binary segmentation / window / bottom-up), and a constraint on
the number of changes (known K vs a penalty). This taxonomy is the frame the brief uses to compose
a detector for legacy-engine's mixed signals. The review is also the source for the load-bearing
claim that kernel-based cost functions extend CPD beyond R^d-valued signals — the property that
lets one detector run on composition vectors. The authors' companion Python package is ruptures,
which implements the reviewed algorithms.

## Key passages

- Abstract: "This article presents a selective survey of algorithms for the offline detection of
  multiple change points in multivariate time series." and "detection algorithms considered in
  this review are characterized by three elements: a cost function, a search method and a
  constraint on the number of changes."
- Abstract: "Implementations of the main algorithms described in this article are provided within
  a Python package called ruptures."
- §2.3 (Selection criteria for the review): "detection methods are expressed as the combination of
  the following three elements" — cost function, search method, constraint on the number of
  change points.
- §4.2.3 (Kernel-based detection): "The cost function c_kernel can be combined with any kernel to
  accommodate various types of data (not just R^d-valued signals)."

---
source_handle: crops-penalty
fetched: 2026-07-11
source_url: https://arxiv.org/abs/1412.3617
provenance: source-direct
---

## Summary

Haynes, Eckley & Fearnhead, "Computationally efficient changepoint detection for a range of
penalties" (CROPS; J. Computational and Graphical Statistics 2017; verified against the ar5iv
render of arXiv:1412.3617). Two load-bearing points. (1) Penalized CPD overfits by construction —
"adding a changepoint always reduces the overall cost" — so the penalty is the only thing standing
between the detector and spurious change points; the standard choices are AIC β=2p, SIC/BIC
β=p·log n, Hannan–Quinn β=2p·log log n. (2) Those textbook penalties are calibrated to a correctly
specified within-segment model; under model mis-specification they lack robustness and can produce
poor segmentations with many false positives — which is exactly legacy-engine's situation (weekly
deck counts are not i.i.d. Gaussian). CROPS itself computes the optimal segmentation for EVERY
penalty value in a continuous range at small cost — the diagnostic sweep that makes penalty choice
an inspectable decision instead of a magic constant.

## Key passages

- Abstract: "in many applications the model assumed for the data is not correct and these penalty
  choices are not always appropriate" and the paper presents "a method to obtain optimal
  changepoint segmentations of data sequences for all penalty values across a continuous range".
- §1: "popular examples used frequently in the literature include β=2p (Akaike's Information
  Criterion); β=p log n (Schwarz's Information Criterion); and β=2p log log n (Hannan and Quinn)".
- §1: "for many cost functions, this results in overfitting since adding a changepoint always
  reduces the overall cost".
- §6 (Discussion): "default choices can work well if we have an accurate model for the data within
  each segment, we have shown that they lack robustness, and can produce poor segmentations, in
  the presence of model mis-specification."

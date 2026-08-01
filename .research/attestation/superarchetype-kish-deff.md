---
source_handle: superarchetype-kish-deff
fetched: 2026-07-31
source_url: https://cran.r-project.org/web/packages/PracTools/vignettes/Design-effects.html
provenance: source-direct
---

## Summary

The PracTools vignette on design effects and effective sample size — survey sampling's formalization
of "unequal contributions cost you precision". Kish's design effect is one plus the relative variance
(squared coefficient of variation) of the weights, and the effective sample size is the nominal size
divided by that design effect. Applied to a pooled cluster cell whose "weights" are the per-member
match counts, this is algebraically the same object as 1/HHI: the more lopsided the member
contributions, the smaller the effective count. The vignette also states the limitation that keeps
the gate honest — Kish's formula is derived under restrictive assumptions (a stratified simple random
sample) and is not always the relevant measure when subgroups are deliberately sampled at different
rates, so it should be used as an interpretable concentration diagnostic rather than as a literal
variance correction.

## Key passages

- Kish's design effect: "deff_K = 1 + relvar(w) = 1+ CV^2(w) = 1 + (1/n) Σ(w_i - w̄)^2 / w̄^2".
- Effective sample size: "n_eff = n/deff(θ̂)".
- Restrictive assumptions: the formula "is derived under some extremely restrictive assumptions. It
  applies to a stratified, simple random sample (STSRS)."
- Where it misleads: "deff_K is not always relevant in surveys where variances differ across strata,
  where subgroups are intentionally sampled at different rates, and/or where different subgroups have
  substantially different response rates."

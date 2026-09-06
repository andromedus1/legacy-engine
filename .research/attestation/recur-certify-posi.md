---
source_handle: recur-certify-posi
fetched: 2026-08-13
source_url: https://arxiv.org/abs/1306.1059
provenance: source-direct
substrate_confidence: source-direct
---

## Summary

Berk, Brown, Buja, Zhang, and Zhao's 2013 *Valid Post-Selection Inference* paper shows why ordinary
tests and confidence intervals lose their classical guarantees after response-driven model
selection. Their PoSI construction restores coverage by simultaneous inference over the model
universe, at a conservatism cost. In their fixed-design regression setting, prescreening that does
not use the response does not invalidate later response inference. The precise theorem is specific
to their regression assumptions, but the distinction between response-free nomination and
response-driven selection is directly informative for experimental design.

## Key passages

- Abstract and Section 1, lines 3–5 and 28–38: model selection driven by stochastic response data
  invalidates ordinary inferential guarantees; simultaneous inference can provide universal
  post-selection protection, though conservatively.
- Section 4.4, lines 247–258: PoSI provides coverage for any selection procedure and explicitly
  protects against informal experimentation and significance hunting.
- Section 4.5, lines 260–278: restricting the searched model universe in advance reduces the
  problem; in fixed-design regression, screening adjusted predictors without the response does not
  invalidate inference.
- Section 4.6, lines 279–313: simultaneous coverage across all candidate submodels yields strong
  family-wise error control after selection.
- Section 6, line 546: some designs require correction constants much larger than ordinary
  single-model critical values.

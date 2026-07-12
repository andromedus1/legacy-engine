---
source_handle: wikipedia-fdr
fetched: 2026-07-11
source_url: https://en.wikipedia.org/wiki/False_discovery_rate
provenance: source-direct
---

## Summary

Wikipedia's "False discovery rate" article, used for the standard definitions (the primary
Benjamini & Hochberg 1995 JRSS-B paper is paywalled; the procedure statement here is the standard
one). FDR conceptualizes the type-I error rate under multiple comparisons as the expected
proportion of rejected hypotheses that are false rejections. The Benjamini–Hochberg step-up
procedure: sort the m p-values, find the largest k with P(k) ≤ (k/m)·α, reject H(1)…H(k). FDR
control is deliberately less stringent than family-wise error control (Bonferroni) and buys more
power at the cost of some expected false discoveries. Relevance: legacy-engine screens ~50–150
entity series for change points every refresh; per-entity permutation p-values (e.g. E-Divisive's)
should be corrected fleet-wide with BH rather than Bonferroni, because a missed real era-break
(pooling across a disturbance) and a spurious break (silently truncated window) are both real but
asymmetric costs the α-level should be tuned against.

## Key passages

- Lead: "In statistics, the false discovery rate (FDR) is a method of conceptualizing the rate of
  type I errors in null hypothesis testing when conducting multiple comparisons."
- BH procedure: "For a given α, find the largest k for which P(k) ≤ (k/m)α. Reject the null
  hypothesis (i.e., declare discoveries) for all H(i) for i = 1, …, k."
- FDR vs FWER: "FDR-controlling procedures provide less stringent control of Type I errors
  compared to family-wise error rate (FWER) controlling procedures (such as the Bonferroni
  correction), which control the probability of at least one Type I error. Thus, FDR-controlling
  procedures have greater power, at the cost of increased numbers of Type I errors."

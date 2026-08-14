---
source_handle: recur-certify-bh-fdr
fetched: 2026-08-13
source_url: https://www.dcscience.net/Benjamini-Hochberg-1995-FDR.pdf
provenance: source-direct
substrate_confidence: source-direct
---

## Summary

Benjamini and Hochberg's 1995 paper defines false discovery rate (FDR) as the expected proportion
of false rejections among rejected hypotheses and introduces a sequential procedure that controls
FDR for independent test statistics. The paper contrasts FDR with family-wise error rate (FWER):
FDR can gain power because it tolerates some false discoveries, whereas FWER controls the chance of
any false rejection. The original theorem's independence conditions matter when candidate tests
share intervals or features.

## Key passages

- Abstract, page 0: FDR controls the expected proportion of falsely rejected hypotheses, is equal
  to FWER when every null is true, and can be less restrictive otherwise.
- Introduction, page 1: strong FWER procedures can have substantially lower power than
  per-comparison procedures, motivating a different error criterion.
- Theorem 1, page 4: the step-up rule controls FDR at the chosen level for independent test
  statistics and any configuration of false null hypotheses.
- Remark after Theorem 1, page 4: independence of statistics corresponding to false nulls is not
  needed for that proof, leaving the null-test dependence structure load-bearing.
- Section 3.1, page 5: the FDR procedure rejects at least as many hypotheses as the compared strong
  FWER procedure in the paper's setting, illustrating the power/error tradeoff.

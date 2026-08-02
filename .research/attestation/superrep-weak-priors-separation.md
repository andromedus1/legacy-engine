---
source_handle: superrep-weak-priors-separation
fetched: 2026-08-01
source_url: https://sites.stat.columbia.edu/gelman/research/unpublished/priors11.pdf
provenance: source-direct
substrate_confidence: source-direct
---

# A weakly informative default prior distribution for logistic and other regression models

## Summary

Gelman and colleagues propose scaled Student-t priors for logistic-regression coefficients. The
method returns finite regularized estimates under complete separation and shrinks higher-order
interactions. Its empirical comparison is against other default prior implementations on a corpus of
datasets. A finite posterior under separation is therefore a property of the prior-assisted model,
not evidence that a sparse cell supplied identifying information.

## Key passages

- Abstract, PDF p. 0: nonbinary inputs are scaled before independent Student-t priors are placed on
  coefficients.
- Abstract, PDF p. 0: the procedure gives an answer under complete separation, a problem that can
  occur even in otherwise modest logistic models.
- Abstract, PDF p. 0: higher-order interactions receive additional shrinkage.
- §4.1: the flat-prior fit fails in the separated example, while weakly informative priors regularize
  the estimate.

## Structural metadata

Primary Annals of Applied Statistics article manuscript (2008). The fetched PDF includes the full
paper and journal citation.

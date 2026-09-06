---
source_handle: recurrent-ecp-james-matteson
fetched: 2026-08-13
source_url: https://packages.oit.ncsu.edu/cran/web/packages/ecp/vignettes/ecp.pdf
provenance: source-direct
source_class: primary-paper
substrate_confidence: source-direct
---

# James and Matteson — nonparametric multiple change-point analysis

## Summary

James and Matteson describe the `ecp` package and its energy-statistic methods for retrospective
multiple change-point analysis of multivariate observations. E-Divisive recursively bisects a
sequence and uses permutation tests; E-Agglo starts from an initial segmentation and greedily merges
adjacent segments. The methods target changes in the joint distribution rather than only a mean or
variance, but their stated theory assumes independent observations and a finite absolute moment.

## Key details

1. The methods estimate both the number and locations of multiple change points and are intended to
   detect general changes in a multivariate distribution. The paper states the assumptions as
   independence over time and existence of a finite absolute alpha-th moment for alpha in `(0, 2]`.
   — pp. 1–3, introduction and package overview.
2. E-Divisive is hierarchical bisection: it selects the split maximizing an energy divergence and
   tests proposed splits by permutation. For independent observations, the paper reports a strong
   consistency result for the procedure. — pp. 4–5, hierarchical divisive estimation.
3. E-Agglo requires an initial segmentation and merges neighboring segments according to an
   energy-statistic goodness-of-fit objective; its greedy search avoids the cost of exhaustive
   optimization. — pp. 5–6, hierarchical agglomerative estimation.
4. The package contrasts its joint-distribution method with mean/variance-specific alternatives and
   notes that some faster nonparametric methods lack the same consistency guarantee. — pp. 2 and 5.

## Structural metadata

Nicholas A. James and David S. Matteson, “ecp: An R Package for Nonparametric Multiple Change
Point Analysis of Multivariate Data,” *Journal of Statistical Software* 62(7), 2014, pp. 1–25.
DOI 10.18637/jss.v062.i07. The fetched file is the paper vignette distributed with the package.

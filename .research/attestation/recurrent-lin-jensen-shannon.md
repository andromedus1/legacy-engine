---
source_handle: recurrent-lin-jensen-shannon
fetched: 2026-08-13
source_url: https://www.cise.ufl.edu/~anand/sp06/jensen-shannon.pdf
provenance: source-direct
source_class: primary-paper
substrate_confidence: source-direct
---

# Lin — divergence measures based on Shannon entropy

## Summary

Lin derives the Jensen–Shannon divergence for comparing probability distributions. Unlike the
directed Kullback divergence discussed in the paper, the construction does not require mutual
absolute continuity, is nonnegative, permits weights on the compared distributions, and extends to
more than two distributions.

## Key details

1. The paper identifies absolute-continuity failures as a limitation of the directed and symmetric
   Kullback divergences: a directed divergence is undefined when the reference distribution assigns
   zero probability where the other assigns positive probability. — p. 145, Section II.
2. The Jensen–Shannon construction is based on Shannon entropy and Jensen's inequality; for two
   distributions it is nonnegative and equals zero when the distributions are equal. It permits a
   separate weight for each distribution. — p. 147, Section IV.
3. The construction generalizes to any finite number of distributions as the entropy of the weighted
   mixture minus the weighted component entropies. — pp. 148–149, Section V.
4. Equation (4.1) defines the two-distribution Jensen–Shannon divergence from a weighted mixture and
   weighted component entropies. With equal weights, exchanging the two distributions leaves that
   expression unchanged. — p. 147, Section IV, equation (4.1).

## Structural metadata

Jianhua Lin, “Divergence Measures Based on the Shannon Entropy,” *IEEE Transactions on
Information Theory* 37(1), January 1991, pp. 145–151. Manuscript received October 24, 1989 and
revised April 20, 1990, as printed on the fetched paper.

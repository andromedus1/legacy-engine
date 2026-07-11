---
source_handle: sklearn-decomposition
fetched: 2026-07-11
source_url: https://scikit-learn.org/stable/modules/decomposition.html
provenance: source-direct
---

## Summary

scikit-learn TruncatedSVD / LSA reference. TruncatedSVD computes only the k largest singular values.
Applied to a term-document matrix (here: a deck-card matrix) the transform is latent semantic
analysis, mapping to a low-dimensional "semantic" space. LSA is known to combat synonymy/polysemy,
which otherwise make term-document matrices overly sparse and give poor cosine similarity — the
load-bearing justification for reducing the sparse deck-card matrix before distance-based clustering.

## Key passages

- Truncation: "TruncatedSVD implements a variant of singular value decomposition (SVD) that only
  computes the k largest singular values, where k is a user-specified parameter."
- LSA: "When truncated SVD is applied to term-document matrices (as returned by CountVectorizer or
  TfidfVectorizer), this transformation is known as latent semantic analysis (LSA), because it
  transforms such matrices to a \"semantic\" space of low dimensionality."
- Combats sparsity: "In particular, LSA is known to combat the effects of synonymy and polysemy
  (both of which roughly mean there are multiple meanings per word), which cause term-document
  matrices to be overly sparse and exhibit poor similarity under measures such as cosine similarity."

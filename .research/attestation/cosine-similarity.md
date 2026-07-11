---
source_handle: cosine-similarity
fetched: 2026-07-11
source_url: https://en.wikipedia.org/wiki/Cosine_similarity
provenance: source-direct
---

## Summary

Cosine-similarity reference. cos(θ) = A·B / (||A|| ||B||). Its load-bearing advantage for the deck
setting: low complexity on sparse vectors because only non-zero coordinates matter — so it is cheap
on a ~40k-card vocabulary where each deck touches ~75 entries. The document-vector framing (each
word a coordinate, a document a vector of occurrence counts) maps directly onto deck-as-card-count
vectors.

## Key passages

- Definition: "cosine similarity = S_C(A,B) := cos(θ) = A·B / ||A|| ||B||".
- Sparse advantage: "One advantage of cosine similarity is its low complexity, especially for sparse
  vectors: only the non-zero coordinates need to be considered."
- Document framing: "each word is assigned a different coordinate and a document is represented by
  the vector of the numbers of occurrences of each word in the document."

---
source_handle: kritschgau-hypergraph
fetched: 2026-07-11
source_url: https://pmc.ncbi.nlm.nih.gov/articles/PMC10960844/
provenance: source-direct
---

## Summary

Kritschgau et al. (2024), hypergraph community detection applied to 17Lands MTG draft data. Two
load-bearing cautions for validation design. (1) An information criterion (minimum description
length) picked 3 clusters as optimal while 5 was "in some sense the obvious number" — i.e. a
statistical index can disagree with the human-intuitive archetype count (and tends to converge on
color identity rather than strategy). (2) Their own conclusion that certifying a cluster as a real,
named archetype "requires some domain knowledge, and is therefore, hard to verify independently" —
the published state of the art still needs a human to name the camp.

## Key passages

- Hyperedge representation: "a hyperedge is a player's card pool (without multiplicity) after a
  draft."
- MDL vs obvious count: "the 3 clusters provide the shortest description length. This is seen in
  Table 1 where the suggested number of clusters is 3 on the basis of minimal description length,
  however, 5 is in some sense the 'obvious' number of clusters."
- Domain-knowledge caveat: "Recognizing these archetypes as the 'themes' of the clusters requires
  some domain knowledge, and is therefore, hard to verify independently."

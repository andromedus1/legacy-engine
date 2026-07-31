---
id: feature-multi-split-matrix-core-tally
kind: story
stage: implementing
tags: [advisory]
parent: feature-multi-split-matrix
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Multi-split core: maximal tally + pooling + uniform builder

## Brief

The multi-split kernel: `compute_match_results` gains an additive `split_variants` param (all
staged parents camp-labeled on both sides in ONE scan) + a `camp_parent` provenance map, and
`matchup.py` gains the pooling/hierarchy kernel (`_pool_opponent_tallies`,
`_multi_hierarchy_inputs` feeding the UNCHANGED `_cell_prior`) plus the `MultiSplitMatrix`
dataclass with `ranking_view()` and the uniform/full-window `build_multi_split_matrix`. Ships
with the uniform half of the parity test: camp rows field-for-field equal to
`build_matrix(split_variant=P)` per parent; unsplit rows equal to the plain matrix; default
(`split_variants=None`) byte-identical with the existing suite untouched.

## Implementation

Parent feature `feature-multi-split-matrix` — Units 1 and 2 of `## Implementation Units`
(exact signatures, notes, and acceptance criteria there). Tests:
`tests/test_match_results_multi_split.py` + the uniform-parity and pure-kernel parts of
`tests/test_matchup_multi_split.py`. Hermetic DBs only — never the default DB.

---
id: epic-card-semantics-ir-fix-ld-mislabel
kind: story
stage: implementing
tags: [advisory, bug]
parent: epic-card-semantics-ir
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-31
---

# Fix _derive_attacks_for_promoted land-destruction mislabel (Wasteland/Ghost Quarter)


`_derive_attacks_for_promoted` (src/legacy_engine/advisory/sideboard.py) mislabels
land-destruction spells as `creature-based`.

Found while implementing `feature-sb-maindeck-aware-coverage-discount`: verified against the
real card corpus (`legacy.duckdb`) that Wasteland's and Ghost Quarter's oracle text is literally
"{T}, Sacrifice ...: Destroy target [nonbasic] land." The removal rule in
`_derive_attacks_for_promoted` checks the bare substring `"destroy target"` and tags
`creature-based` before any land-specific check runs, so any promoted (non-catalog)
land-destruction hoser gets mislabeled as `creature-based` instead of `greedy-manabase`/`ramp`.

This doesn't affect Wasteland today because it's a curated `HOSER_CATALOG` entry
(`attacks=["greedy-manabase"]`) that bypasses the derivation entirely, but any land-destruction
card promoted from the empirical sideboard pool WITHOUT a curated catalog entry (e.g. Ghost
Quarter, which is not in `HOSER_CATALOG`) would be silently mis-tagged.

Suggested fix: add a land-destruction detection rule (oracle_text contains `"destroy target"`
AND target phrasing indicates a land, e.g. `"target land"` / `"target nonbasic land"`) ahead of
the generic creature-removal rule in `_derive_attacks_for_promoted`, mapping it to
`greedy-manabase` (and/or `ramp`) instead of `creature-based`.

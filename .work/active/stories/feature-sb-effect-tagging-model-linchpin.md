---
id: feature-sb-effect-tagging-model-linchpin
kind: story
stage: implementing
tags: [advisory]
parent: feature-sb-effect-tagging-model
depends_on: [feature-sb-effect-tagging-model-vocab-catalog]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Linchpin hybrid model (derive + curated overrides)

## Brief

Build the archetype linchpin model — the `centrality` input Feature B's impact score consumes.
Hybrid: auto-derive candidate linchpins from composition (near-mandatory inclusion × engine/combo
role) and merge curated overrides on top (curated centrality wins). New module + curated JSON SSOT +
config path, following the `curated-json-resource-loader` pattern. Depends on the vocab-catalog story
because `neutralized_by` references the effect-tag vocabulary it defines.

## Implementation

Covers parent feature unit **4** — see `feature-sb-effect-tagging-model` § Implementation Units
(Unit 4) for the `Linchpin` dataclass, `load_linchpin_overrides` / `derive_linchpins` /
`linchpins_for_archetype` signatures, the curated JSON schema, and acceptance criteria. New files:
`advisory/linchpins.py`, `data/linchpins/legacy.json`, `config.py` additions; tests in
`tests/test_linchpins.py`.

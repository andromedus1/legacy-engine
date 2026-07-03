---
id: feature-sb-field-weighted-scorer-impact
kind: story
stage: implementing
tags: [advisory]
parent: feature-sb-field-weighted-scorer
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Impact factors + hoser→linchpin capability bridge

## Brief

New `src/legacy_engine/advisory/impact.py`: the four decomposed impact factors (centrality,
symmetry, castability, draw-probability) combined multiplicatively with hard gates, plus the
`hoser_capabilities()` bridge (deferred from Feature A) mapping a hoser to the linchpin
`neutralized_by` capability vocabulary. Pure / DB-free (objective-search-split) — takes resolved
inputs (opp linchpins, my vulnerability tags, my colors, copies), returns an `ImpactBreakdown`.

## Implementation

Covers parent feature **Units B1 + B2** — see `feature-sb-field-weighted-scorer` § Implementation
Units for exact signatures, constants (`_CENTRALITY_BASELINE`, `_SYMMETRY_FLOOR`), and the locked
Design decisions (multiplicative hard gates). Consumes `advisory/linchpins.py` + the `HoserCard`
`symmetry`/`cast_requires`/`functional_group` fields + the `plays-<color>`/`graveyard-*` vocab from
Feature A. Tests: new `tests/test_impact.py`.

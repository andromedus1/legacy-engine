---
id: feature-sb-maindeck-aware-coverage-discount
kind: story
stage: implementing
tags: [advisory]
parent: feature-sb-maindeck-aware-coverage
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Maindeck-coverage discount on SB element weights

## Brief

Detect which vulnerability tags the maindeck already answers and discount the SB coverage-model
element weights for those tags, so the recommender stops padding cards redundant with the maindeck
(the "SB'd Ghost Quarter while running 4 Wasteland" bug). Gated-additive: no maindeck answers ⇒
byte-identical.

## Implementation

Covers parent feature **Units C1 + C2** — see `feature-sb-maindeck-aware-coverage` § Implementation
Units for the `_maindeck_answer_coverage` helper, the `_MAINDECK_DISCOUNT`/`_MAINDECK_SATURATION`
constants, the `_build_coverage_model` discount + `recommend_sideboard` wiring, and acceptance
criteria. File: `src/legacy_engine/advisory/sideboard.py`; tests in `tests/test_sideboard.py`.

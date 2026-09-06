---
id: feature-ranking-credible-window-utility-transition-field
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: feature-ranking-credible-window-utility
depends_on: [feature-ranking-credible-window-utility-horizon-clamp]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Cold-start transition field

## Brief

Implement Unit 2 of the parent feature: construct the exact observed post-ban field plus a bounded,
decaying, affectedness-filtered preceding-regime prior with fully reconciled provenance.

## Implementation notes

- Added typed `FieldSlice`/`TransitionField` models and `build_transition_field` to the advisory
  field boundary. Current counts remain untouched; prior pseudo-decks are capped by the 500-deck
  floor, exclude every affected label supplied by the affectedness map, and allocate with stable
  largest-remainder rounding.
- The refresh generator now derives affectedness once, uses the transition projection for ranking
  shares and Dirichlet counts, and serializes observed/effective sizes, prior strength, evidence
  kind, and reason. Matchup matrices still use their independent per-entity pair horizons.
- Added evidence payload fields and transition-prior support while retaining the production Agency
  ordering unchanged.

## Verification

- `PYTHONPATH=. uv run --no-sync python -m pytest -q tests/test_field_model.py tests/analytics/eras/test_consume.py` (103 passed)
- `PYTHONPATH=. uv run --no-sync python -m pytest -q tests/test_refresh_best_call_ranking.py` (44 passed)

## Deviations / adjacent issues

- Existing camp parity tests intentionally treat camp row fields as an additive payload allow-list;
  transition provenance is serialized on archetype rows/meta while camp row shape remains parity-
  identical. Camp fractions continue to use observed current-regime presence, as required by the
  design, until a separate camp prior projection is justified.

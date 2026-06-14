---
id: feature-empirical-sideboard-swings
kind: feature
stage: done
tags: [advisory]
parent: epic-bigmana-coverage-sideboard-fidelity
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Empirical sideboard swing magnitudes where data supports

## Brief
The recommender's per-tag swing magnitudes (`_SWING_DEDICATED=0.20`, `_SWING_SOFT=0.10`) are curated
heuristic constants, not derived from before/after-sideboard win-rate data — they drive solver ordering.
Where the data supports it (sufficient n on the relevant matchup/tag), derive empirical swings from
actual sideboarded-game win-rate deltas; keep the curated constant + its honest caveat where the data is
thin. Must stay honest (confidence-tier the empirical swings; never present a thin-data swing as
established). Gated-additive: thin tags keep the curated constant + caveat.

## Design

### What is and is not measurable from this corpus

**NOT measurable: before/after-board win-rate swing.**
The `rounds` table stores only match-level aggregate scores (`"2-1"`, `"2-0"`, etc.).
Individual game-within-match outcomes are not recorded — game 1 (pre-board) cannot be
separated from games 2–3 (post-board). A true before/after-board swing cannot be derived
from this data. Fabricating one would be dishonest.

**IS available: presence-correlational per-card×matchup lift (already used elsewhere).**
`card_value_matchup` from `analytics.card_value` provides a per-card×matchup `lift`
estimate: how much better decks that registered card X in the sideboard (`board="side"`)
won vs archetype Y, relative to the card's overall corpus average. This is a
**presence-correlational** signal — confounded by deck-quality and player-selection
effects. It is not a causal win-rate delta. It is already used in the maindeck-aware
OUT/IN planner; extending it to sideboard catalog cards is the honest available signal.

### Approach: `empirical_swing_proxy` + `card_swing_overrides`

Where the presence-correlational signal for a catalog sideboard card vs a matchup clears
the `≥evolving` tier (n ≥ 30 decisive matches) AND has a positive lift above the noise
floor (`_EMPIRICAL_SWING_MIN_LIFT = 0.02`), the `empirical_swing_proxy()` function converts
that lift to a bounded swing value (capped at `_EMPIRICAL_SWING_CAP = 0.35`).

These per-card proxies are passed into `_build_coverage_model` via the new
`card_swing_overrides: dict[str, float] | None` parameter. The override replaces a card's
catalog swing in the `best_swing_for_tag` max computation. The call-site applies
`max(proxy, catalog_swing)` so the catalog floor is always preserved — data can raise
but not lower the effective swing for a tag.

### Honesty properties enforced

- Only **positive lifts** produce a proxy. Negative lift (card present in losing decks)
  keeps the curated constant — we do not penalize catalog cards on selection effects.
- Lifts below `_EMPIRICAL_SWING_MIN_LIFT` are treated as noise → None → curated constant.
- Proxy is capped at `_EMPIRICAL_SWING_CAP = 0.35` to prevent selection-effect outliers.
- Speculative tier (n < 30) always returns None → curated constant.
- `card_swing_overrides=None` → `_build_coverage_model` is byte-identical to pre-feature.
- `heuristic_note` on `SideboardPackage` switches to `_DATA_INFORMED_NOTE` when any
  swings were data-informed, labeling them presence-correlational (not causal).
- `SideboardPackage.swing_data_informed` and `swing_overrides_count` are new additive
  fields that let callers audit when and how many cards had data-informed swings.

### Gating

The override computation runs only when:
1. `card_winrates` was successfully computed (rounds corpus exists, non-empty).
2. `any_gate_cleared` — at least one maindeck cell gated (confirms corpus is non-trivial).
3. `_top_opponents` is non-empty.

When any of these are absent, `card_swing_overrides = None` and the model is
byte-identical to pre-feature. All existing tests (which supply no rounds data) remain
green untouched.

## Implementation notes

### What's measurable vs not
- **Not measurable**: before/after-board swing. The `rounds` table records only
  match-level aggregate scores. No game number column exists. Individual game outcomes
  (pre-board vs post-board) are not in the schema.
- **Measurable (presence-correlational proxy)**: per-catalog-card×matchup lift from
  `card_value_matchup(..., board="side")`. Already used for maindeck OUT/IN planning;
  extended here to catalog cards.

### What was implemented
- `empirical_swing_proxy(cv: object) -> float | None` — converts a `CardValue`-shaped
  object to a bounded swing proxy. Returns None for speculative tier, negative/negligible
  lifts. Capped at 0.35. No circular imports (duck-typed, no import from analytics).
- `_EMPIRICAL_SWING_CAP = 0.35`, `_EMPIRICAL_SWING_MIN_LIFT = 0.02` — tunable constants.
- `_DATA_INFORMED_NOTE` — replacement for `_HEURISTIC_NOTE` when data-informed swings
  are used; labels the presence-correlational nature explicitly.
- `_build_coverage_model(..., card_swing_overrides=None)` — new gated-additive parameter.
  When provided, overrides card swing in `best_swing_for_tag` max computation.
- `recommend_sideboard` Step 3e — computes `card_swing_overrides` from `card_winrates`
  (already in scope from Step 2b), querying all catalog cards vs top opponents as sideboard
  cards. Aggregates max proxy across opponents. Uses `max(proxy, catalog_swing)` floor.
- `SideboardPackage.swing_data_informed: bool = False` and
  `SideboardPackage.swing_overrides_count: int = 0` — new additive audit fields.

### Files touched
- `src/legacy_engine/advisory/sideboard.py` — all implementation
- `tests/test_sideboard.py` — 14 new tests in `TestEmpiricalSideboardSwings`

### Test count
2150 total (baseline 2136 + 14 new). Full suite green.

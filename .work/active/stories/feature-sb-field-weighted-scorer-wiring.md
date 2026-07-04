---
id: feature-sb-field-weighted-scorer-wiring
kind: story
stage: done
tags: [advisory]
parent: feature-sb-field-weighted-scorer
depends_on: [feature-sb-field-weighted-scorer-impact]
release_binding: v0.2.0
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Wire impact into the coverage model + draw-prob copy-shaping in the ILP

## Brief

Replace `advise sideboard`'s scoring-core inputs in place: element weight becomes
`field_share × swing × impact(best hoser | my deck, that opp)`, and the per-copy marginal
(`_u_redundancy`/`_redundancy_penalty`) becomes draw-probability-driven so the ILP tapers copies.
Keep the ILP/greedy/τ/hedge machinery unchanged. Preserve a byte-identical path when impact
inputs are absent (honest-degrade + no-collection contract).

## Implementation

Covers parent feature **Units B3 + B4** — see `feature-sb-field-weighted-scorer` § Implementation
Units. File: `src/legacy_engine/advisory/sideboard.py` (`_build_coverage_model` element weights +
the copy-shaping). Tests: extend `tests/test_sideboard.py` (impact-modulated weights, copy taper,
byte-identical no-impact regression guard); re-baseline `tests/test_recommendation_coverage.py`.

## Implementation notes (2026-07-03)

**Files changed**: `src/legacy_engine/advisory/sideboard.py` (production), `tests/test_sideboard.py`
(tests). `src/legacy_engine/advisory/impact.py` and `src/legacy_engine/advisory/linchpins.py` were
read-only inputs (Unit B1/B2, already on main) — not modified.

**Unit B3 — impact-modulated element weights**

- `_build_coverage_model` gained two new keyword params: `opponent_linchpins: dict[str,
  list[Linchpin]] | None = None` and `opponent_cards: dict[str, dict[str, int]] | None = None`.
  My-side context (`my_colors`, `my_vulnerability_tags`) is NOT a new parameter — the function
  already receives `deck_colors`/`deck_tags` (used for the anti-hate elements), so those are
  reused directly for the `impact()` call. This keeps the signature smaller than the story
  sketch suggested and avoids threading duplicate data.
- Step 1 (`best_swing_for_tag`) now also tracks `best_hoser_for_tag[tag]` — the literal same
  `HoserCard` object that achieved the recorded best swing (switched the `max(...)` one-liner to
  an explicit `if effective_swing > current` comparison; the recorded swing VALUES are
  unchanged, only the extra hoser-identity bookkeeping is new).
- Step 2 multiplies each `(archetype, tag)` element's `share × swing` by
  `impact(best_hoser_for_tag[tag], archetype, opp_linchpins=opponent_linchpins[archetype],
  my_vulnerability_tags=deck_tags, my_colors=deck_colors, copies=1,
  opp_cards=opponent_cards[archetype]).score()`, guarded by `if opponent_linchpins is not
  None`. Anti-hate pseudo-elements (`_hate:<tag>`, no opponent archetype to evaluate against)
  are explicitly out of scope for this multiplier, consistent with Step 3b's existing
  `matchup_pressure` precedent (`if "|" not in key: continue`).
- **`copies=1` design decision** (not `hoser.max_copies`): the element weight represents "this
  tag has an answer at all," not a maxed-out playset. Unit B4 already owns the copy-count
  taper inside the ILP/greedy per-copy marginal; applying `draw_probability` a second time here
  at `max_copies` would double-apply the taper (once shrinking the element's base weight, again
  shrinking each additional copy inside the solver). Documented in both the module docstring
  and the `_build_coverage_model` docstring.
- **New DB glue** (`_archetype_linchpins_and_cards` / `_field_opponent_linchpins`, placed next
  to `_field_matchup_values`): resolves one archetype's `Linchpin` list + known maindeck
  composition via `card_frequencies(board="main")` + `_load_deck_cards`, objective-search-split
  style (all DB work happens here, once per archetype in the field, before
  `_build_coverage_model` is called — mirrors the `field_vulnerability_tags` one-query-per-
  archetype precedent already in this file). `linchpins_for_archetype` is called even when the
  corpus has zero decks for that archetype, because it *always* merges in curated
  `LINCHPIN_OVERRIDES` regardless of derived candidates — so a well-known archetype (e.g.
  Painter) still surfaces its curated linchpins against a thin/synthetic corpus.
- **Gating in `recommend_sideboard`**: `opponent_linchpins`/`opponent_cards` stay `None` (byte-
  identical weights) unless `_field_opponent_linchpins` finds at least one field archetype with
  a non-empty linchpin list — i.e. real corpus-derived composition data OR a curated override.
  This exactly mirrors the existing `any_gate_cleared` gate used for `matchup_pressure`. Verified
  empirically: the shipped `LINCHPIN_OVERRIDES` registry only curates `Painter`, `Show and
  Tell`, and `Eldrazi` (checked `data/linchpins/legacy.json`), and neither name appears anywhere
  in `tests/test_sideboard.py`; `derive_linchpins`'s role-priority list (`tutor`/`storm`/
  `ritual`/`fast_mana`) also doesn't match the existing hermetic fixtures' seeded cards (e.g.
  `TestRedundancyDecay`'s "Reanimator" corpus seeds `Reanimate`, whose `graveyard_recursion`
  role isn't in that priority list). Net effect: **all 2386 pre-existing tests pass unmodified**
  — the gate degrades to fully off for every existing hermetic fixture, with zero re-baselining
  needed anywhere in the suite.

**Unit B4 — draw-probability per-copy shaping**

- Minimal, surgical change: `_U_REDUNDANCY_DEFAULT` (previously the curated constant tuple
  `(1.0, 0.55, 0.25, 0.10)`) is now computed by a new `_draw_prob_redundancy_curve()` helper —
  `u(k) = (draw_probability(k) − draw_probability(k−1)) / (draw_probability(1) −
  draw_probability(0))`, i.e. the hypergeometric per-copy marginal normalized so the 1st copy
  is exactly `1.0` (preserving `_redundancy_penalty`'s `penalty(1) == 0` contract). Computed
  value: `(1.0, 0.6102, 0.3682, 0.2196)` vs the old `(1.0, 0.55, 0.25, 0.10)` — same concave
  tapering shape, now mechanics-grounded instead of a curated guess.
- `_u_redundancy`, `_redundancy_penalty`, the greedy per-copy subtraction, and the ILP's `z_c^k`
  incremental-copy linearization are all UNCHANGED — they only ever consume `_U_REDUNDANCY_DEFAULT`
  as an opaque tuple, so redefining the constant's source is a drop-in swap. `redundancy_strength`/
  `tau` == 0.0 still short-circuits to the exact byte-identical no-op path regardless of curve
  shape, so this is fully gated the same way it always was.

**Documentation discovery — `tests/test_recommendation_coverage.py` reference is stale**: per the
story brief and the parent feature's Testing section, this file was named for "deliberate
re-baseline for the new weighting." Reading it: it tests `acquire_plan`'s overpriced-printing
flag and `interaction_facts` evidence content — entirely unrelated to sideboard scoring. A sibling
story in this same epic (`feature-sb-effect-tagging-model-vocab-catalog`) already hit and
documented this exact same mismatch ("`tests/test_recommendation_coverage.py` needed no changes
— it tests `acquire_plan`"). Consistent with that precedent: made NO changes to this file (ran it
as part of the full suite; it passes unmodified). The real coverage-model tests for
`recommend_sideboard`/`_build_coverage_model` live in `tests/test_sideboard.py`, which is where
the new `TestImpactModulatedWeighting`, `TestArchetypeLinchpinsAndCards`, and
`TestDrawProbabilityRedundancyCurve` classes were added.

**Tests added** (`tests/test_sideboard.py`): `TestImpactModulatedWeighting` (byte-identical guard
with `opponent_linchpins=None`; linchpin-hit vs baseline-centrality weight ratio; symmetric
self-hosing hoser drops to `_SYMMETRY_FLOOR`; `cast_requires` hard-gates to 0.0 when unmet/absent
opponent composition data), `TestArchetypeLinchpinsAndCards` (curated-override-without-corpus-
decks, per-field keying, an integration smoke test on `TestRedundancyDecay`'s real "Reanimator"
corpus confirming the gate stays off and output is unchanged), `TestDrawProbabilityRedundancyCurve`
(curve matches hand-computed hypergeometric marginal; concave/decreasing; `u(1) == 1.0`).

**Verification**: `.venv/bin/python -m pytest -q` → **2399 passed** (2386 pre-existing + 13 new),
zero re-baselining required anywhere in the suite.

**Deviations from the story sketch**: (1) no new "my-side" params on `_build_coverage_model` —
reused `deck_colors`/`deck_tags` (see above); (2) `tests/test_recommendation_coverage.py` was
left untouched rather than re-baselined (it's unrelated to this feature — documented above with
reference to the sibling story that already found this). No escape hatch needed — both are
judgment calls within scope, not blocking design gaps.

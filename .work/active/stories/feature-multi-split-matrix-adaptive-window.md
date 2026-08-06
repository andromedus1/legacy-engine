---
id: feature-multi-split-matrix-adaptive-window
kind: story
stage: done
tags: [advisory]
parent: feature-multi-split-matrix
depends_on: [feature-multi-split-matrix-core-tally]
release_binding: v0.4.0
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Adaptive multi-split builder + window entry point

## Brief

The era-aware half (trickiest unit): `build_multi_split_adaptive` mirrors
`build_adaptive_matrix`'s skeleton (one maximal scan per distinct horizon, per-window pooled
hierarchy buckets, cross-era prior overrides via cached pre-boundary scans), with camp horizons
resolved exact -> parent -> ban-only through the new explicit `camp_parent` param on
`era_horizons` (no prefix parsing for multi-parent). Plus the thin composition layer:
`build_multi_split_inputs` in `advisory/window.py` (same `WindowResolution` mode dispatch +
audit lines; `build_advisory_inputs` and the ~15 spine call sites get ZERO edits) and
`staged_split_parents()` in `archetype/discovered.py`. Ships the adaptive half of the parity
test including `cell_windows`, `horizon_meta`, and cross-era `prior_source` label parity.

## Implementation

Parent feature `feature-multi-split-matrix` — Units 3 and 4 of `## Implementation Units`
(exact signatures, notes, and acceptance criteria there). Tests: the adaptive-parity part of
`tests/test_matchup_multi_split.py` + `tests/test_advisory_window_multi_split.py`. Hermetic
DBs only — never the default DB; use the explicit `horizons=` hook to pin windows
deterministically where era rows would be noisy.

## Implementation notes

**Adaptive parity HOLDS.** The one-pass era-windowed build reproduces N per-parent adaptive
builds field-for-field, windows and cross-era prior labels included. No assertion was weakened
and no design fallback was needed.

### What shipped

- `analytics/matchup.py` — `AdaptiveMultiSplitMatrix` + `build_multi_split_adaptive`. Same
  skeleton as `build_adaptive_matrix`: full maximal scan fixes inclusion, `era_horizons` resolves
  one horizon per entity, one `compute_match_results(split_variants=parents)` per DISTINCT
  horizon, cells sourced at `max(valid_since[subject], valid_since[opponent])`, thin (`n<100`)
  era-truncated cells overridden by a lazily-cached pooled pre-boundary scan. The only difference
  from the plain builder is granularity: each window's scan is pooled to parent-level opponents
  (`_pool_opponent_tallies`) and its hierarchy inputs reconstructed from camp sums
  (`_multi_hierarchy_inputs`) — `_cell_prior` is reused unchanged, as the design requires.
- `analytics/eras/consume.py` — additive `camp_parent` param on `era_horizons`, applied via a new
  `_resolve_parent` helper that prefers an explicit map entry and falls through to `_parent_label`
  otherwise. The single-split prefix path is untouched (existing `test_consume.py` green,
  unmodified).
- `advisory/window.py` — `MultiSplitAdvisoryInputs` + `build_multi_split_inputs`, same
  `WindowResolution` mode dispatch and lazy-import convention as `build_advisory_inputs`.
  `build_advisory_inputs` and every one of the ~15 spine call sites are byte-unchanged;
  `cli.py` has no hunk in this diff.
- `archetype/discovered.py` — `staged_split_parents()`.

### Decisions taken during implementation

1. **Per-window `camp_parent` for the hierarchy buckets, full-scan map for cell keys.** Each
   window bucket pools with its own scan's `mr.camp_parent`; the cell-emission `own_parent` skip
   and `MultiSplitMatrix.camp_parent` use the full-scan map so the key set is window-independent.
   A camp absent from a window then resolves `camp_of[camp] == camp` and falls back to its own
   marginal — byte-identical to what `_camp_hierarchy_inputs` does when a camp has no sibling
   tally in that window (it finds no LCO key and falls through the same way).
2. **The `// multi-split: N parents, M camp rows` audit line is emitted in EVERY mode**, not just
   adaptive as the design's Unit 4 note listed. The consumer (Unit 5) builds one adaptive matrix
   plus per-date uniform fallback matrices and needs the provenance marker on both; the line is
   additive on a brand-new entry point, so nothing existing can regress.
3. **`staged_split_parents` propagates `ValueError` on a malformed registry** rather than
   degrading to `[]`. Missing/empty → `[]` per the design; corruption is a bug, and this matches
   `load_discovered`'s own fail-fast contract.

### Test evidence

`tests/test_matchup_multi_split.py::TestAdaptiveParity` asserts, for every camp of every parent
against every parent-level opponent (and every unsplit subject against the plain build):

- all 13 `MatchupCell` fields — `archetype_a`, `archetype_b`, `wins`, `n`, `p_raw`, `p_shrunk`,
  `ci_low`, `ci_high`, `tier`, `is_mirror`, `display`, `prior_mean`, `prior_source`;
- `cell_windows[(subject, opponent)]` and `cell_windows[(subject, subject)]` equal to the
  per-parent build's;
- `horizon_meta[entity]` equal as a whole `EraHorizon` (`since`/`source`/`trigger`/`alarm`) for
  camp subjects AND for parent-level opponents, plus `valid_since` parity for both;
- the cross-era label verbatim —
  `"pre-disturbance value (window < 2026-03-01); hierarchy: parent cell (leave-camp-out)"` on a
  camp cell whose opponent column is POOLED (Painter's camps summed back to `Painter`), which is
  the exact interaction the design flagged as riskiest;
- a ban-only-truncated cell (`("Control", "Delver")`) keeps `prior_source == "marginal"` — a
  ban-only boundary must never take a cross-era prior.

Fixture: the merged two-parent corpus plus `entity_eras` rows covering all three horizon sources
in one DB — camp-exact (`Doomsday [Murktide]`, own row), parent-inherited (`Doomsday [Turbo]`),
and ban-only both undated (`Painter` and its camps) and dated (`Delver`, via rounds-free
pre-ban decks running Entomb, so a ban-only horizon with a real date exists without perturbing a
single match tally). `TestAdaptiveFixtureCoversEveryHorizonSource` pins that all three are live,
and the parity tests self-assert non-vacuity (`cross_era_cells >= 4` on camp rows, `>= 1` on
unsplit rows) so they cannot pass by never exercising the override.

### Non-vacuity proof (mutation testing)

Seven mutations scoped to `build_multi_split_adaptive`'s body only — all killed:

| mutation | tests RED |
|---|---|
| drop the cross-era prior override | 3 |
| source cells from the full scan instead of their own horizon window | 3 |
| camps inherit the parent horizon instead of their camp-exact era row | 2 |
| drop the explicit `camp_parent` map from the horizon lookup | 2 |
| cross-era prior over the POST-boundary hierarchy (label unchanged, mean wrong) | 3 |
| emit the `(camp, own_parent)` column | 1 |
| perturb one per-horizon pooled tally by +1 win | 4 |

Method note worth keeping: a first attempt at the "post-boundary hierarchy" mutation used a plain
`str.replace` and silently patched `build_adaptive_matrix`'s identical line too — mutating both
sides of a parity test symmetrically makes it look robust when it is not. Mutations of a parity
test MUST be scoped to one side.

### Measured economics (live corpus, read-only)

30 staged parents, `min_row_share=0.001`: one `build_multi_split_adaptive` = **8.96s** (34
distinct horizons, 179 subjects × 94 opponents, 16,826 cells). One per-parent
`build_adaptive_matrix(split_variant=P)` = **7.66s**, so the old 30-parent sweep ≈ **230s**.
~26× reduction — matching the design's ~25× prediction, and the scan count is distinct-horizons,
not parents × horizons (asserted in `test_scan_count_is_distinct_horizons_not_parents_times_horizons`).

### Scope

Units 3 and 4 only. Unit 5 (best-call page migration, cross-camp P(best), docs roll-forward) is
`feature-multi-split-matrix-best-call-onepass` and is untouched here — nothing consumes the new
entry points yet, so this lands with zero behavior change to any shipped surface.

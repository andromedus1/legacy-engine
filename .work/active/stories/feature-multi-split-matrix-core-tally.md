---
id: feature-multi-split-matrix-core-tally
kind: story
stage: done
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

## Implementation notes

**Parity HELD.** The design's riskiest assumption is confirmed: one multi-split build reproduces
the per-parent builds field-for-field. No fallback was needed; Unit 3 can proceed on this kernel.

### Unit 1 — `src/legacy_engine/analytics/match_results.py`
- `MatchResults.camp_parent: dict[str, str]` (additive, default `{}`).
- `compute_match_results(..., split_variants=None)`; both params → `ValueError`. Both normalize to
  one `split_set`; `_split_set_label` is the membership-test generalization of `effective_label`
  (which is untouched). `split_set == frozenset()` is the literal identity path.
- `camp_parent[label] = archetype` is recorded at relabel time — the labeler is the SSOT. No prefix
  parsing anywhere, per the `Painter` / `Blue Painter` hazard (decision 7); a dedicated test pins
  that both archetypes' camps resolve to their own parent.

### Unit 2 — `src/legacy_engine/analytics/matchup.py`
- `_pool_opponent_tallies(mr, camp_parent)` — opponent-side pooling to parent level; pairs whose
  opponent pools to the subject's own parent are dropped (decision 2).
- `_multi_split_inclusion(mr, min_row_share)` — private helper (not in the design's signature list;
  factored out because Unit 3's adaptive builder needs the same inclusion step). Returns
  `(subjects, opponents, parents)` by reconstructing parent records from camp sums over the
  relabel-invariant `2*(decisive+mirror)` denominator.
- `_multi_hierarchy_inputs(...)` — the many-parent generalization of `_camp_hierarchy_inputs`;
  `_cell_prior` is consumed **unchanged**. The `lco >= 0` assert is carried over verbatim.
- `MultiSplitMatrix` + `ranking_view()` + `build_multi_split_matrix(...)` exactly per the design.
- Not exported from `analytics/__init__.py` — Units 4/5 import from `matchup.py` directly, and
  leaving `__init__` alone keeps the byte-identical-default surface untouched.

### Tests
- `tests/test_match_results_multi_split.py` (21 tests) — identity paths, singleton equivalence
  (`matchups`/`archetypes`/`coverage`/`mirror_n`/`camp_parent`, full-corpus and windowed),
  two-parent simultaneous relabel, the `decisive + mirror` invariance, parent-marginal
  reconstruction, the `Painter`/`Blue Painter` prefix trap, and both-params `ValueError`. It also
  owns the shared hermetic two-parent fixture (2 split parents × 2 named camps + unlabeled
  residue, 3 plain archetypes incl. a below-floor `Elves`, two tournaments on distinct dates,
  cross-parent / same-parent-cross-camp / camp-mirror / plain-mirror pairings).
- `tests/test_matchup_multi_split.py` (56 tests) — pure-kernel tests on hand-built `MatchResults`
  (no DB), inclusion-set equality vs the plain/per-parent builds, `(camp, own_parent)` absence,
  singleton and empty-`parents` degeneracy, and the `ranking_view()` + `rank_decks` contract.

**The parity test** (`TestUniformParity`) asserts, over 6 `(min_row_share, since, until)`
combinations — `(0.02, full)`, `(0.02, since=late)`, `(0.02, until=late)`, `(0.0, full)`,
`(0.0, since=late)`, `(0.0, early..late)`:
1. `set(per.archetypes) - camps == set(msm.opponents) - {parent}` — the key sets agree exactly.
2. For every camp × every opponent (excluding the parent's own absent column), and for every camp
   mirror: all 13 `MatchupCell` fields equal `build_matrix(split_variant=parent)`'s cell —
   `archetype_a`, `archetype_b`, `wins`, `n`, `p_raw`, `p_shrunk`, `ci_low`, `ci_high`, `tier`,
   `is_mirror`, `display`, `prior_mean`, `prior_source`.
3. Every unsplit subject's cells + mirror equal the plain `build_matrix(con)`'s, same 13 fields.

Non-vacuity was verified by three mutations, each of which turns the parity assertions red:
perturbing the pooled tally arithmetic (8 failures), emitting the `(camp, own_parent)` column
(6 failures), and a prior-only regression that drops zero-`n` LCO references so camp cells fall
back to the marginal source (7 failures).

### Verification
- Full suite green; zero existing tests changed (the byte-identical-default gate — including the
  `report matchups` freshness-stripped body goldens).
- `ruff check src/`: the four touched files are clean; the repo's 23 findings are pre-existing
  (CI runs this non-blocking).

---
id: epic-stable-era-windows-shrinkage-hierarchy
kind: story
stage: done
tags: [analytics, methodology]
parent: epic-stable-era-windows-shrinkage
depends_on: []
release_binding: v0.4.0
gate_origin: null
created: 2026-07-12
updated: 2026-07-12
---

# Hierarchical + cross-era cell priors

## Brief
Units 1+2: cell prior chain (camp→LCO-parent′→marginal′→0.5), cross-era prior for thin post-boundary cells, prior_source labels — beta_binomial_shrink_to is the only primitive.

## Implementation
Parent feature `epic-stable-era-windows-shrinkage` — exact contracts + acceptance criteria there.

## Implementation notes

**Unit 1 (hierarchical cell prior)**, `src/legacy_engine/analytics/matchup.py`:
- `_camp_hierarchy_inputs(mr, labels, split_variant)` derives one window's `(marginals,
  parent_cells_lco, camp_of)` entirely from a single already-computed `MatchResults` — zero extra
  DB scans. Key insight: because every match a camp plays is attributed to exactly one camp label,
  summing wins/losses separately across all camp siblings of a split reproduces the unsplit
  parent's marginal AND its directed cell vs any external opponent exactly (a cross-camp match is
  a directed win/loss pair at camp level but a mirror, +1 win +1 loss to the same label, at the
  unsplit level — summed wins/losses match either way). LCO = parent totals (sum of siblings) minus
  the camp's own tally; asserted `>= 0` (never clamped) — structurally guaranteed non-negative
  since the camp's own tally is one non-negative term inside the sum being subtracted from, so
  this assert can never actually trip on real data (defensive, not reachable — documented in the
  docstring rather than force-tripped in a test).
- `_cell_prior(subject, opponent, *, marginals, parent_cells_lco, camp_of)` — pure, per the
  parent feature's exact signature. Camp cells with a valid LCO reference shrink toward the LCO
  parent cell (itself shrunk toward the parent's own shrunk marginal); everything else (plain
  archetype cells, and camp-vs-sibling-camp cells with no meaningful unsplit parent reference)
  shrinks toward the subject's own shrunk marginal.
- `build_cell` gained `prior_mean: float = 0.5, prior_source: str | None = None` (additive
  defaults — byte-identical for any caller that doesn't pass one). n=0 cells now return
  `p_shrunk == prior_mean` (design decision: "n=0 cells return the prior mean with the source
  label") instead of `None` — `p_raw`/CI stay `None` (no observations); the raw-must-travel-with-
  shrunk honesty rule is enforced by the existing `display=False` gate (n=0 < 30), not by hiding
  `p_shrunk`. Updated the one pre-existing test asserting the old n=0 behavior
  (`tests/test_matchup.py::TestCellBuilder::test_n0_cell_p_raw_none`) to match — this is the
  epic's own explicit contract change, not an accidental regression.
- `build_matrix` and `build_adaptive_matrix` both call `_camp_hierarchy_inputs`/`_cell_prior` for
  every non-mirror cell. In `build_adaptive_matrix`, hierarchy inputs are computed once PER
  DISTINCT `since` bucket (reusing the existing `mr_by_since` scans — no new
  `compute_match_results` calls for Unit 1) so a cell's prior is always anchored in the SAME
  window its raw data came from, never a wider/stale-era population.
- `MatchupCell` gained `prior_mean`/`prior_source` (additive, default `None`). Mirror cells
  untouched (fixed 0.5, no prior fields set).

**Unit 2 (cross-era prior)**, same file, `build_adaptive_matrix` only:
- `_era_sourced_boundary(a, b, s_ab)`: true when the contributing archetype(s) whose `valid_since`
  equals the cell's window `s_ab` have `horizon_meta[...].source in ("era", "era-parent")` — i.e.
  the truncation came from a real detected disturbance, not a ban-only fallback (a ban-only
  boundary has no persisted "pre-disturbance era" to compute from, so it never gets this
  treatment).
- `_cross_era_prior(a, b, boundary)`: computes (once per distinct boundary date, cached in
  `pre_mr_cache`/`pre_hierarchy_cache`) the same directed cell over the PRE-boundary window
  `[None, boundary)`, shrinks it through the SAME hierarchy chain using PRE-boundary
  marginals/LCO cells, and returns `(cross_era_mean, "pre-disturbance value (window < <date>);
  hierarchy: <source>")`. Applied only when the post-boundary cell is thin (`n < 100`) — wins over
  the Unit 1 hierarchy prior when both apply, per the locked design decision.

**Worked example verified** (the epic's motivating case, `tests/test_matchup_hierarchy.py` +
`.work/active/features/epic-stable-era-windows-shrinkage.md`'s Unit 1 AC): camp cell raw 5/16
(31.25%, the epic's "31.2%"), LCO-parent totals 45/101 shrunk toward parent marginal 0.5 →
prior_mean = 0.452586 (45.3% to 1 decimal), final shrunk estimate = 0.380284 → **38.0%** to 1
decimal, materially different from the flat-0.5 result (`beta_binomial_shrink(5, 16)` = 0.403226,
40.3%) — reproduced BOTH as a pure `_cell_prior` fixture test and end-to-end through a hand-built
DuckDB corpus via `build_matrix(split_variant=...)`.

**Tests**: new `tests/test_matchup_hierarchy.py` (15 tests) covering `_cell_prior` pure fixtures,
the end-to-end worked example, LCO-subtraction unit coverage, and the cross-era prior (thin vs.
established post-boundary, ban-only-sourced boundaries excluded, undisturbed cells unaffected).
Updated `tests/test_matchup.py`'s one affected pre-existing test. Ran ruff on both touched source
files and both touched/new test files (clean). Full suite: `.venv/bin/python -m pytest -q` →
2943 passed, 1 pre-existing xfail, **1 expected failure**
(`test_matchup_split_variant.py::TestGoldenReportMatchupsDefault::test_default_body_byte_identical`)
— this is the pinned golden the sibling `-shrinkage-goldens` story re-pins; confirmed the shift is
exactly what the new hierarchy formula predicts (Control's marginal is entirely self-referential
in that 2-archetype fixture, so its own cell's prior pulls harder than flat 0.5 — 17%→7%, a known,
documented, self-consistent EB simplification the project already accepts in `card_value.py`'s
own two-level chain).

No production bugs found or parked during this story.

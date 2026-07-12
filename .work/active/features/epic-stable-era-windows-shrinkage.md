---
id: epic-stable-era-windows-shrinkage
kind: feature
stage: review
tags: [analytics, methodology]
parent: epic-stable-era-windows
depends_on: [epic-stable-era-windows-consumption]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-12
---

# Hierarchical cell shrinkage: parent-anchored + cross-era priors as default

## Brief

Replaces the flat-0.5 matchup-cell prior with the hierarchy the repo's own
two-level-empirical-bayes pattern prescribes: a camp cell shrinks toward the SHRUNK parent-
archetype cell (leave-camp-out, so the parent estimate excludes the camp's own matches — no
double-counting), the parent cell shrinks toward its marginal, the marginal toward 0.5. PLUS the
cross-era prior this epic makes necessary: a thin post-disturbance cell shrinks toward its own
pre-disturbance value (labeled as such) instead of flat 0.5 — the right prior for young eras.
Worked motivating case: Lands[Sphere/Tomb] vs S&T raw 31.2 n=16 displays 40.3 today (pulled
toward 50); parent-anchored (~45.3) it reads ~38. Becomes the DEFAULT displayed estimate
everywhere in the same release as the window swap (design decision: one user-visible all-cells
shift); triple-display (shrunk%|raw% n=) is the honesty carrier — never a shrunk estimate without
raw + n. Design must specify: shrink-strength allocation across levels, leave-camp-out estimator,
interaction between the hierarchy and the cross-era prior (which anchor wins when both apply),
and the shrinkage-compression caveat (camp S* compressed toward 50 vs parents — compare camps to
camps) that the 07-11 analysis logged.

## Epic context

- Parent epic: `epic-stable-era-windows`
- Position in epic: final layer — needs era boundaries (ledger) and lands on top of the
  re-windowed cells, re-pinning goldens once at the end.

## Inherited design decisions

- Shrinkage rollout — one shot, both default together (design decision): default in the same
  RELEASE as stable_since windows; goldens re-pinned; triple-display carries it.
- idea-hierarchical-cell-shrinkage absorbed in full: camp→parent chain AND cross-era prior (scope
  decision).

## Research briefs

- `docs/briefs/change-point-detection.md` (era boundaries the cross-era prior keys on).
- In-repo: `.agents/skills/patterns/two-level-empirical-bayes.md` — the primitive
  (`beta_binomial_shrink_to`) and the shrink-toward-SHRUNK-parent chain (card_value.py precedent).

## Foundation references

- `docs/ARCHITECTURE.md` — analytics/matchup.py (`beta_binomial_shrink_to`, `SHRINK_STRENGTH`,
  cell assembly), analytics/card_value.py (the existing two-level chain to mirror).
- Patterns: two-level-empirical-bayes, confidence-metadata, freshness-stripped-cli-body-golden,
  honest-degrade-marker (cross-era-prior label).

## Design decisions

Resolved with judgment under autopilot (2026-07-12):

- **The cell prior chain** (replacing flat 0.5 everywhere, per the one-shot decision):
  - Parent-archetype cell: shrink toward the SUBJECT archetype's shrunk marginal WR (which
    itself shrinks toward 0.5 at the same strength) — cell → marginal′ → 0.5.
  - Camp cell: shrink toward the LEAVE-CAMP-OUT parent cell estimate (parent cell computed
    excluding the camp's own matches, then itself shrunk per the parent chain) — camp →
    LCO-parent-cell′ → marginal′ → 0.5. No double-counting by construction.
  - Cross-era prior: when a cell's window was truncated at a stable_since boundary AND the
    post-boundary cell is below established tier (n<100), the prior MEAN becomes the same
    cell computed over the PRE-boundary window (itself shrunk per the normal chain); strength
    unchanged. When both the hierarchy and the cross-era prior apply, the CROSS-ERA mean wins
    (it is the more specific prior) and the label carries both.
- **Strength**: SHRINK_STRENGTH=15 at every level, chained — no new constants; the existing
  `beta_binomial_shrink_to` is the only primitive used (two-level-empirical-bayes pattern).
- **Labels, not new display**: triple-display (shrunk%|raw% n=) already carries honesty; cells
  gain a `prior_source` label ("marginal" / "parent cell (leave-camp-out)" / "pre-disturbance
  value") surfaced in the audit/explain paths, so a shrunk number's anchor is always visible.
- **`beta_binomial_shrink` (flat-0.5) stays** for non-cell consumers (card_value's own chain is
  untouched — it already implements its own two-level hierarchy); only MATCHUP CELL assembly
  moves to the new chain.
- **Goldens re-pin here** (the final all-cells shift; hermetic-DB goldens WILL move this time —
  shrink-toward-marginal differs from flat-0.5 even without era data). Every re-pin diff must be
  explainable as a shrunk-value change with raw/n unchanged.

## Implementation Units

### Unit 1: hierarchical cell prior in matchup assembly
**File**: `src/legacy_engine/analytics/matchup.py`
**Story**: `epic-stable-era-windows-shrinkage-hierarchy`
`_cell_prior(subject, opponent, *, marginals, parent_cells_lco, camp_of) -> tuple[float, str]`
(prior mean + source label); cell assembly calls `beta_binomial_shrink_to(wins, n,
prior_mean=prior)` instead of `beta_binomial_shrink`. LCO parent cells: when split_variant is
active, parent cell (a_parent vs b) counts EXCLUDE the subject camp's matches (compute from the
same match_results pass — camp rows are already separate records, so parent-LCO = parent totals
minus camp totals; guard n>=0). MatchupCell gains `prior_mean: float | None = None`,
`prior_source: str | None = None` (additive). Mirror cells stay fixed 0.5.
**AC**: hand-built fixtures — camp cell shrinks toward LCO parent (worked example from the epic:
raw 31.2% n=16 with parent′ 45.3 reads ≈38, NOT 40.3); parent cell shrinks toward its shrunk
marginal; n=0 cell returns the prior with source label; existing tier gates untouched; mirror
0.5 untouched.

### Unit 2: cross-era prior
**Files**: `src/legacy_engine/analytics/matchup.py` (+ small helper in analytics/eras/consume.py)
**Story**: `epic-stable-era-windows-shrinkage-hierarchy`
In `build_adaptive_matrix`, for each cell whose window since came from an era boundary (know this
from horizon_meta source=="era"/"era-parent") and whose post-boundary n < 100: compute the same
directed cell over the PRE-boundary window (one extra compute_match_results per distinct
boundary date — reuse the existing per-valid_since batching), shrink it per the normal chain,
use it as prior mean, label "pre-disturbance value (window < <date>)". Both-sides-truncated
cells use the max boundary consistently with cell_windows.
**AC**: synthetic corpus with an implanted boundary — thin post-boundary cell reads between raw
and pre-boundary value with the label; established post-boundary cell (n>=100) ignores the
cross-era prior; cells with no boundary unchanged from Unit 1 behavior.

### Unit 3: goldens + display surfacing
**Files**: pinned golden tests + wherever cells render prior labels (report matchups explain
paths / split-variant rows)
**Story**: `epic-stable-era-windows-shrinkage-goldens`
Re-pin the full-body goldens (diffs must show ONLY shrunk-value + label changes; raw/n identical
— assert that property in the re-pin commit message); surface `prior_source` where cells are
rendered with audit detail (the `--split-variant` rows at minimum: append `prior: <source>` to
the existing tier annotation), respecting the never-compare-shrunk-floors-across-n rule (no new
cross-cell comparisons introduced).
**AC**: full suite green; goldens' raw/n columns byte-identical pre/post; camp rows show prior
labels.

### Unit 4 (bundled follow-up story): mixed-horizon consumers
**Story**: `epic-stable-era-windows-mixed-horizon-consumers` (already at implementing)
Per its brief: sideboard per-opponent equity windows resolve through era_horizons (one horizon
source per recommendation); dashboard seeded-eras test; doc lines. Byte-identical without era
data.

## Implementation Order
1. Unit 1 → 2. Unit 2 → 3. Unit 3 → 4. Unit 4 (independent files, same branch)

## Risks
- **LCO subtraction** must never produce negative counts (camp records are a partition of parent
  records in the split pass — assert, don't clamp silently).
- **Chained shrinkage compounds** — the marginal′ anchor moves every cell slightly; the goldens
  quantify the shift and the raw/n-identical property bounds the blast radius.

## Closing note (2026-07-12)

All three items shipped, each its own commit on `feature/stable-era-shrinkage`:
`epic-stable-era-windows-shrinkage-hierarchy` (Units 1+2), `epic-stable-era-windows-shrinkage-goldens`
(Unit 3), `epic-stable-era-windows-mixed-horizon-consumers` (Unit 4). Full detail — files touched,
worked-example numbers, golden diff, per-item test counts — lives in each story's own
"Implementation notes" section. Full suite green throughout (`.venv/bin/python -m pytest -q`,
final state 2950 passed / 1 pre-existing xfail). No production bugs found or parked. LCO
subtraction's `assert >= 0` is structurally unreachable on real data (documented in
`_camp_hierarchy_inputs`'s docstring) rather than force-tripped by a test.

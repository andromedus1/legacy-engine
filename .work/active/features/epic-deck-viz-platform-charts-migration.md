---
id: epic-deck-viz-platform-charts-migration
kind: feature
stage: review
tags: [viz]
parent: epic-deck-viz-platform
depends_on: [epic-deck-viz-platform-foundation]
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# charts.py Migration — Vega-Lite builders replace matplotlib

## Brief
Migrate the four existing `analytics/charts.py` surfaces off matplotlib and onto Vega-Lite, then drop
the `matplotlib` dependency. The migration is cheap because `charts.py` already separates a pure,
matplotlib-free prep layer (`_heatmap_model`/`_metashare_model`/`_tier_model`/`_trends_model` →
`HeatmapModel`/`BarModel`/`TierModel`/`TrendModel` dataclasses that bake in ALL the honesty logic —
masking, fringe, thin-regime banding, caveat strings) from the matplotlib `render_*` functions.

Deliver: (1) the four prep functions + their model dataclasses moved into `viz/` (e.g. `viz/models.py`);
(2) four hand-built Vega-Lite spec builders against those models — `spec_metashare(BarModel)` (horizontal
bar, muted speculative tier, hatched fringe), `spec_matchup_heatmap(HeatmapModel)` (rect + text layer,
`redyellowgreen` over `values`, grey masked cells — the format-level N×N), `spec_tier_list(TierModel)`
(S/A/B columns), `spec_trends(TrendModel)` (line + point, gaps for `None`, shaded thin-regime bands);
(3) repoint existing callers; (4) delete the matplotlib `render_*` functions and remove `matplotlib`
from `pyproject.toml` as the final unit, keeping the suite green throughout. Each builder gets a JSON
snapshot fixture + a `jsonschema` validation test (the foundation's convention).

This feature does NOT add the per-deck-only tiles (matchup ROW bar, positioning bar, consensus list) or
the dashboard/CLI — those are the dashboard feature, which REUSES `spec_metashare` and `spec_trends`
from here. Scope is strictly the 1:1 migration of the four standalone chart surfaces.

## Epic context
- Parent epic: `epic-deck-viz-platform`
- Position in epic: **consumer of foundation; producer for dashboard** — the dashboard's meta-share
  (Tile A) and trends (Tile C) tiles reuse `spec_metashare` / `spec_trends` built here.

## Inherited design decisions
- **Keep the pure `_*_model` prep layer; swap only the backend.** Move prep models into `viz/`, write
  `spec_*` builders, drop matplotlib `render_*` + the dependency last (Brief §5, the migration map).
- Hand-built Vega-Lite dicts; test-time `jsonschema` + JSON snapshots (inherited from foundation).
- **Confidence/labels carry through every chart** — masked/`display=False` cells greyed + "insufficient",
  speculative muted, fringe hatched, thin regimes banded; subtitles from existing `*.subtitle`
  (`confidence-metadata` pattern, Brief §3.1).

## Design decisions
- **Visual tone = dark + minimal** (Andrew, `--only-questions`; see the foundation feature for the
  theme details). All four migrated charts must read correctly on the dark theme — same palette/axis
  adjustments (light text/axes, swapped categorical-black).
- (No other open forks: prep-model location — `viz/models.py` per the brief — and the tier-list
  Vega-Lite representation — faceted text vs three stacked bars — are feature-design judgment calls
  consistent with the dark-minimal tone.)

## Research briefs
- [docs/briefs/deck-viz-platform.md](../../../docs/briefs/deck-viz-platform.md) — §5 (the charts.py
  migration map: surface → prep model → new builder → Vega-Lite mark), §4 (Tile A/C contracts these
  builders also serve).

## Design decisions (added at feature-design, autopilot judgment)
- **Plan B split — this feature migrates the chart MACHINERY; the dashboard feature owns the new CLI
  surface.** charts-migration moves the prep models, adds the Vega-Lite spec builders, deletes
  `charts.py`, drops matplotlib, AND removes the now-orphaned `report … --chart-dir` hook. The
  replacement CLI (`viz meta|matchups|trends|tiers`) lands in the dashboard feature alongside the `viz`
  group. Rationale: keeps each feature independently green and avoids rewriting the `--chart-dir`
  handlers twice (once to a vega backend, once to remove). Between the two features the chart-export CLI
  is briefly absent — acceptable inside one epic shipped together (late-binding release).
- **Prep models + prep fns move to `viz/models.py` verbatim** (they're already matplotlib-free; they
  import domain records, so `viz → analytics`/`models` is a clean presentation→data edge).
- **Tier-list Vega-Lite representation = horizontal bars faceted by bucket** (row-facet S/A/B, `x=share`,
  `y=archetype`) — reuses the bar idiom, legible, snapshot-stable. (The faceted-text alternative was the
  other only-questions option; bars chosen.)
- **Spec builders consume the prep models, not raw records** — `spec_*(model)` so the honesty logic
  (masking/fringe/thin/caveat) stays in one place and the builders are pure dict→dict-testable.

## Architectural choice
Two new modules under `viz/`: `viz/models.py` (the four prep dataclasses + their `_*_model` prep
functions, lifted verbatim from `charts.py`) and `viz/specs.py` (four `spec_*` builders that turn a prep
model into a hand-built Vega-Lite v6 dict). `charts.py` is deleted and matplotlib dropped. Considered
(A) leave the prep fns in `analytics/` and only add `viz/specs.py` — rejected, the prep models are a
presentation concern (view-models), they belong with the renderer, and `analytics/__init__` should stop
re-exporting chart code; (B) one combined `viz/specs.py` holding both models and builders — rejected,
the model/builder split mirrors the foundation's theme/render split and keeps prep logic testable apart
from spec shape. Chosen: `viz/models.py` + `viz/specs.py`.

## Implementation Units

### Unit 1: viz/models.py — lift the prep layer
**File**: `src/legacy_engine/viz/models.py`
Move verbatim from `analytics/charts.py` (they are already matplotlib-free):
- `@dataclass HeatmapModel{archetypes, values, masked, mirror, annotations, caveat, title}` + `_heatmap_model(matrix: MatchupMatrix) -> HeatmapModel`
- `@dataclass BarModel{labels, shares, muted, fringe, tiers, subtitle, title}` + `_metashare_model(report: MetaShareReport) -> BarModel`
- `@dataclass TierModel{buckets, subtitle, title}` + `_tier_model(report, *, s_min=0.10, a_min=0.05, b_min=0.02) -> TierModel`
- `@dataclass TrendModel{regime_labels, archetypes, series, thin_regimes, subtitle, title}` + `_trends_model(series: TrendSeries) -> TrendModel`
**Implementation Notes**: keep imports (`MatchupMatrix` from `models.matchup`, `MetaShareReport`/`TrendSeries` from analytics) — the prep logic is unchanged; this is a pure move. Keep the `_is_never_other` / threshold helpers `_tier_model` relies on.
**Acceptance Criteria**:
- [ ] The four prep fns produce byte-identical models to the pre-move `charts.py` versions (existing prep-model tests pass after re-pointing imports to `viz.models`).

### Unit 2: viz/specs.py — Vega-Lite builders
**File**: `src/legacy_engine/viz/specs.py`
```python
from __future__ import annotations
from legacy_engine.config import VL_SCHEMA_URL
from legacy_engine.viz.models import BarModel, HeatmapModel, TierModel, TrendModel

def _base(description: str, title: str) -> dict:
    return {"$schema": VL_SCHEMA_URL, "description": description, "title": title}

def spec_metashare(m: BarModel) -> dict: ...          # horizontal bar; y=label (sorted), x=share;
    # opacity 0.35 where muted; fringe rows greyed; tooltip share/tier; subtitle via title.subtitle
def spec_matchup_heatmap(m: HeatmapModel) -> dict: ... # rect + text layer; color=p_shrunk redyellowgreen
    # domain [0,1] midpoint .5; masked cells -> null/grey; text = annotations; caveat as subtitle
def spec_tier_list(m: TierModel) -> dict: ...          # bar faceted by bucket row (S/A/B); x=share,y=archetype
def spec_trends(m: TrendModel) -> dict: ...            # line+point; x=regime (ordinal, chronological),
    # y=share, color=archetype; None -> gaps (omit, don't 0); rect band layer where thin_regimes
```
**Implementation Notes**:
- Hand-built dicts only (no Altair). Every spec sets `$schema` (v6) + a non-empty `description`.
- Do NOT set `config` — the theme is injected at render time by `strip_and_inject`.
- redyellowgreen scale matches `THEME.range.diverging`; the heatmap relies on the injected theme.
- For trends gaps: omit the (archetype, regime) datum entirely so the line breaks; never emit share=0.
**Acceptance Criteria**:
- [ ] Each builder returns a dict with `$schema == VL_SCHEMA_URL` and a non-empty `description`.
- [ ] `assert_renders(spec_X(model))` passes for each builder (real Vega-Lite compiler via render_png).
- [ ] JSON snapshot fixtures match for a representative model per builder.
- [ ] Heatmap masks cells where `masked[i][j]` (null/grey, not a fabricated rate); mirror annotated.
- [ ] Trends omits `None` cells (gaps), shades `thin_regimes` bands.

### Unit 3: delete charts.py + drop matplotlib
**Files**: remove `src/legacy_engine/analytics/charts.py`; edit `pyproject.toml` (remove the
`"matplotlib>=3.8",` line).
**Acceptance Criteria**:
- [ ] `rg matplotlib src/ tests/` returns nothing.
- [ ] `import legacy_engine.analytics` succeeds with charts exports removed.

### Unit 4: repoint callers
**Files**:
- `src/legacy_engine/analytics/__init__.py` — remove the `from ...charts import (...)` block and the
  `render_*` / model names from `__all__`.
- `src/legacy_engine/cli.py` — remove the `--chart-dir` option + its `if chart_dir:` blocks from
  `report meta`, `report matchups`, `report trends`, `report tiers` (4 commands), plus the now-unused
  `_chart_filename` helper and the `TierModel`/charts imports. (The replacement `viz` CLI group lands in
  the dashboard feature.)
- `src/legacy_engine/viz/__init__.py` — add `spec_metashare/spec_matchup_heatmap/spec_tier_list/spec_trends`
  and the four prep models/fns to the re-export surface.
**Acceptance Criteria**:
- [ ] `legacy report meta|matchups|trends|tiers` run without `--chart-dir` (no chart option present); text output unchanged.
- [ ] No import references `analytics.charts` anywhere.

### Unit 5: tests
**Files**: rename/rework `tests/test_charts.py` → `tests/test_viz_specs.py`:
- Keep the prep-model tests (re-point imports to `viz.models`).
- Add per-builder: a JSON snapshot assertion + `assert_renders` (real compiler).
- Remove the old CLI `--chart-dir` smoke tests (the option is gone; the `viz` CLI tests arrive with the
  dashboard feature). Confirm no other test imports `analytics.charts` or uses `--chart-dir`.
**Acceptance Criteria**:
- [ ] Full suite green; no references to `charts`/`--chart-dir`/matplotlib remain.

## Implementation Order
1. **Unit 1 (viz/models.py)** — lift prep layer; re-point its imports.
2. **Unit 2 (viz/specs.py)** — builders against the moved models.
3. **Unit 4 (repoint callers)** — analytics/__init__, cli.py, viz/__init__.
4. **Unit 3 (delete charts.py + drop matplotlib)** — after callers no longer import it.
5. **Unit 5 (tests)** — move prep-model tests, add builder tests, drop --chart-dir tests. Run full suite.

## Testing
- **Unit (`tests/test_viz_specs.py`)**: the four prep fns (moved tests) + four builders (snapshot + render
  via `assert_renders`); heatmap masking/mirror; trends gaps + thin bands; tier faceting.
- **Integration**: `legacy report meta|matchups|trends|tiers` still run (text path) with `--chart-dir`
  gone (covered by existing test_cli.py once the option is removed — update any assertion that referenced it).
- **Test data**: reuse the rounds-bearing DB fixtures already used by test_charts.py; `make_vl_spec` not
  needed here (builders produce their own specs).

## Risks
- **Heatmap + tier-facet spec correctness** is the trickiest — **Fallback**: design heatmap as a
  `rect`+`text` layered spec and tier as a row-faceted bar; if a faceted tier spec proves awkward in VL,
  fall back to three `vconcat` bar panels (same data, simpler). Validate via `assert_renders`.
- **Removing `--chart-dir` leaves no chart CLI until the dashboard feature** — **Fallback**: acceptable
  within one epic; if it must not regress mid-epic, the dashboard feature is the very next item in the
  chain and restores it as `viz meta|matchups|trends|tiers`.

## Child stories
None — single-stride, tightly-coupled migration (one module family, ~5 units, one pass). Stories would be overhead.

## Foundation references
- `docs/ARCHITECTURE.md` — `viz/` module section; the `charts.py` "being superseded" note + the
  drop-matplotlib dependency note.
- `src/legacy_engine/analytics/charts.py` — the 594-LoC migration source (prep/render split; deleted).

## Implementation notes

### What moved / was created / deleted

- **Created** `src/legacy_engine/viz/models.py` — 4 prep dataclasses (`HeatmapModel`, `BarModel`,
  `TierModel`, `TrendModel`) + 4 prep functions (`_heatmap_model`, `_metashare_model`, `_tier_model`,
  `_trends_model`) + threshold constants (`TIER_S_MIN/A_MIN/B_MIN`). Lifted verbatim from `charts.py`
  (already matplotlib-free); only the import block was changed (from `analytics.metashare._is_never_other`
  import path, unchanged; imports from `analytics.matchup` / `analytics.trends` unchanged).

- **Created** `src/legacy_engine/viz/specs.py` — 4 Vega-Lite v6 spec builders:
  - `spec_metashare(BarModel)`: horizontal bar, opacity condition on `muted`, color condition on `fringe`, tooltip
  - `spec_matchup_heatmap(HeatmapModel)`: rect+text 2-layer; redyellowgreen scale domain [0,0.5,1]; masked/mirror cells → grey (`#9AA0A6`); mirror annotated
  - `spec_tier_list(TierModel)`: faceted by bucket row (S/A/B); x=share, y=archetype; bucket-colored bars; empty model falls back to stub spec
  - `spec_trends(TrendModel)`: line+point; ordinal x (chronological sort); None cells omitted (gap); rect band layer for thin regimes; no band layer when no thin regimes

- **Updated** `src/legacy_engine/analytics/__init__.py` — removed the `charts` import block and 8 names
  from `__all__` (`BarModel`, `HeatmapModel`, `TierModel`, `TrendModel`, `render_*` ×4).

- **Updated** `src/legacy_engine/cli.py` — removed `--chart-dir` option from all 4 report commands
  (`meta`, `matchups`, `trends`, `tiers`); removed the `_chart_filename` helper; removed all
  `if chart_dir:` blocks; repointed `_print_tier_list`'s local import from `analytics.charts.TierModel`
  → `viz.models.TierModel`; `report_tiers` now imports `_tier_model` from `viz.models`.

- **Updated** `src/legacy_engine/viz/__init__.py` — added all 4 spec builders + 4 prep models/fns to
  re-export surface.

- **Deleted** `src/legacy_engine/analytics/charts.py` (594 LoC; matplotlib `render_*` functions removed;
  prep layer moved to `viz/models.py`).

- **Updated** `pyproject.toml` — removed `"matplotlib>=3.8"` from dependencies.

- **Deleted** `tests/test_charts.py` (matplotlib-era smoke renders + `--chart-dir` CLI tests, all obsolete).

- **Created** `tests/test_viz_specs.py` — 61 tests:
  - Prep-model tests re-pointed from `analytics.charts` → `viz.models` (all passing, byte-identical logic)
  - Per-builder: `test_schema_present`, `test_description_non_empty`, `test_no_config_key`,
    `test_assert_renders` (real Vega-Lite compiler via vl_convert), `test_json_snapshot`,
    plus surface-specific assertions (masking, mirror, fringe, gaps, thin bands, faceting)

### Final test count
- **1089 passing** (full suite; was 1076 before this feature; delta +13 = 61 new tests − 48 deleted
  matplotlib smoke tests and chart-dir CLI tests from test_charts.py).

### Confirmation: matplotlib gone
- `rg "import matplotlib" src/ tests/` → empty (exit 1)
- `rg "analytics\.charts" src/ tests/` → empty (exit 1)
- `rg "chart_dir|_chart_filename|--chart-dir" src/ tests/` → empty (exit 1)
- `"matplotlib>=3.8"` removed from `pyproject.toml`

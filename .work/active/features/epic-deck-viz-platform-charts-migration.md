---
id: epic-deck-viz-platform-charts-migration
kind: feature
stage: drafting
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
- **Visual tone = dark + minimal** (the maintainer, `--only-questions`; see the foundation feature for the
  theme details). All four migrated charts must read correctly on the dark theme — same palette/axis
  adjustments (light text/axes, swapped categorical-black).
- (No other open forks: prep-model location — `viz/models.py` per the brief — and the tier-list
  Vega-Lite representation — faceted text vs three stacked bars — are feature-design judgment calls
  consistent with the dark-minimal tone.)

## Research briefs
- [docs/briefs/deck-viz-platform.md](../../../docs/briefs/deck-viz-platform.md) — §5 (the charts.py
  migration map: surface → prep model → new builder → Vega-Lite mark), §4 (Tile A/C contracts these
  builders also serve).

## Foundation references
- `docs/ARCHITECTURE.md` — `viz/` module section; the `charts.py` "being superseded" note + the
  drop-matplotlib dependency note.
- `src/legacy_engine/analytics/charts.py` — the 594-LoC migration source (prep/render split).

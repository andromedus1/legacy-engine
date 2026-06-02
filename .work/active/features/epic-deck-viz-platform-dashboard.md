---
id: epic-deck-viz-platform-dashboard
kind: feature
stage: drafting
tags: [viz]
parent: epic-deck-viz-platform
depends_on: [epic-deck-viz-platform-foundation, epic-deck-viz-platform-charts-migration]
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Per-Deck Dashboard + viz CLI

## Brief
The headline deliverable: a reusable per-deck dashboard composing five tiles into one self-contained
HTML page, plus the `viz` CLI group. Delivers `viz/layout.py` (the `Tile` + `Dashboard` 12-col model and
the self-contained HTML template — a CSS `grid-template-columns: repeat(12, 1fr)` page embedding chart
tiles via a `vega-embed` snippet and HTML tiles directly) and `viz/deck_dashboard.py`
(`build_deck_dashboard(con, archetype, window)` composing the five tiles), plus the three net-new tile
builders not produced by charts-migration:
- **Tile B — matchup spread**: the subject deck's ROW from `matchup.build_adaptive_matrix` rendered as a
  horizontal win% bar (per opponent) with CI error bars (`rule` layer), a 0.5 reference, grey
  "insufficient" for `display==False`, and the adaptive `cell_windows` date in the tooltip.
- **Tile D — positioning**: `advisory/positioning.rank_decks` as a horizontal `s_quantile` bar
  highlighting the subject deck, CI error bars, `p_best` annotation, `low_coverage` faded; best-deck
  lens (`u_bar`) overlaid; `field_source` + `data_coverage` shown.
- **Tile E — consensus list**: `generation/consensus.build_consensus` rendered as an HTML card-list tile
  (60+15, grouped, each card shaded by `card_frequencies` `inclusion_pct`), with `sample_n`, `window`,
  and any `legality_errors`. ("Primer" = the composed page itself; an optional prose tile is enough for
  v1 — there is no primer function.)

Tiles A (meta-share) and C (trends) REUSE `spec_metashare` / `spec_trends` from charts-migration. Also
delivers the `viz` CLI group: `viz deck <archetype> --out file.html|<dir>` plus the migrated
`viz meta|matchups|trends|tiers` leaves (the `--out` extension drives the renderer: `.html` → template /
`render_html_tile`, `.png` → `render_png`; `viz deck --out <dir>` writes one PNG per tile). The existing
`report --chart-dir` matplotlib hook is removed (rendering centralizes under `viz`).

## Epic context
- Parent epic: `epic-deck-viz-platform`
- Position in epic: **terminal feature** — depends on foundation (render/theme/layout plumbing) and
  charts-migration (reuses `spec_metashare`/`spec_trends`). Largest feature in the epic; if it grows past
  a comfortable single pass, `/feature-design` may spawn child stories (e.g. split the CLI group from the
  dashboard composer).

## Inherited design decisions
- **Whole-dashboard PNG is OUT of scope** (would need a browser). The dashboard is HTML; PNG export is
  **per-tile** (Brief §2.1, §7).
- **Dashboard HTML loads the vega-embed CDN triple by default** (`vega@6`/`vega-lite@6`/`vega-embed@7`,
  matching vl-convert's bundled JS); an `--offline` flag inlines `vlc.javascript_bundle()` once for a
  fully self-contained page. Single-tile `viz <chart> --out x.html` is self-contained by default
  (`vegalite_to_html(bundle=True)`). *(Resolved this session — reversible; flag for override.)*
- **`report --chart-dir` is removed**; all rendering centralizes under the `viz` group (no `--html/--png`
  forwarding on `report` for v1). *(Resolved this session — reversible; flag for override.)*
- Per-deck matchup tile uses the **adaptive per-cell matrix** (`build_adaptive_matrix`), never a uniform
  window (regime-aware-advisory lesson).
- Confidence/labels carry through every tile; `data_coverage`/thin/masked surfaced honestly.
- Patterns: `cli-nested-groups` (`@main.group() viz`, `_setup_logging` first, lazy imports, `_window_opts`
  + `_verbose`, `_not_implemented` stubs); `constants-only-config`; dataclass result types.

## Design decisions
(All from Andrew, `--only-questions`.)
- **Layout = attack-focused**: matchup-spread **wide** across the top, positioning **prominent**,
  meta-share + trends secondary, consensus full-width at the bottom. (Leads with the "how to attack the
  field" surfaces — the engine's advisory differentiator.)
- **Visual tone = dark + minimal** (see the foundation feature for theme details).
- **Consensus tile (E) = two-column**: maindeck on the left, sideboard on the right, each card row
  shaded by `card_frequencies` `inclusion_pct` (lock = solid, flex = faint).
- **Primer = auto-generated summary tile — IN scope for v1.** Derive a few sentences from data the other
  tiles already pull: meta rank/share (`metashare`), best/worst matchups (the deck's adaptive-matrix
  row), and the positioning verdict (`rank_decks` rank + S). Confidence-gated/labelled like every other
  surface; **degrade gracefully on thin data — never fabricate** a read. Adds a summary/primer unit to
  `deck_dashboard.py`. (This supersedes the brief's "no primer fn / optional prose" note — §4 Tile E.)

## Research briefs
- [docs/briefs/deck-viz-platform.md](../../../docs/briefs/deck-viz-platform.md) — §4 (per-tile data
  contracts: source fns + return shapes + Vega-Lite marks for all 5 tiles), §3.5 (layout/Tile model),
  §6 (CLI surface), §7 (dashboard-PNG constraint, vega-embed version triple, offline-vs-CDN).

## Foundation references
- `docs/ARCHITECTURE.md` — `viz/` module section (`layout.py`, `deck_dashboard.py`); CLI line `viz (deck)`.
- `docs/SPEC.md` — the `DeckDashboard` entity + the Visualization & Reporting capability block.
- Tile sources: `analytics/matchup.py` (`build_adaptive_matrix`), `advisory/positioning.py`
  (`rank_decks`), `generation/consensus.py` (`build_consensus`, `card_frequencies`).

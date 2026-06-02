---
id: epic-deck-viz-platform-dashboard
kind: feature
stage: implementing
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
(All from the maintainer, `--only-questions`.)
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

## Architectural choice
Three new modules + a CLI group, building on the shipped foundation (`theme`, `render_png`,
`render_html_tile`, `strip_and_inject`) and migration (`viz/specs.py` `spec_metashare`/`spec_trends`,
`viz/models.py` prep fns):
- **`viz/specs.py` (extend)** — add the two net-new per-deck CHART builders: `spec_matchup_row` (Tile B)
  and `spec_positioning` (Tile D). Keeps all Vega-Lite builders in one module.
- **`viz/layout.py`** — `Tile`/`Dashboard` dataclasses + `render_dashboard_html` (12-col CSS grid;
  chart tiles via a `vegaEmbed` snippet with the theme-injected spec inlined as JSON; html tiles inline;
  CDN triple from `config`, or fully inlined when `offline=True`).
- **`viz/deck_dashboard.py`** — `build_deck_dashboard` composes the five tiles for one archetype +
  the auto-generated primer; plus `_consensus_html` (Tile E, two-column) and `_primer_summary` (text).
- **`cli.py`** — the `viz` group: `viz deck` + migrated `viz meta|matchups|trends|tiers`.
Considered folding per-deck builders into a separate `viz/tiles.py` — rejected, one builder module
(`specs.py`) is simpler and they share helpers. Considered expressing the dashboard as one Vega-Lite
`vconcat` spec — rejected (the consensus + primer tiles are HTML, not charts; §2.1 of the brief).

## Implementation Units

### Unit 1: per-deck chart builders (extend viz/specs.py)
**File**: `src/legacy_engine/viz/specs.py`
```python
def spec_matchup_row(rows: list[dict], *, deck: str) -> dict: ...
# Tile B. rows = per-opponent dicts {opponent, p_shrunk, ci_low, ci_high, n, tier, display, window}.
# horizontal bar of p_shrunk per opponent (sorted), layered: bar + CI `rule` (ci_low..ci_high) +
# a reference `rule` at 0.5; masked (display False / p_shrunk None) → grey "n=X insufficient", no rate;
# tooltip: p_raw%, n, tier, window (the adaptive cell window). description names the deck.
def spec_positioning(ranking, *, subject: str, u_bar: float | None = None) -> dict: ...
# Tile D. DeckRanking → horizontal bar of s_quantile per candidate (sorted best→worst),
# subject deck highlighted (color condition), CI `rule` from s_ci, p_best in tooltip,
# low_coverage decks faded (opacity), optional u_bar overlay `rule` (best-deck lens).
```
**Implementation Notes**: hand-built dicts; `$schema` + non-empty `description`; no `config`. Reuse the
masking idiom from `spec_matchup_heatmap`. For positioning, the subject highlight uses a Vega-Lite
`condition` on `datum.deck == <subject>`.
**Acceptance Criteria**:
- [ ] `assert_renders(spec_matchup_row(rows, deck=...))` and `assert_renders(spec_positioning(r, subject=...))` pass (real compiler).
- [ ] Matchup-row masks `display==False` cells (grey, no rate); reference rule at 0.5 present.
- [ ] Positioning highlights the subject and fades `low_coverage` decks; CI rules present.
- [ ] JSON snapshot per builder.

### Unit 2: viz/layout.py — Tile/Dashboard + HTML template
**File**: `src/legacy_engine/viz/layout.py`
```python
from dataclasses import dataclass, field

@dataclass
class Tile:
    kind: str            # "chart" | "html"
    title: str
    col_span: int        # 1..12
    spec: dict | None = None
    html: str | None = None

@dataclass
class Dashboard:
    title: str
    tiles: list[Tile]

def render_dashboard_html(dash: Dashboard, *, offline: bool = False) -> str: ...
# Self-contained HTML page. <head>: dark page CSS + grid (grid-template-columns: repeat(12,1fr)) +
# either 3 CDN <script> (config.VIZ_CDN_VEGA/VEGA_LITE/VEGA_EMBED) or, if offline, one inlined
# vl_convert.javascript_bundle(). Each chart Tile -> <div style="grid-column: span N"> + a vegaEmbed(el,
# strip_and_inject(spec, variant="screen"), {actions:false, renderer:"svg"}) call with the spec inlined
# as JSON. Each html Tile -> its html in a spanned div. Dark page background matches the theme.
```
**Implementation Notes**: theme-inject each chart spec via `strip_and_inject(..., variant="screen")`
before inlining (so HTML matches PNG). `offline=True` → call `vl_convert.javascript_bundle()` once and
inline it instead of the CDN scripts. Page bg = theme `_BG` (dark).
**Acceptance Criteria**:
- [ ] `render_dashboard_html(d)` returns one `<!DOCTYPE html>` doc containing a 12-col grid and one
  `vegaEmbed(` call per chart tile + each html tile's markup.
- [ ] CDN mode references the three config CDN URLs; `offline=True` inlines the bundle and references no CDN.
- [ ] Chart specs are theme-injected (no raw `config` leaks; dark page bg).

### Unit 3: viz/deck_dashboard.py — the composer
**File**: `src/legacy_engine/viz/deck_dashboard.py`
```python
def build_deck_dashboard(con, archetype: str, *, provenance: str | None = None,
                         regime: str = "current", seed: int | None = 0) -> Dashboard: ...
```
Assembly (adaptive default, mirrors the advisory layer):
- `adaptive = build_adaptive_matrix(con, provenance=provenance)`; `cur_since, cur_until = resolve_regime(regime)`
- `field = build_global_field(con, since=cur_since, until=cur_until, provenance=provenance)`
- `candidates = sorted(field.shares)`; `ranking = rank_decks(adaptive.matrix, field, candidates, risk_averse=True, seed=seed)`
- `subj = positioning_score(adaptive.matrix, field, archetype, seed=seed)` (for `u_bar`/`data_coverage`)
- `meta = compute_metashare(con, since=cur_since, until=cur_until, provenance=provenance)` → `spec_metashare(_metashare_model(meta))` (Tile A)
- matchup ROW: for each `opp in adaptive.matrix.archetypes`, pull `adaptive.matrix.cells[(archetype,opp)]` + `adaptive.cell_windows.get((archetype,opp))` → `spec_matchup_row(rows, deck=archetype)` (Tile B)
- `trends = compute_trends(con)` → `spec_trends(_trends_model(trends))` (Tile C)
- `spec_positioning(ranking, subject=archetype, u_bar=subj.u_bar)` (Tile D)
- `cons = build_consensus(con, archetype, since=cur_since, until=cur_until)`; `mf = card_frequencies(con, archetype, board="main", since=cur_since, until=cur_until)`; `sf = card_frequencies(..., board="side", ...)` → `_consensus_html(cons, mf, sf)` (Tile E)
- `_primer_summary(archetype, meta, rows, ranking, subj)` → primer html tile

**Attack-focused layout order** (per the maintainer): primer/header → matchup-row (col_span 12, wide top) →
positioning (col_span 6) + meta-share (col_span 6) → trends (col_span 12) → consensus (col_span 12, bottom).

Helpers:
```python
def _consensus_html(deck, main_freqs, side_freqs) -> str: ...
# two-column: maindeck (left) | sideboard (right); each row "n  CardName" shaded by inclusion_pct
# (lock solid → flex faint via inline background-opacity). Show sample_n, window, legality_errors.
def _primer_summary(archetype, meta, matchup_rows, ranking, subj) -> str: ...
# a few sentences from data already pulled: meta rank/share, best & worst non-masked matchups,
# positioning rank (index in ranking.decks) + S(s_mean) + data_coverage caveat. DEGRADE on thin data:
# if no established matchups → say "insufficient matchup data", never fabricate; if archetype absent
# from meta/field → say so. Confidence/labels carried.
```
**Acceptance Criteria**:
- [ ] Returns a `Dashboard` with the five tiles + primer, in attack-focused order with the col_spans above.
- [ ] Matchup-row tile uses the adaptive per-cell windows (Tile B rows carry `window`).
- [ ] `_primer_summary` degrades gracefully (no fabricated reads) when the archetype has thin/no data —
  covered by a thin-fixture test.
- [ ] `_consensus_html` renders two columns shaded by inclusion_pct, with sample_n + window.

### Unit 4: cli.py — the `viz` group
**File**: `src/legacy_engine/cli.py`
```python
@main.group()
def viz() -> None: ...
@viz.command("deck")  @click.argument("archetype")  @click.option("--out", required=True) @_window_opts @_verbose
def viz_deck(...): ...   # build_deck_dashboard -> .html: render_dashboard_html; <dir>: one render_png per chart tile
@viz.command("meta"|"matchups"|"trends"|"tiers")  @click.option("--out", required=True) @_window_opts @_verbose
def viz_*(...): ...      # build record -> prep model -> spec_* ; --out .html -> render_html_tile, .png -> render_png
```
**Implementation Notes**: `_setup_logging(verbose)` first; lazy imports; reuse `_window_opts`/`_verbose`;
`--out` extension drives the renderer; `viz deck --out <dir>` writes one PNG per chart tile (whole-page
PNG is out of scope). Add `--offline` to `viz deck` (forwards to `render_dashboard_html(offline=True)`).
Wrap `vl_convert` `ValueError` as `click.ClickException`. `mkdir(parents=True)` at write time.
**Acceptance Criteria**:
- [ ] `viz deck <arch> --out x.html` writes a dashboard HTML; `--out <dir>` writes per-tile PNGs.
- [ ] `viz meta|matchups|trends|tiers --out x.html|.png` writes the respective artifact.
- [ ] A spec that fails to render surfaces a `click.ClickException`, not a raw traceback.

### Unit 5: tests
**Files**: `tests/test_viz_tiles.py` (spec_matchup_row, spec_positioning — snapshot + assert_renders +
masking/highlight), `tests/test_viz_layout.py` (render_dashboard_html — grid, vegaEmbed-per-chart-tile,
html tiles, CDN vs offline), `tests/test_viz_deck_dashboard.py` (build_deck_dashboard on the
rounds-bearing fixture DB → 5 tiles + primer, attack-order col_spans, primer thin-data degradation,
two-column consensus), and `viz`-group tests in `tests/test_cli.py` (viz deck/meta → writes html + png;
--out ext routing; ClickException on bad spec). Reuse the rounds-bearing DB fixtures + `assert_renders`.
**Acceptance Criteria**:
- [ ] Full suite green; new tests cover each builder, layout, composer (incl. thin-data), and CLI routing.

## Implementation Order
1. **Unit 1** (per-deck builders) — leaf, reuses shipped render/theme.
2. **Unit 2** (layout) — independent of Unit 1; needed by the composer.
3. **Unit 3** (deck_dashboard composer) — depends on Units 1+2 + analytics/advisory/generation sources.
4. **Unit 4** (viz CLI group) — depends on Unit 3 (deck) + migrated builders (meta/matchups/trends/tiers).
5. **Unit 5** (tests) — alongside each unit; full suite last.

## Testing
- **Unit**: builders (snapshot + `assert_renders` + masking/highlight); layout (grid/embeds/offline);
  `_consensus_html` two-column + shading; `_primer_summary` thin-data degradation (no fabrication).
- **Integration**: `build_deck_dashboard` end-to-end on the rounds-bearing fixture DB → 5 tiles + primer;
  `viz` CLI commands write real html/png files; `--out` extension routing; ClickException on bad spec.
- **Test data**: reuse the rounds-bearing DB fixtures (as test_charts.py/test_card_winrates did);
  `assert_renders` from conftest.

## Risks
- **Largest feature in the epic** (~5 units, builders + layout + composer + CLI). — **Fallback**: if a
  single implementation pass overflows, split into a story for Units 1+2 (builders + layout) and a story
  for Units 3+4 (composer + CLI, depends on the first); the design is already unit-partitioned for that.
- **Primer fabrication risk** — the auto-summary must NOT invent reads on thin data. — **Fallback**:
  `_primer_summary` gates every sentence on established/evolving tier + presence in meta/field; a
  dedicated thin-fixture test asserts it degrades to "insufficient data" rather than a number.
- **rank_decks cost** (Monte-Carlo over all candidates) inside the dashboard — **Fallback**: it's the
  same call the advisory CLI already makes; acceptable for a one-shot dashboard render. Seed for
  determinism in tests.

## Child stories
None for now — single-stride, one module family (`viz/` + the `viz` CLI group). Kept whole so the
composer, builders, layout, and CLI evolve together. The Risks section names the 2-story fallback split
if the implementing pass proves too large.

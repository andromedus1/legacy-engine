---
description: Read before designing/building the viz/ layer — how to adapt a Vega-Lite stack to legacy-engine; the dependency decisions (vl-convert-python, hand-built dicts), per-tile data contracts, charts.py migration map, and CLI surface.
type: brief
kind: research
research_method: /brief
updated: 2026-06-01
status: draft
summary: |
  Integration brief that unblocks epic-deck-viz-platform. Harvests ds-engine's locked viz research
  (Vega-Lite + vl-convert + strip-and-inject theming + 12-col tiles) and resolves the four
  legacy-engine-specific questions: vl-convert-python is the single render dependency (it does BOTH
  static PNG and self-contained HTML); specs are authored as hand-built Python dicts (not Altair);
  the five dashboard tiles bind to named analytics/advisory/generation functions whose shapes are
  documented here; and charts.py migrates by keeping its pure `_*_model` prep layer and swapping the
  matplotlib renderers for Vega-Lite spec builders.
key_findings:
  - "vl-convert-python (1.9.x, zero-dependency abi3 wheel, macOS-arm64 + linux wheels) is the SINGLE render dependency: vegalite_to_png(spec, scale=) for static PNG AND vegalite_to_html(spec, bundle=True) for self-contained interactive HTML. No Chrome, no Node, no browser. PNG is deterministic same-machine."
  - "Author specs as hand-built Vega-Lite v6 dicts, NOT Altair. Small fixed chart vocabulary (~5 marks), we already depend on vl-convert (which takes dicts), tight theme control, trivial JSON snapshot tests. Altair would add jinja2+jsonschema+narwhals for no benefit."
  - "We author every spec ourselves, so ds-engine's runtime AJV validator + correction-loop are NOT needed. Validation is a TEST-TIME concern (jsonschema.validate against the VL v6 schema + JSON snapshot fixtures). This trims the epic's 'structural validator' scope substantially."
  - "Strip-and-inject is still mandatory (vega-embed #27): strip top-level spec.config, then bake the canonical theme dict into spec.config before BOTH render paths so HTML and PNG match. Two theme variants (screen vs print) sharing palette/fonts."
  - "charts.py already splits pure honesty-logic prep (_heatmap_model/_metashare_model/_tier_model/_trends_model — matplotlib-free dataclasses) from matplotlib render_* . Migration KEEPS the prep models, writes spec_from_*(model) Vega-Lite builders, and drops the matplotlib renderers + the matplotlib dependency."
  - "Per-deck dashboard tiles bind to: metashare.compute_metashare→MetaShareReport; matchup.build_adaptive_matrix→AdaptiveMatrix (the deck's ROW as a win% bar, not the full NxN); trends.compute_trends→TrendSeries; positioning.rank_decks→DeckRanking (highlight subject deck); generation/consensus.build_consensus→GeneratedDeck (HTML card-list tile, not a chart). No 'primer' function exists — the composed page IS the primer."
---

# Brief: Adapting a Vega-Lite Visualization Stack to legacy-engine

## Purpose
Unblocks `epic-deck-viz-platform` (`.work/active/epics/epic-deck-viz-platform.md`, tagged `[needs-brief]`)
for `/epic-design`. The landscape ("which spec format / renderer / theming model") is **already settled**
by ds-engine's locked research — harvested in §1, cited, not re-litigated. This brief resolves the four
**legacy-engine-specific** integration questions: the render dependency (§2), the authoring path (§2),
the `viz/` module shape (§3), the per-tile data contracts (§4), the `charts.py` migration map (§5), and
the CLI surface (§6). It is builder-facing and concrete.

---

## 1. Settled decisions (harvested from ds-engine, do not redo)

| Decision | One-line rationale | ds-engine source |
|---|---|---|
| **Vega-Lite is the spec format** | Only format with the LLM/pretraining coverage + a JSON schema; beats ECharts/Plotly on the axis that matters | `adhoc-viz-rendering/parent.md` |
| **vl-convert for static raster, not kaleido** | Self-contained Rust+Deno+resvg, no Chrome; 100-400ms vs kaleido's 2-3s; renders Vega-Lite directly | `rendering-pipeline-server-vs-client.md` |
| **Strip-and-inject theming is mandatory** | vega-embed #27: a spec-internal `config:` BEATS an embed-level `config:`; passive injection silently loses the theme | `theming-accessibility-design-system.md` |
| **Two theme variants** | Screen (transparent/lighter) vs print/PNG (white bg, larger fonts); share palette + fonts, differ only in bg + sizing | `theming-accessibility-design-system.md` |
| **Colorblind-safe categorical palette** | Okabe-Ito 8-color, not tableau10 (fails WCAG 3:1 at small marks) | `theming-accessibility-design-system.md` |
| **Required `description` on every spec** | Populates the SVG `aria-label`; only universally-required field beyond `$schema` | `theming-accessibility-design-system.md` |
| **12-column tile/layout grid** | Industry-standard grid; tiles placed `{row, col, col_span, row_span}` | `src/output/dashboard-layout/types.ts` |

**Two things ds-engine needs that legacy-engine does NOT** (because ds-engine's specs are authored at
runtime by an LLM agent, ours are authored by us in code):
- **A runtime AJV validator + correction loop.** ds-engine retries malformed agent specs 79%→~99%.
  We hand-build every dict from typed Python, so structural correctness is a *test-time* guarantee
  (see §3.4), not a runtime loop. **Drop it from scope.**
- **A curated 215-line Vega-Lite sub-schema for validation.** Same reason — we validate our own emitted
  dicts against the *real* VL v6 schema in tests; no need to hand-maintain a permissive sub-schema.

---

## 2. Dependency decisions

### 2.1 Render dependency — `vl-convert-python` (the only new runtime dep)
**Confirmed (2026):** `vl-convert-python` 1.9.0.post1 (stable; 2.0.0rc1 exists, stay on 1.9.x). It is a
**zero-dependency** `cp37-abi3` wheel wrapping a Rust crate that embeds Deno/V8 + bundled Vega JS +
`resvg`. Pre-built wheels exist for **macOS arm64** (our dev box), macOS x86_64, manylinux x86_64/aarch64,
win_amd64 — `pip install vl-convert-python` needs no compiler, no Chrome, no Node.

**The key finding: it does BOTH output paths we need.** One dependency covers the epic's "interactive
HTML + static PNG" requirement:

```python
import vl_convert as vlc

# Static PNG (offline, no browser):
png_bytes: bytes = vlc.vegalite_to_png(spec_dict, scale=2.0, vl_version="6.4")

# Self-contained interactive HTML for a SINGLE chart (vega-embed inlined, fully offline):
html: str = vlc.vegalite_to_html(spec_dict, bundle=True)   # bundle=True ≈ 878KB, no CDN, works offline
# bundle=False ≈ 1KB, loads vega/vega-lite/vega-embed from CDN (needs internet at view time)
```

- **Accepts `str | dict`** for the spec; we pass dicts directly (no `json.dumps` needed, unlike
  ds-engine's subprocess bridge which serialized first).
- **Theme**: `vegalite_to_png(..., config=theme_dict, theme="latimes")` params exist, but for
  HTML/PNG parity we **bake the theme into `spec["config"]`** (see §3.2) and rely on that, mirroring
  ds-engine's actual implementation choice.
- **Fonts**: bundles Liberation Sans as fallback; otherwise uses host system fonts via resvg. Keep the
  theme font stack generic and ending in `system-ui, sans-serif` so PNGs render consistently without
  shipping fonts. `vlc.register_font_directory("/abs/path")` is available if a brand font is wanted later.
- **VL version**: pin `vl_version="6.4"` (bundled set: 5.8–6.4; default is latest). Our specs declare
  `"$schema": "https://vega.github.io/schema/vega-lite/v6.json"`.
- **Determinism**: byte-identical PNG across repeated runs same-machine (verified). Cross-platform
  text-layout floats *could* differ by a hair; not a practical issue for our use.
- **Failure mode**: invalid spec → `ValueError` with the verbatim Vega-Lite error text (descriptive, no
  silent failure). Wrap leaf CLI calls so a bad spec surfaces as a `click.ClickException`.

**Dashboard composition note (important constraint).** `vegalite_to_html`/`vegalite_to_png` render a
*single* spec. The per-deck dashboard is a **multi-tile page mixing charts AND non-chart content** (the
consensus 60+15 card list, primer prose) — that is NOT expressible as one Vega-Lite spec. So:
- **Per-tile artifacts**: each chart tile → `render_png(spec)` and (optionally) a standalone
  `vegalite_to_html(spec, bundle=True)`.
- **The dashboard page** is **our own hand-built HTML template** (12-col CSS grid; mirrors the
  `/knowledge-graph` + kanban-`board` precedent), embedding each chart tile via a small `vega-embed`
  snippet (chart JSON inlined) and rendering the card-list/primer tiles as HTML.
- **A single PNG of the *whole* dashboard is out of scope** (would need a browser screenshot — which we
  are explicitly avoiding). PNG export is **per-tile**; that is what feeds primers / Moxfield / sharing.
  Surface this honestly in the design; don't imply a one-shot dashboard PNG.

### 2.2 Authoring path — hand-built Vega-Lite dicts, NOT Altair
**Decision: hand-built dicts.** Altair 6.1 is reasonable but adds `jinja2 + jsonschema + narwhals +
packaging` for no benefit here, because:
1. The vocabulary is small and fixed (~5 marks: bar, grouped/normalized bar, rect/heatmap, line,
   text/table). ~6 builder functions, written once.
2. We already depend on vl-convert, which consumes dicts directly — Altair would just produce the same
   dict we can write ourselves.
3. Tight theme control: inject `spec["config"] = theme` at construction time; no `alt.theme.register`
   global state.
4. Testing is trivial JSON snapshots (assert builder output == fixture) — no Altair schemapi layer.
5. Matches ds-engine's *actual* choice (they hand-curate JSON despite the idea-file naming Altair).

Validate the emitted dicts against the **real** VL v6 schema with `jsonschema` **in the test suite only**
(dev dependency), plus snapshot fixtures. No runtime validation path.

### 2.3 Net dependency change
- **Add (runtime):** `vl-convert-python>=1.9,<2`.
- **Add (dev/test):** `jsonschema` (schema-validate emitted specs in tests).
- **Remove (eventually):** `matplotlib` — once all four `charts.py` surfaces migrate (§5). Stage the
  removal as the final migration unit so tests stay green throughout.

---

## 3. The `viz/` module (design grounding for /epic-design)

Follows ARCHITECTURE.md's committed map: `viz/` = `spec.py` + `theme.py`(within spec) + `layout.py` +
`render.py` + `deck_dashboard.py`. Suggested concrete shape:

```
src/legacy_engine/viz/
  __init__.py
  theme.py        # canonical theme dicts (screen + print variants) + strip_and_inject()
  specs.py        # hand-built Vega-Lite dict builders, one per chart kind (consumes charts.py prep models)
  layout.py       # Tile + Grid model (12-col) + dashboard HTML template renderer
  render.py       # render_png(spec)->bytes ; render_html_tile(spec)->str (both via vl_convert)
  deck_dashboard.py  # build_deck_dashboard(con, archetype, window) -> composes the 5 tiles into one page
```

### 3.1 Conventions to follow (non-negotiable)
- **Result types are `@dataclass`** (matches the analytics/advisory convention — `MetaShareReport`,
  `MatchupMatrix`, etc. are dataclasses, NOT `LegacyEngineModel`). Tile/spec records follow suit.
  `LegacyEngineModel` (Pydantic) is only for external-data models. → `pydantic-base-model` pattern.
- **All viz constants in `config.py`** (no I/O on import): `VIZ_DIR = DATA_DIR / "viz"`, CDN URLs for
  the dashboard template (`vega@6`, `vega-lite@6`, `vega-embed@7` — matching vl-convert's bundled
  versions), `VIZ_PNG_SCALE = 2.0`, palette constants. `mkdir` happens at write time in `render.py`.
  → `constants-only-config` pattern.
- **Confidence carries through.** Every tile encodes the same honesty the text reports do: masked
  (`display=False` / `n==0`) cells are greyed and labelled "n=X, insufficient" never a rate; speculative
  tier muted; fringe hatched/Other; thin regimes banded; `data_coverage` surfaced. No unlabelled number.
  → `confidence-metadata` pattern.

### 3.2 Strip-and-inject (port of ds-engine's 2-function algorithm)
```python
def strip_and_inject(spec: dict, *, variant: str = "screen") -> dict:
    out = copy.deepcopy(spec)          # never mutate caller's dict
    out.pop("config", None)            # Layer-1 strip: top-level config only (vega-embed #27)
    out["config"] = THEME[variant]     # inject canonical theme; spec.config now wins everywhere
    return out
```
Call it once at render time, in BOTH `render_png` and the dashboard tile-embed path, so HTML and PNG are
identical. `variant="screen"` for HTML, `variant="print"` for PNG.

### 3.3 Theme dict (concrete fields to mirror — port ds-engine's VegaConfig shape)
```python
_SHARED = dict(
    font="'Helvetica Neue', Arial, system-ui, sans-serif",
    title=dict(fontWeight=600, color="#111827"),
    axis=dict(labelColor="#6B7280", titleColor="#374151",
              tickColor="#E5E7EB", domainColor="#E5E7EB", gridColor="#F3F4F6"),
    legend=dict(labelColor="#374151"),
    range=dict(
        category=["#E69F00","#56B4E9","#009E73","#F0E442",      # Okabe-Ito (colorblind-safe)
                  "#0072B2","#D55E00","#CC79A7","#000000"],
        diverging="redyellowgreen",  # win-rate heatmap: red=bad→green=good (MTG-conventional)
    ),
)
THEME = {
  "screen": {**_SHARED, "background": "transparent",
             "title": {**_SHARED["title"], "fontSize": 15}, "axis": {**_SHARED["axis"], "labelFontSize": 12}},
  "print":  {**_SHARED, "background": "#FFFFFF",
             "title": {**_SHARED["title"], "fontSize": 18}, "axis": {**_SHARED["axis"], "labelFontSize": 14}},
}
```
*Caveat to record:* `redyellowgreen` is the domain-conventional win-rate scale but is not fully
colorblind-safe. Keep it for the heatmap (red/green = bad/good is the MTG idiom and the tooltip carries
the number), but use Okabe-Ito for all *categorical* (archetype) encodings.

### 3.4 Validation = test-time only
- A pytest that imports each builder, builds a spec from a fixture model, and runs
  `jsonschema.validate(spec, VL_V6_SCHEMA)`.
- JSON snapshot fixtures per builder (assert dict == fixture) so spec drift is caught in review.
- A pytest that round-trips one spec through `vlc.vegalite_to_png` and asserts non-empty PNG bytes
  (smoke test the renderer integration). Mark it so CI without the wheel can skip if needed.

### 3.5 Layout / Tile model (minimal — do NOT copy ds-engine's dual-representation back-compat)
```python
@dataclass
class Tile:
    kind: str            # "chart" | "html"
    title: str
    col_span: int        # 1..12
    spec: dict | None = None   # Vega-Lite dict for kind=="chart"
    html: str | None = None    # raw HTML for kind=="html" (card list, primer prose)

@dataclass
class Dashboard:
    title: str
    tiles: list[Tile]    # laid out left-to-right, wrapping the 12-col grid by col_span
```
`layout.py` renders `Dashboard` → one self-contained HTML page: a CSS `grid-template-columns: repeat(12,
1fr)` container; each chart tile is a `<div style="grid-column: span N">` with a `vegaEmbed(...)` snippet
(theme-injected spec inlined as JSON); html tiles drop their HTML in directly. Three CDN `<script>` tags
(vega@6, vega-lite@6, vega-embed@7) in `<head>`; `actions:false`, `renderer:"svg"`.

---

## 4. Per-tile data contracts (the 5 dashboard tiles)

All shapes below are read from the actual source. A *per-deck* dashboard fixes one `archetype` and a
window (default = current ban-regime via `trends.resolve_regime("current")`, the adaptive default).

### Tile A — Meta-share (where the field is)
- **Source:** `analytics/metashare.compute_metashare(con, definition="raw", provenance=..., since=, until=) -> MetaShareReport`.
- **Shape:** `MetaShareReport{definition, provenance, entries:[MetaShareEntry{archetype, share, n, tier, fringe}], total_decks, unlabeled, min_share, excluded_no_match_data}`.
- **Spec:** horizontal **bar**; `y=archetype (nominal, sorted by share desc)`, `x=share (quantitative)`,
  `opacity` muted when `tier=="speculative"`, hatch/`color` grey for `fringe`/"Other", tooltip `n`+`tier`.
  Subtitle from `definition`+`provenance`+`total_decks` (the existing `BarModel.subtitle`).

### Tile B — Matchup spread (this deck vs the field) — uses the ADAPTIVE matrix
- **Source:** `analytics/matchup.build_adaptive_matrix(con, provenance=...) -> AdaptiveMatrix`.
  `AdaptiveMatrix{matrix:MatchupMatrix, valid_since:{arch:date|None}, cell_windows:{(a,b):date|None}}`.
- **For a per-deck dashboard, take the subject deck's ROW**: iterate `matrix.cells[(archetype, opp)]`
  for each `opp in matrix.archetypes`. `MatchupCell{wins, n, p_raw, p_shrunk, ci_low, ci_high, tier,
  is_mirror, display}`.
- **Spec:** horizontal **bar** of `p_shrunk` per opponent (sorted), with **error bars** from
  `ci_low/ci_high` (a `rule` layer), a reference rule at 0.5, grey+"insufficient" for `display==False`,
  tooltip `p_raw`, `n`, `tier`, and `cell_windows[(deck,opp)]` (the adaptive window — audit trail).
- *(The full N×N heatmap is the format-level chart migrated in §5, not the per-deck tile.)*

### Tile C — Trends across ban-regimes
- **Source:** `analytics/trends.compute_trends(con, definition="raw", provenance=...) -> TrendSeries`.
  `TrendSeries{definition, provenance, regimes:[RegimeWindow{label, since, until, opening_events, event_count, span_days, thin}], cells:{(regime_label,arch):TrendCell{archetype, share, n, tier}}, archetypes}`; `.trajectory(arch)->[TrendCell|None]` gives one deck's line.
- **Spec:** multi-line (or single-line for the subject deck highlighted among top-k). `x=regime.label
  (ordinal, chronological)`, `y=share`, `color=archetype`. **`None` cells are gaps** (do not plot 0).
  Shade x-band where `regime.thin`; tooltip `n`, `tier`, `opening_events`, `span_days`.

### Tile D — Positioning (best-call vs best-deck)
- **Source:** `advisory/positioning.rank_decks(matrix, field, candidates, risk_averse=True) -> DeckRanking`
  (candidates = the field archetypes from `metashare`). Optionally
  `positioning_score(matrix, field, archetype) -> PositioningResult` for the subject's
  `s_mean`/`u_bar`/`s_ci`/`data_coverage`.
- **Shape:** `DeckRanking{decks(sorted), p_best, s_mean, s_ci, s_quantile, quantile_level, data_coverage, low_coverage, pairwise, field_source}`.
- **Spec:** horizontal **bar** of `s_quantile` per candidate (sorted), **highlight the subject deck**,
  error bars from `s_ci`, annotate `p_best`; fade/flag decks in `low_coverage`. Best-call = field-weighted
  `s_mean`; best-deck lens = `PositioningResult.u_bar` (overlay marker or a second small bar). Always show
  `field_source` + `data_coverage` (a low-coverage deck's S is prior-dominated — say so).

### Tile E — Consensus list + primer (HTML tile, not a chart)
- **Source:** `generation/consensus.build_consensus(con, archetype, since=, until=) -> GeneratedDeck`
  (`{archetype, maindeck:{name:count→60}, sideboard:{name:count≤15}, window, sample_n, legality_errors}`)
  and `card_frequencies(con, archetype, board="main"|"side") -> [CardFreq{name, inclusion_pct, modal_count, decks_running}]` for the flex/lock shading.
- **Render as an HTML table tile** (kind="html"): the 60+15 list grouped by type/count, each card shaded
  by `inclusion_pct` (lock = high %, flex = low %). Show `sample_n`, `window`, and any `legality_errors`.
- **"Primer":** *there is no primer function in the source* (`grep primer src/` → 0 hits). The composed
  dashboard page IS the primer in intent. For v1, an optional free-text/markdown prose tile is enough;
  a generated primer is a future item, not this epic.

---

## 5. charts.py migration map

`analytics/charts.py` (594 LoC) is already structured as **pure prep model → matplotlib renderer**. The
`_*_model` functions are matplotlib-free dataclasses that bake in *all* the honesty logic (masking,
fringe, thin-regime banding, caveat strings). **This is the migration win: keep the prep models, swap the
backend.**

| charts.py surface | Prep model (KEEP, move to viz/) | Old (DROP) | New viz builder | Vega-Lite mark |
|---|---|---|---|---|
| Matchup heatmap (format-level N×N) | `_heatmap_model -> HeatmapModel{archetypes, values, masked, mirror, annotations, caveat, title}` | `render_matchup_heatmap` (matplotlib) | `spec_matchup_heatmap(HeatmapModel)` | `rect` + `text` layer; `color` = `redyellowgreen` over `values`, grey for `masked` |
| Meta-share bars | `_metashare_model -> BarModel{labels, shares, muted, fringe, tiers, subtitle, title}` | `render_metashare` | `spec_metashare(BarModel)` | horizontal `bar`; `opacity` from `muted`, hatch from `fringe` |
| Tier list (S/A/B) | `_tier_model -> TierModel{buckets:{S,A,B:[(arch,share,tier)]}, subtitle, title}` | `render_tier_list` | `spec_tier_list(TierModel)` | faceted/`text` columns or 3 stacked `bar` panels |
| Trends lines | `_trends_model -> TrendModel{regime_labels, archetypes, series:{arch:[share|None]}, thin_regimes, subtitle, title}` | `render_trends` | `spec_trends(TrendModel)` | `line` + `point`; gaps for `None`; `rect` band for `thin_regimes` |

**Plan:** (1) move the four `_*_model` prep fns + their model dataclasses into `viz/` (or a shared
`viz/models.py`); (2) write the four `spec_*` builders against those models; (3) repoint callers; (4)
delete the matplotlib `render_*` fns and drop the `matplotlib` dependency as the final unit (keeps tests
green throughout). The per-deck dashboard tiles (§4) reuse these builders where they overlap (metashare,
trends) and add the per-deck row-bar (Tile B) + positioning bar (Tile D) + consensus HTML (Tile E).

---

## 6. CLI surface

Follows `cli-nested-groups`: new `@main.group() viz`, leaves call `_setup_logging(verbose)` first, lazy
imports inside the body, `_window_opts` + `_verbose` decorators reused, unimplemented leaves use
`_not_implemented`.

```python
@main.group()
def viz() -> None:
    """Visualization — Vega-Lite dashboards (HTML) and chart export (PNG)."""

@viz.command("deck")            # the headline per-deck dashboard
@click.argument("archetype")
@click.option("--out", type=click.Path(dir_okay=False), required=True,
              help="Output path; .html (interactive dashboard) or .png (per-tile export dir if a dir).")
@_window_opts
@_verbose
def viz_deck(archetype, out, ..., verbose):
    _setup_logging(verbose)
    from legacy_engine.viz.deck_dashboard import build_deck_dashboard
    ...

# Per-tile / format-level commands (migrated charts.py surfaces):
@viz.command("meta")     -> spec_metashare      -> --out file.html|.png
@viz.command("matchups") -> spec_matchup_heatmap-> --out file.html|.png   (format-level N×N)
@viz.command("trends")   -> spec_trends         -> --out file.html|.png
@viz.command("tiers")    -> spec_tier_list      -> --out file.html|.png
```

- **`--out` extension drives the renderer**: `.html` → `render_html_tile`/dashboard template; `.png` →
  `render_png`. For `viz deck --out <dir>` (PNG), write one PNG per tile.
- **Replace `report --chart-dir`**: the existing `--chart-dir` matplotlib hook on `report meta|matchups|
  trends|tiers` is removed; those visualizations move to `viz`. (Optional nicety: add `--html/--png` to
  the `report` commands that forward to the `viz` builders — decide in epic-design; the clean default is
  to centralize all rendering under `viz`.)
- Keep `_chart_filename(kind, definition, provenance)` naming for PNG outputs.

---

## 7. Implementation notes, gotchas, open decisions for /epic-design

- **Decompose suggestion (feature seams):** (1) `viz/` foundation = `theme` + `strip_and_inject` +
  `render` (png/html) + test-time validation; (2) migrate the 4 `charts.py` surfaces (prep-model reuse,
  drop matplotlib); (3) the per-deck dashboard = `layout` + `deck_dashboard` composing the 5 tiles +
  Tiles B/D/E builders + `viz deck` CLI. Natural 3-feature epic; (1)→(2)→(3) dependency order.
- **Whole-dashboard PNG is out of scope** (no browser). PNG = per-tile. State it in the epic so nobody
  expects a one-shot dashboard image.
- **vega-embed version triple** for the dashboard template: vega@6 / vega-lite@6 / vega-embed@7 (matches
  vl-convert's bundled JS so HTML and PNG render identically). Pin in `config.py`.
- **Self-contained vs CDN HTML:** `vegalite_to_html(bundle=True)` is fully offline (~878KB/chart). For
  the multi-chart dashboard template, CDN scripts keep the page small but need internet at view time;
  offer a `--offline` flag (inline `vlc.javascript_bundle()` once for the whole page) if offline viewing
  matters. Default decision deferred to epic-design.
- **Determinism for snapshot tests:** assert on the emitted *spec dict* (fully deterministic), not on
  PNG bytes (machine-dependent); keep the PNG test a non-empty-bytes smoke test.
- **`description` field:** set it on every spec (from the model `title`/`subtitle`) for the SVG aria-label.
- **Fonts in CI:** the generic font stack avoids shipping fonts; if a PNG test asserts layout, pin the
  font to Liberation Sans (bundled) to avoid host-font drift.

---

## Sources
- ds-engine locked research: `/Users/<user>/dev/ds-engine/.research/briefs/adhoc-viz-rendering/parent.md`,
  `dashboarding-for-ai-agent-platform/parent.md`, `rendering-pipeline-server-vs-client.md`,
  `theming-accessibility-design-system.md`.
- ds-engine implementation (reference, not ported): `src/viz/strip-and-inject.ts`, `render-ssr.ts`,
  `schema/ds-engine-viz-spec.json`, `validator.ts`, `theme/*.ts`; `src/viz-core/VizMount.tsx`;
  `src/output/dashboard-layout/types.ts`.
- legacy-engine source: `analytics/{metashare,matchup,trends,charts}.py`, `models/matchup.py`,
  `advisory/positioning.py`, `generation/consensus.py`, `ingestion/banlist.py`, `cli.py`, `config.py`;
  patterns `constants-only-config`, `cli-nested-groups`, `pydantic-base-model`, `confidence-metadata`.
- vl-convert-python: [PyPI](https://pypi.org/project/vl-convert-python/) · [GitHub vega/vl-convert](https://github.com/vega/vl-convert) · [thirdparty fonts](https://github.com/vega/vl-convert/blob/main/thirdparty_font.md).
- Altair: [PyPI](https://pypi.org/project/altair/) · [v6.1.0 notes](https://github.com/vega/altair/releases/tag/v6.1.0).

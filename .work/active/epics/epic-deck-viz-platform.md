---
id: epic-deck-viz-platform
kind: epic
stage: drafting
tags: [viz]
parent: null
depends_on: [epic-meta-analytics, epic-advisory, epic-deck-generation, epic-regime-aware-advisory]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-06-01
---

# Deck Visualization Platform

## Brief
A reusable, local visualization layer for legacy-engine that supersedes today's matplotlib→PNG
`analytics/charts.py`. It authors **Vega-Lite** specs in Python and renders them two ways — interactive
self-contained **HTML** (via `vega-embed` from CDN) and static **PNG** (via `vl-convert`, a Rust
renderer with no Chrome dependency) — behind a small composable spec/theme/layout layer. The headline
deliverable is a reusable **per-deck dashboard** template: one page composing meta-share, the matchup
spread, trends-across-ban-regimes, positioning (best-call vs best-deck), and the consensus 60+15 list +
primer for any archetype. Fully local — no server, no cloud, no MCP, no SPA — mirroring the existing
self-contained-HTML precedent (the `/knowledge-graph` and kanban-`board` renderers). It can later feed
the Moxfield surfacing work ([deck-generation-and-moxfield.md](../../../docs/briefs/deck-generation-and-moxfield.md)).

This is the promotion of backlog idea `idea-deck-viz-platform`. Prior art lives in the sibling
**ds-engine**, but its viz stack has grown into a 14–16-phase TypeScript / GCP (BigQuery+GCS) / MCP /
React enterprise dashboarding-as-a-service platform — far too heavy to port into a local Python/DuckDB
CLI. We reuse the **technique and the locked research lessons**, not the platform. ds-engine's research
already paid for the landscape (`.research/briefs/adhoc-viz-rendering`,
`dashboarding-for-ai-agent-platform`); a fresh full campaign is NOT needed.

## Strategic decisions
- **Ambition level — reusable local mini-platform, not a charts.py tweak and not a ds-engine port**: a
  real spec layer (Vega-Lite sub-schema + structural validator + canonical theme + 12-col tile/layout)
  PLUS the per-deck dashboard, fully local. Composable so other commands can emit tiles. — Andrew, this session.
- **Render outputs — BOTH interactive HTML and static PNG**: interactive HTML via vega-embed for
  exploring a dashboard in a browser; static PNG via vl-convert for primers / Moxfield surfacing /
  sharing where JS can't run. — Andrew, this session.
- **Relationship to `charts.py` — supersede, not coexist**: the Vega-Lite stack replaces the matplotlib
  charts path rather than living beside it (Andrew did not elect to keep matplotlib). Migrate the
  existing chart surfaces (tier list, meta share, matchup heatmap, trends) onto the new renderer.
  — Andrew, this session.
- **Audience / footprint — unchanged**: still CLI-first, local-only analytics. A read-only dashboard is
  a reporting surface, not the "deck-building UI" the VISION rules out; VISION and PRINCIPLES are
  unaffected. (ARCHITECTURE + SPEC rolled forward this session.)

## Locked technical decisions (bake into design)
- **Vega-Lite is the spec format.** ds-engine research: it is the only format with reliable
  LLM/pretraining coverage and a JSON schema — it beats ECharts/Plotly on the axis that matters for
  programmatic/agent authoring.
- **Strip-and-inject theming is mandatory.** vega-embed #27: a spec-internal `config:` takes
  precedence, so the canonical project theme must be *stripped* from authored specs and *re-injected*
  at render time. Non-negotiable for consistent output.
- **Spec layer**: a curated Vega-Lite sub-schema + a structural validator + the canonical theme + a
  12-col grid tile/layout model. Commands emit composable tiles; the dashboard composes tiles.
- **Two renderers off one spec**: `render_html` (self-contained, vega-embed from CDN, interactive) and
  `render_png` (vl-convert, offline, no browser/Chrome).
- **Per-deck dashboard** composes five existing surfaces, each fed by already-built code:
  meta-share (`analytics/metashare`), matchup spread (`analytics/matchup` — use the **adaptive per-cell
  ban-aware matrix**, not a uniform window, per the regime-aware-advisory lesson), trends across
  ban-regimes (`analytics/trends`), positioning best-call vs best-deck (`advisory/positioning`), and the
  consensus 60+15 list + primer (`generation/consensus`).
- **Confidence/labels carry through.** Every chart respects source-transparency + confidence-gating
  (online/paper/blend label, window, tier) exactly as the text reports do — no unlabeled headline
  numbers, no sub-threshold cells shown.
- **Fully local / offline.** No web server, no cloud, no MCP, no SPA. Self-contained HTML opened
  directly in a browser; PNG needs no runtime.

## Brief (DONE — ready for /epic-design)
Integration brief written: [docs/briefs/deck-viz-platform.md](../../../docs/briefs/deck-viz-platform.md).
It harvests ds-engine's locked research and resolves all four legacy-engine-specific unknowns. Key
resolutions that shape the design:
1. **`vl-convert-python`** is the SINGLE render dependency — `vegalite_to_png` (static PNG) AND
   `vegalite_to_html` (self-contained interactive HTML). Zero-dependency wheel, macOS-arm64 + linux, no
   Chrome/Node. Pin `>=1.9,<2`, `vl_version="6.4"`.
2. **Authoring = hand-built Vega-Lite dicts, NOT Altair** (small fixed vocabulary, we already need
   vl-convert, tight theme control, trivial snapshot tests).
3. **Scope trim:** because we author every spec ourselves, ds-engine's runtime AJV validator +
   correction-loop + curated sub-schema are NOT needed — validation is test-time (`jsonschema` +
   JSON snapshots). The "structural validator" unit shrinks accordingly.
4. **charts.py migration win:** keep its pure `_*_model` prep dataclasses (matplotlib-free honesty
   logic), write `spec_*` Vega-Lite builders against them, drop the matplotlib renderers + dep.
5. **Per-deck dashboard** = our own 12-col HTML template (charts via vega-embed + card-list/primer as
   HTML); a whole-page PNG is OUT (no browser) — PNG export is per-tile.

Suggested 3-feature decomposition (dependency-ordered): (1) `viz/` foundation (theme + strip-and-inject
+ render png/html + test-time validation); (2) migrate the 4 charts.py surfaces; (3) per-deck dashboard
(layout + deck_dashboard + Tiles B/D/E + `viz deck` CLI).

## Dependencies
`depends_on`: `epic-meta-analytics`, `epic-advisory`, `epic-deck-generation`, `epic-regime-aware-advisory`
— all `done`. The dashboard composes their outputs; no new analytics are required, only presentation.

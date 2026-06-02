---
id: epic-deck-viz-platform
kind: epic
stage: drafting
tags: [viz, needs-brief]
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
  PLUS the per-deck dashboard, fully local. Composable so other commands can emit tiles. — the maintainer, this session.
- **Render outputs — BOTH interactive HTML and static PNG**: interactive HTML via vega-embed for
  exploring a dashboard in a browser; static PNG via vl-convert for primers / Moxfield surfacing /
  sharing where JS can't run. — the maintainer, this session.
- **Relationship to `charts.py` — supersede, not coexist**: the Vega-Lite stack replaces the matplotlib
  charts path rather than living beside it (the maintainer did not elect to keep matplotlib). Migrate the
  existing chart surfaces (tier list, meta share, matchup heatmap, trends) onto the new renderer.
  — the maintainer, this session.
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

## Needs-brief (legacy-engine-specific, before /epic-design)
Tagged `[needs-brief]`. The remaining unknowns are integration-grain, not landscape-grain. The brief
(`/brief`) must resolve:
1. **`vl-convert-python`** integration — packaging, version, invocation, theme/font handling, failure
   modes; confirm it's the PNG path (vs alternatives) at our scale.
2. **Authoring path — Altair vs hand-built Vega-Lite JSON** from Python. Trade-offs: Altair ergonomics
   + dependency weight vs. hand-built JSON + full control of the curated sub-schema. Pick one.
3. **Tile data contracts** — the exact existing `legacy_engine` analytics/advisory/generation functions
   (and their return records) that feed each of the five dashboard tiles, and the shape each tile needs.
4. **charts.py migration map** — which current chart surfaces map to which new tiles, and the CLI
   surface (`viz deck …` plus any `report --html`/`--png` wiring) that replaces the matplotlib path.

Do NOT re-run a full research campaign — harvest ds-engine's locked briefs for the landscape.

## Dependencies
`depends_on`: `epic-meta-analytics`, `epic-advisory`, `epic-deck-generation`, `epic-regime-aware-advisory`
— all `done`. The dashboard composes their outputs; no new analytics are required, only presentation.

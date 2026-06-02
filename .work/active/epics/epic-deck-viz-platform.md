---
id: epic-deck-viz-platform
kind: epic
stage: done
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

## Design decisions
- **Dashboard HTML script loading**: CDN triple (`vega@6`/`vega-lite@6`/`vega-embed@7`) by default; an
  `--offline` flag inlines vl-convert's `javascript_bundle()` for a fully self-contained page.
  Single-tile HTML export is self-contained by default (`vegalite_to_html(bundle=True)`). — resolved this
  session (reversible flag; multi-chart offline bundles would be heavy, so CDN is the sane default).
- **`report --chart-dir` disposition**: removed; all rendering centralizes under the `viz` group (SSOT).
  No `--html/--png` forwarding on `report` for v1. — resolved this session (reversible; cleaner surface).

## Decomposition
Split by capability into a 3-feature dependency chain (per brief §7). A linear chain rather than parallel
fan-out is deliberate: the dashboard reuses the migration's `spec_metashare`/`spec_trends` builders, and
both depend on the foundation's render/theme/validation plumbing — the shared-contract edges are real, so
forcing parallelism would duplicate builders. The epic is small (3 features); the critical path is fine.

### Child features
- `epic-deck-viz-platform-foundation` — theme + strip-and-inject + render (png/html) + test-time validation; adds vl-convert-python dep — depends on: `[]`
- `epic-deck-viz-platform-charts-migration` — move the 4 pure `_*_model` prep dataclasses into viz/, write `spec_*` Vega-Lite builders, drop matplotlib `render_*` + the dep — depends on: `[epic-deck-viz-platform-foundation]`
- `epic-deck-viz-platform-dashboard` — `layout.py` + `deck_dashboard.py` (5 tiles) + net-new Tile B/D/E builders + the `viz` CLI group — depends on: `[epic-deck-viz-platform-foundation, epic-deck-viz-platform-charts-migration]`

### Decomposition risks
- **Dashboard is the largest feature** (5-tile composer + 3 net-new builders + layout template + CLI
  group + migrated leaves ≈ 10-12 units). If `/feature-design` finds it overflows one pass, split the
  `viz` CLI group off as a child story.
- **Linear critical path** means no parallelism across the three; acceptable for a 3-feature epic, but it
  does mean the dashboard can't start until both predecessors land.

## Dependencies
`depends_on`: `epic-meta-analytics`, `epic-advisory`, `epic-deck-generation`, `epic-regime-aware-advisory`
— all `done`. The dashboard composes their outputs; no new analytics are required, only presentation.

## Completion
All three child features `done` (foundation → charts-migration → dashboard). Final completion review
(fresh-context Opus; same-model, Codex out) verdict: **Complete** after foundation-doc reconciliation.
- **Code/tests/integration/e2e: sound.** Suite 1173 green. `import legacy_engine.{cli,viz,analytics}` clean.
  End-to-end on the real seeded DB: `viz deck` writes a 12-col dashboard HTML (4 vegaEmbed tiles +
  non-fabricated primer) + per-tile PNGs; `viz meta|matchups|trends|tiers` render; apostrophe archetypes
  render. matplotlib fully removed.
- **Accepted findings (all doc-drift, fixed in this pass):** reconciled ARCHITECTURE.md (`viz/` module
  table → as-built theme/models/specs/render/layout/deck_dashboard; removed deleted `charts.py` row;
  removed matplotlib + altair from deps, vl-convert-python is the single render dep; 5 viz CLI commands;
  data-flow + frontmatter) and SPEC.md (dropped the "structural validator" over-claim → test-time
  validation). Regenerated the knowledge index. No code defects found.

v1 ships: a reusable local Vega-Lite viz layer (hand-built specs, dark theme, dual HTML+PNG output) that
replaces matplotlib, plus the headline attack-focused per-deck dashboard with auto-primer. NOT pushed —
the maintainer controls publication.

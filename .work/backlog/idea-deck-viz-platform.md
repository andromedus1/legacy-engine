---
id: idea-deck-viz-platform
created: 2026-05-30
tags: [viz, needs-research]
---

Build a visualization **platform** for legacy-engine (beyond today's matplotlib→PNG `charts.py`) plus a good, reusable **per-deck template** — a rich per-archetype "deck dashboard" surface composing meta-share, the matchup-spread, trends-across-ban-regimes, positioning (best-call vs best-deck), and the consensus list + primer, that could also feed the Moxfield surfacing work (`docs/briefs/deck-generation-and-moxfield.md`) and extend the analytics `charts` feature. Prior art to reuse (not reinvent) lives in **ds-engine**: a Vega-Lite spec format authored from Python via Altair and rendered in-browser via `vega-embed` (see `ds-engine/docs/research/_archive/adhoc-viz-rendering.md`); an agent-viz pipeline in `ds-engine/src/viz/` (viz-spec JSON schema, static-analyzer, validator, correction-loop, render-ssr, theme); a `dashboard-viewer` SPA + dashboard tooling/components; and research in `.research/briefs/dashboarding-for-ai-agent-platform` + `adhoc-viz-rendering` + `dashboarding-landscape`. Research-first: a `/research` or `/brief` pass on adapting that stack to legacy-engine should precede design.

---
id: epic-meta-analytics-charts
kind: feature
stage: drafting
tags: [analytics]
parent: epic-meta-analytics
depends_on: [epic-meta-analytics-metashare, epic-meta-analytics-matchup-matrix, epic-meta-analytics-trends]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Analytics Charts (tier list · meta share · matchup heatmap · trends)

## Brief
The rendering layer over the three analytics data producers. Render matplotlib charts (edh-engine's
charting pattern): a **meta-share chart** (per definition, online/paper), a **matchup heatmap** (the
`MatchupCell` matrix, color-scaled by shrunk rate, low-n cells visually muted/blanked to honor the n<30
display gate), a **tier-list** view (archetypes bucketed by share + confidence), and a **trends chart**
(share trajectories across ban-list regimes from `trends`). Charts must **render confidence honestly**:
suppressed/low-n cells are visibly distinct (not shown as a confident value), and every chart carries
the provenance/caveat line (matchup-n ≪ metashare-n; window; online/paper basis) so a saved image is
self-describing.

Owns the final wiring of the `report meta | matchups | tiers` CLI surface to actually emit charts (and
text summaries) to an output path, replacing the current `_not_implemented` stubs. Reads the computed
results from `metashare`, `matchup-matrix`, and `trends`; it does not recompute any statistic — purely
a presentation + CLI-output feature.

Does NOT compute any meta-share, matchup, or trend statistic (consumes them), and does NOT render
advisory outputs (that's `epic-advisory`'s report surface).

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: terminal feature — consumes `metashare`, `matchup-matrix`, and `trends`; renders
  and wires the CLI report surface. The epic's user-facing payoff.

## Inherited design decisions
- **Charts render confidence honestly**: low-n / suppressed cells visibly distinct; n<30 display gate respected visually.
- **Every chart is self-describing**: provenance/caveat line baked in (matchup-n ≪ metashare-n, window, online/paper basis).
- **Presentation only** — recompute nothing; consume `metashare` / `matchup-matrix` / `trends` outputs.
- Follow **edh-engine's matplotlib charting pattern**.

## Research briefs
- `docs/briefs/advisory-methods.md` — §1 presentation prior art (mtgdecks match-count headline, ≥2% row inclusion, per-cell n<30 hide, CI on every shown cell).
- `docs/briefs/legacy-metagame.md` — the meta as a sanity-check target for the rendered output.

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/charts.py`; the `report meta|matchups|tiers` CLI group; "edh-engine charting pattern".
- `docs/SPEC.md` — source-transparency / confidence-gating NFRs (charts are a surface that must honor them).

<!-- feature-design fills in: the chart functions, the CLI leaf wiring + output paths, and test approach (smoke-render + assert low-n suppression). -->

---
id: epic-meta-analytics
kind: epic
stage: drafting
tags: [analytics]
parent: null
depends_on: [epic-tournament-ingestion, epic-archetype-classifier]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Meta & Performance Analytics

## Brief

The first pillar's payoff: turn archetype-labeled tournament data into the metagame. Compute meta-share
three labeled ways (raw count / top-cut presence / win-rate-weighted) split online/paper/blend, build
the matchup matrix from `Rounds` (Wilson CIs + Beta-Binomial shrinkage + confidence tiers, with
matchup-n kept separate from metashare-n), track trends across ban-list regimes, and render charts
(tier list, meta share, matchup heatmap, trends).

This is "what's the meta, and how do the decks match up" — the descriptive foundation the advisory
pillar consumes. Covers the SQL aggregation over DuckDB + the statistical layer (scipy/statsmodels).
Does NOT cover the positioning score, sideboard recommender, or what-to-play advisor (that's
`epic-advisory`).

## Research briefs
- `docs/briefs/advisory-methods.md` — matchup-matrix statistics (Wilson, shrinkage, tiers, n<30 display gate, bimodal-coverage caveat).
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — the three meta-% definitions, online/paper split, matchup computation from Rounds.
- `docs/briefs/legacy-metagame.md` — the current meta as a sanity-check target; the meta-speed-metric direction.

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/` (metashare, matchup, trends, charts); MatchupCell model; confidence tiers.
- `docs/SPEC.md` — MatchupCell entity; confidence-gating + source-transparency NFRs.
- `docs/PRINCIPLES.md` — never an unlabeled meta-%; confidence-gate every stat.

## Anticipated child features
- Meta-share computation (3 definitions, online/paper/blend, ≥2% inclusion) over DuckDB
- Matchup matrix (Rounds → cells; Wilson CI + Beta-Binomial shrinkage + tiers; mirror=50%; n separation)
- Trends across ban-list regimes (version-stamped)
- Charts (tier list, meta share, matchup heatmap, trends)

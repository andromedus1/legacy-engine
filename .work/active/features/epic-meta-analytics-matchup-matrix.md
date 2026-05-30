---
id: epic-meta-analytics-matchup-matrix
kind: feature
stage: drafting
tags: [analytics]
parent: epic-meta-analytics
depends_on: [epic-meta-analytics-match-results]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Matchup Matrix (Wilson + Beta-Binomial shrinkage + tiers)

## Brief
Turn the directed `(archetype_a, archetype_b) → {wins, losses, n}` aggregates from `match-results`
into a presentable matchup matrix of `MatchupCell`s. Per cell compute: the **raw rate** `p̂ = wins/n`
(always shown with `n`), a **Wilson score 95% CI** (the single default — Wald is forbidden; Jeffreys
as the n≤40 alternative), and a **Beta-Binomial shrunk estimate** `p̃ = (α+wins)/(α+β+n)` with a prior
centered at 50% and modest strength (α=β≈5–10) — so a 3–1 cell reads ~54%, not 75%, while a 200-game
cell is essentially unshrunk. **Display both raw and shrunk — shrinkage is never the only number
shown.** Fix **mirror cells at 50.0%, report n only** (no CI). Define and emit the `MatchupCell` model
(`{wins, n, p_raw, p_shrunk, ci_low, ci_high, tier}`) into `models/`.

Attach a **confidence tier** to each cell via the existing tiering, with the **display gate at n<30**
(advisory-methods resolves the ops brief's n<100 down to n<30 — n<100 is the *established* floor, while
30–99 carries usable directional signal the CI honestly bounds): n<30 **speculative** → hide the rate,
show "n=X, insufficient"; 30–99 **evolving** → shrunken rate + Wilson CI, flagged; ≥100 **established**
→ rate + CI, full confidence. Carry the **mandatory bimodal-coverage caveat**: matchup-n ≪ metashare-n
(only rounds-bearing events contribute), kept as a separate labeled field, with a provenance line on
every matrix. Row inclusion gated at ≥2%-of-matches (mtgdecks-style). Online/paper split honored.
Wires the `report matchups` CLI leaf. Prefer `statsmodels.stats.proportion.proportion_confint` for the
Wilson/Jeffreys CIs (hand-rolled Wilson acceptable fallback).

Does NOT do the per-archetype rounds join or result parsing (that's `match-results`), the positioning
score / Bayesian MC (that's `epic-advisory`), or chart rendering (`charts`).

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: consumer of `match-results`. Parallel to `metashare`. Producer of the
  `MatchupCell`s that `charts` (heatmap) and downstream `epic-advisory` consume.

## Inherited design decisions
- **Wilson CI as the single default**; Jeffreys for n≤40; Wald forbidden.
- **Beta-Binomial shrinkage** prior centered 50%, α=β≈5–10; **show raw AND shrunk**, never shrunk alone.
- **Mirror fixed at 50.0%**, n only, no CI.
- **Display gate n<30** (hide rate); 30–99 evolving (flagged); ≥100 established — reuse `tier_for_sample`.
- **matchup-n separate from metashare-n** + mandatory bimodal-coverage provenance caveat on every matrix.

## Research briefs
- `docs/briefs/advisory-methods.md` — §1 (matchup-matrix estimation: Wilson formula, Jeffreys, Beta-Binomial shrinkage, the confidence-tier table, the n<30 display gate, the bimodal-coverage caveat, mtgdecks ≥2% row inclusion).
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — §4.3/§4.5 (bimodal coverage, external-matrix cross-check is validation-only), §6 (gating).

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/matchup.py`; `models/` `MatchupCell` + `ConfidenceMetadata`.
- `docs/SPEC.md` — `MatchupCell` entity; confidence-gating + source-transparency NFRs.
- `docs/PRINCIPLES.md` — #7 confidence-gate-every-stat.

<!-- feature-design fills in: the MatchupCell field types, Wilson/Jeffreys/shrinkage helper signatures, the matrix builder, the CLI leaf, and test approach (synthetic aggregates → verify Wilson/shrinkage/tiers/mirror). -->

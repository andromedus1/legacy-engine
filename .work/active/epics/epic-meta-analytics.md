---
id: epic-meta-analytics
kind: epic
stage: done
tags: [analytics]
parent: null
depends_on: [epic-tournament-ingestion, epic-archetype-classifier]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
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

## Decomposition

Split by **capability**, with one shared **foundation feature extracted**. The provisional sketch had
four arcs (metashare, matchup, trends, charts) mapping 1:1 to the architecture's `analytics/` files. The
realized shape adds a fifth, `match-results`, pulled out in front of metashare and matchup: both the
win-rate-weighted meta-share (§3c) and every matchup cell need the same rounds→archetype match-outcome
join — including the player-name normalization the ops brief flags as the weak link. Extracting it once
removes duplication and lets metashare and matchup-matrix parallelize. Trends reuses metashare's
per-window computation; charts is the terminal rendering + CLI-wiring sink over all three producers.

The dependency graph is a clean DAG (`match-results` source → `charts` sink), so autopilot can run
metashare ∥ matchup-matrix after the foundation lands.

### Child features

- `epic-meta-analytics-match-results` — rounds→archetype match-outcome join, player-name normalization, result-string parsing (match-level W/L), byes/draws handling, per-pair + per-archetype raw aggregates; surfaces unmatched-pairing coverage — depends on: `[]`
- `epic-meta-analytics-metashare` — three labeled meta-% definitions (raw / top-cut / win-rate-weighted), online/paper/blend split, ≥2% inclusion floor, confidence tiers; wires `report meta` — depends on: `[epic-meta-analytics-match-results]`
- `epic-meta-analytics-matchup-matrix` — `MatchupCell`s from the raw aggregates: Wilson CI + Beta-Binomial shrinkage + confidence tiers (n<30 display gate) + mirror=50% + matchup-n separation + bimodal caveat; wires `report matchups` — depends on: `[epic-meta-analytics-match-results]`
- `epic-meta-analytics-trends` — version-stamped meta-share evolution segmented by ban-list regime; window gating — depends on: `[epic-meta-analytics-metashare]`
- `epic-meta-analytics-charts` — matplotlib tier list / meta share / matchup heatmap / trends, confidence rendered honestly; wires the `report` CLI output surface — depends on: `[epic-meta-analytics-metashare, epic-meta-analytics-matchup-matrix, epic-meta-analytics-trends]`

## Design decisions

Resolved under autopilot delegation (no strategic 50/50s — all pinned by the briefs / architecture /
codebase; logged here so each feature-design pass inherits them):

- **Match-result granularity**: match-level W/L, not game-level. `rounds.result` ("2-1") is an aggregate match score, not per-game winners — count one match win for the winner. *(ops brief §4.2, explicit.)*
- **rounds↔decks join key**: normalized `player` name within a `tournament_id` (the only available key); pairings that don't resolve to a labeled deck → surfaced `unmatched` coverage count, never silently dropped. Byes/draws/forfeits dropped from win-rate accumulation. *(ops brief §4.4 + project never-drop-silently convention.)*
- **Win-rate-weighted meta-share couples to the foundation**: metashare §3c consumes `match-results`' per-archetype win/loss; §3a/§3b are pure deck counts. Hence the `metashare → match-results` edge.
- **Confidence display gate = n<30** (hide rate, show n), 30–99 evolving (flagged), ≥100 established — advisory-methods resolves the ops brief's n<100 *down* to n<30 (n<100 is the *established* floor; 30–99 carries usable directional signal the CI honestly bounds). Reuse `confidence.tier_for_sample`.
- **MatchupCell ownership**: lives in `models/` (per architecture). `match-results` emits raw `{wins, losses, n}` aggregates; `matchup-matrix` produces the full `MatchupCell {p_raw, p_shrunk, ci, tier}`.
- **Charts is a separate terminal feature** (matches architecture's `charts.py`) depending on all three data producers — rather than per-feature rendering — so the `report` CLI surface and confidence-honest rendering live in one place.
- **Matchup trends deferred** from `trends` (MVP = meta-share trends only): per-regime matchup sample is too sparse to present honestly; revisit post-MVP.

## Decomposition risks

- **Player-name join coverage** (`match-results`): handles/casing/byes make the rounds↔decks join lossy; sparse joins → thin matchup cells. Mitigated by surfacing the unmatched-pairing coverage as an explicit stat (not silent), and by the n<30 display gate downstream. This is the riskiest unit — design it first within `match-results`.
- **Bimodal coverage** is structural, not a bug: MTGO Leagues feed metashare-n but contribute zero matchup-n. The separate-aggregates design (`match-results`) and the mandatory provenance caveat (`matchup-matrix`, `charts`) contain it, but the matchup matrix will always be a smaller, challenge/paper-skewed sample — must stay labeled as such.
- **Trends regime boundaries** depend on `BanListSnapshot` dates from the (done) ingestion epic; if B&R snapshots are sparse, regimes are coarse — acceptable for MVP.

## Children complete (2026-05-30)

All five child features are at `stage: done`:
- `epic-meta-analytics-match-results` — rounds→archetype join, player-name normalization, raw aggregates
- `epic-meta-analytics-metashare` — three labeled meta-% definitions + online/paper split + confidence tiers
- `epic-meta-analytics-matchup-matrix` — Wilson/Jeffreys CI + Beta-Binomial shrinkage + n<30 gate
- `epic-meta-analytics-trends` — version-stamped meta-share evolution across ban-list regimes
- `epic-meta-analytics-charts` — matplotlib tier-list / meta-share / matchup-heatmap / trends + CLI wiring

Advancing epic `implementing → review` for aggregate epic-level review. Suite: 344 tests green.

## Review (2026-05-30) — epic-level

**Verdict**: Approve

**Lenses** (per-line lenses skipped — exercised in each child's own review):
- **Design alignment**: realized decomposition matches the brief — the 5-feature shape (match-results foundation → metashare ∥ matchup-matrix → trends → charts sink) is a clean DAG, built in dependency order. The provisional 4-arc sketch's `match-results` extraction paid off (no duplicated rounds→archetype join).
- **Capability completeness**: "what's the meta, and how do the decks match up" works end-to-end. CLI surface delivered: `report meta` (3 labeled definitions × online/paper), `report matchups` (Wilson/Jeffreys CI + Beta-Binomial shrinkage + n<30 gate + bimodal caveat), `report tiers` (S/A/B), `report trends` (version-stamped across ban-list regimes), all with `--chart-dir` PNG output via `charts.py`.
- **Foundation-doc alignment**: one drift found and fixed inline — `ARCHITECTURE.md` CLI enumeration omitted the `report trends` leaf added by the trends feature; now `report meta|matchups|tiers|trends`. No other drift (analytics/ module table, MatchupCell, confidence tiers all match code).
- **Breaking changes**: none cross-cutting. metashare/match_results gained only additive, default-None kwargs (date window); `compute_all` untouched; all prior tests green.

**Blockers**: none (the ARCHITECTURE drift was fixed inline during this review)
**Important**: none
**Nits**: carried in each child's review (unused imports in trends.py/charts.py; render_trends legend dedupe) — cosmetic, deferred to next touch.

**Notes**:
- Confidence-honesty thread holds across the whole epic: never an unlabeled meta-% (PRINCIPLES #6); n<30 display gate enforced in matchup cells and rendered as masked heatmap cells; matchup-n kept distinct from metashare-n; bimodal-coverage caveat carried from `match-results` through `matchup-matrix` into `charts`; thin trend windows capped at `evolving`.
- 344 tests green across the suite. Left at `stage: done` in active/ (no release_binding) for late-binding pickup by `/agile-workflow:release-deploy` — not archived, per the project's late-binding-releases rule.

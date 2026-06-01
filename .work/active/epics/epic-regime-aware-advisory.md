---
id: epic-regime-aware-advisory
kind: epic
stage: drafting
tags: [advisory, analytics, correctness]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Regime-Aware Advisory

## Brief

The advisory pillar — `analytics/matchup.build_matrix`, `analytics/match_results.compute_match_results`,
and everything downstream (`advisory/positioning` best-deck/best-call, `report matchups`, `advise *`,
`report gaps`) — is computed over the **full corpus** and is **not** ban-regime / banlist aware.
`compute_match_results` takes no `since/until` (windowed `wrw` already raises `NotImplementedError`).

**Consequence (observed 2026-06-01):** with data through 2026-05-30 the full-corpus positioning ranked
**Dimir Reanimator the #1 best deck AND best call** — but the **Entomb ban (2025-11-10)** had already
collapsed it from 9.1% → 0.1% share; it is dead in the current format. Likewise the **Undercity Informer
ban (2026-05-18)** cut Oops! All Spells 5.1% → 1.7%. The meta-share / `trends` layer IS regime-aware and
correctly shows these declines, so **the engine contradicts itself between layers** and the advisory layer is
stale-and-wrong after any format-defining ban.

This epic makes the advisory layer regime-aware, in two sequenced arcs:

- **v1 — uniform windowing plumbing.** Thread `since/until` through `compute_match_results → build_matrix →
  positioning/rank_decks/gaps`. Add `--since`/`--regime` to `report matchups`, `report meta` (currently
  un-windowed — only `trends` windows today), `advise *`, and `report gaps`. A `--regime` shorthand resolves
  to the current (or a named) ban-regime window via `analytics.trends.regime_windows`. Behavior stays
  **full-corpus by default**; windowing is opt-in.
- **v2 — adaptive per-matchup-cell windowing.** Each archetype gets a **`valid_since`** = the date of the
  most recent ban whose banned card it actually ran (≥ an inclusion threshold in the pre-ban regime —
  data-derived from `card_frequencies` × the banlist × `regime_windows`). A pairwise cell **A vs B** pools
  data back to **`max(valid_since(A), valid_since(B))`**; positioning always weights by the **current** field
  shares. Unaffected×unaffected cells keep full history (established tier); ban-affected cells truncate
  honestly. Then v2 **flips the default** to the adaptive window. Validated against real data: ban
  affectedness is starkly bimodal (Entomb = 100% of Dimir Reanimator decks / ~0% elsewhere; Undercity
  Informer = 99.9% of Oops! / 0% elsewhere), so a simple inclusion threshold classifies cleanly.

Not in scope: the goldfish pillar; recency-weighting as an alternative to hard windows (noted as a future
lever, not v1/v2).

## Strategic decisions
- **Default behavior = adaptive default (v2-aware)**: v1 ships **full-corpus-default + opt-in** `--since`/`--regime`
  flags (backward-compatible); **v2 flips the default to the adaptive per-cell window** (max valid data per
  matchup, current-field weighting) — the smartest default. Full-corpus stays available via an explicit
  `--all-time` flag.
- **Thin-regime policy = degrade + loud caveat**: when the requested/current regime is too thin for reliable
  matchup/positioning math (e.g. the 12-day / 483-decisive-round post-Undercity-Informer regime), fall back to
  the widest defensible window (full-corpus in v1; the v2 adaptive window in v2) and print a **prominent
  banner** ("current regime too thin: n=X, flagged evolving — showing wider data"). Always returns an answer,
  never silently and never empty.

## Anticipated child features (sketch — realized at /epic-design)
- **v1: `windowing-plumbing`** — `since/until` through `compute_match_results` → `build_matrix` →
  `positioning`/`rank_decks`/`gaps`; `--since`/`--regime`/`--all-time` on `report matchups|meta|gaps` +
  `advise *`; thin-regime degrade-with-banner. `depends_on: []`.
- **v2: `adaptive-cell-windowing`** — `valid_since` per archetype from banned-card inclusion (data-derived,
  conservative when lists shift); per-cell window = `max(valid_since(A), valid_since(B))`; current-field
  weighting; flip the default to adaptive; per-cell window surfaced in output (auditability).
  `depends_on: [v1]`.
- (epic-design may split v1's CLI surface from the core windowing, or v2's affectedness-classifier from the
  cell-windowing, if sizing warrants.)

## Known limits to design around (from the analysis)
- **Affectedness via card-inclusion catches DIRECT hits, not indirect ones** — a deck that didn't run the
  banned card but rebuilt because the field shifted reads as "unaffected" though its tech moved. Be
  conservative (shorten the window when an archetype's lists churn) and **always surface the window each cell
  used** (audit-everything ethos).
- **Archetype-label drift** — pooling assumes an archetype is "the same deck" across the window; strongest for
  stable/unaffected decks (where the technique is needed), weakest for churning ones. Acceptable, documented.
- v2 does not try to fix field-level power shifts beyond using **current** field shares — that is the right
  honest estimate (current field × maximally-valid pairwise cells).

## Foundation references
- `docs/ARCHITECTURE.md` — "What's Deferred" → Regime-aware advisory row (this epic); the advisory + analytics
  module tables.
- `src/legacy_engine/analytics/match_results.py` (`compute_match_results`, `compute_card_winrates`),
  `analytics/matchup.py` (`build_matrix`, `beta_binomial_shrink_to`), `analytics/trends.py` (`regime_windows`),
  `advisory/positioning.py` (`rank_decks`, `positioning_score`), `advisory/gaps.py`, `generation/consensus.py`
  (`card_frequencies` — affectedness input), `ingestion/banlist.py` (`current_banlist` — banned cards × dates).
- Promoted from the parked idea `idea-regime-aware-advisory`.

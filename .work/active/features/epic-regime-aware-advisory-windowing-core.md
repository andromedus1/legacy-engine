---
id: epic-regime-aware-advisory-windowing-core
kind: feature
stage: drafting
tags: [advisory, analytics, correctness]
parent: epic-regime-aware-advisory
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Windowing Core (v1 plumbing)

## Brief

The analytics/advisory plumbing that makes regime windowing *possible* — the foundation v1 step.
Thread a date window (`since`/`until`) through the matchup/positioning chain so the matrix can be
built over any window, mirroring the windowing `compute_card_winrates` already has:

- **`analytics/match_results.compute_match_results`** — add `since`/`until` (reuse the same
  date-bounded rounds-join CTE shape `compute_card_winrates` already uses; the dup/uniq_decks guard
  CTE is shared SSOT in this module).
- **`analytics/matchup.build_matrix`** — pass `since`/`until` through to `compute_match_results`.
- **`advisory/gaps.compute_archetype_gaps`** — thread `since`/`until` into both its `build_matrix`
  and `build_global_field` calls (it currently is un-windowed).
- A small **regime resolver** (e.g. `analytics/trends.resolve_regime(name|"current") -> (since, until)`)
  that maps a regime name (or "current") to a window via the existing `regime_windows()` SSOT.

`positioning_score` / `rank_decks` need NO new params — they consume a pre-built `matrix` + `field`,
so windowing happens at matrix/field build time and flows in. Behavior stays **full-corpus by
default** (all new params default to `None` = today's behavior); this feature ships no default change
and no CLI — it is pure additive plumbing so existing tests stay green untouched.

Does NOT cover: the CLI flags / regime UX / thin-regime degrade banner (→ `cli-surface`), nor the
adaptive per-cell windowing (→ `adaptive`). It only makes a uniformly-windowed matrix buildable.

## Epic context
- Parent epic: `epic-regime-aware-advisory`
- Position in epic: foundation feature — `cli-surface` and `adaptive` both build on this windowing.

## Inherited design decisions
- **Full-corpus default preserved in v1** (the default flip is v2/`adaptive`'s job) — all windowing
  params default to `None`.
- Window resolution reuses `analytics.trends.regime_windows` (the dated-ban-regime SSOT); no new ban-date source.

## Research briefs
- `docs/briefs/card-adjacency-and-discovery.md` (windowing/`CardWinRates` reuse context); the epic body.

## Foundation references
- `src/legacy_engine/analytics/match_results.py` — `compute_match_results` (+ the windowed
  `compute_card_winrates` to mirror), the shared dup/uniq_decks CTE.
- `src/legacy_engine/analytics/matchup.py` — `build_matrix`.
- `src/legacy_engine/analytics/trends.py` — `regime_windows` (resolver source).
- `src/legacy_engine/advisory/gaps.py` — `compute_archetype_gaps` (window threading).

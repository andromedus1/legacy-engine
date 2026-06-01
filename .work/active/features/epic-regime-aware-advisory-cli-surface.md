---
id: epic-regime-aware-advisory-cli-surface
kind: feature
stage: drafting
tags: [advisory, analytics, correctness]
parent: epic-regime-aware-advisory
depends_on: [epic-regime-aware-advisory-windowing-core]
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# CLI Surface + Thin-Regime Degrade (v1 UX)

## Brief

The user-facing v1 surface on top of `windowing-core`: opt-in windowing flags + the honest
thin-regime fallback.

- **Flags** on the advisory/report surfaces that consume the matchup matrix / field — `report
  matchups`, `report meta` (currently un-windowed; only `trends` windows today), `report gaps`,
  and `advise *`: `--since`/`--until` (explicit window), `--regime [current|<named>]` (resolve via
  `windowing-core`'s regime resolver), and `--all-time` (explicit full-corpus). Mirror the existing
  Click option/`--db`/`try-finally`/`_setup_logging` conventions.
- **Thin-regime degrade + loud caveat** (the inherited policy): when the requested/current window is
  too thin for reliable matchup/positioning math (below a decisive-round / coverage floor — the
  12-day / 483-round post-Undercity-Informer case is the motivating example), fall back to the
  widest defensible window (full-corpus in v1) and print a **prominent banner** stating the regime
  was too thin (n=X, flagged evolving) and that wider data is shown. Always returns an answer; never
  silently, never empty.
- Echo **which window was actually used** in each command's header (auditability).

Default stays **full-corpus** in v1 (the default flip is v2). Does NOT cover the adaptive per-cell
window (→ `adaptive`) or the core plumbing (→ `windowing-core`).

## Epic context
- Parent epic: `epic-regime-aware-advisory`
- Position in epic: consumer of `windowing-core`; establishes the `--regime`/`--all-time`/window-banner
  UX that `adaptive` later re-defaults.

## Inherited design decisions
- **Full-corpus default in v1; windowing opt-in** via `--since`/`--regime`; `--all-time` is the explicit
  full-corpus escape (kept meaningful into v2 when the default flips).
- **Thin-regime = degrade + loud caveat** (fall back to widest defensible window + prominent banner;
  always returns an answer).

## Research briefs
- The epic body (`## Strategic decisions`); `docs/briefs/card-adjacency-and-discovery.md` for the
  honesty/disclaimer ethos to mirror.

## Foundation references
- `src/legacy_engine/cli.py` — `report matchups|meta|gaps`, `advise *` command group; the
  `report tiers`/`report gaps` option-shape precedent.
- `windowing-core`'s regime resolver + windowed `build_matrix`/`compute_archetype_gaps`.

## Carried-forward nit (from windowing-core review)
- `metashare.py` has stale text now that `compute_match_results` IS windowed: the module docstring (~line 4) and the windowed-`wrw` `NotImplementedError` message (~line 397) both say "match_results is not windowed". Behavior is still correct (the wrw guard stands); fix the wording during this feature's pass.

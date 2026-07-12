---
id: epic-stable-era-windows-consumption
kind: feature
stage: drafting
tags: [analytics, advisory]
parent: epic-stable-era-windows
depends_on: [epic-stable-era-windows-era-ledger]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# stable_since as the default horizon across all regime-windowed surfaces

## Brief

The consumption swap: `stable_since` replaces ban-only `valid_since` as the adaptive-matrix
horizon (`build_adaptive_matrix` cells source over `[max(stable_since(a), stable_since(b)), now)`),
with honest degrade to the ban-only horizon when detection is thin/uncertain for an entity. Camp
labels resolve to their OWN stable_since where the camp cleared detection's density floor,
falling back to the parent's (today `_base_archetype` always falls back — per-camp horizons are
new capability). Every cell carries its detected window + named trigger; the `_adaptive_audit`
line and the advisory-window-resolution block's `// audit` output extend to name disturbances
("Doomsday since 2026-04-20: Flow State adoption"). Scope reaches ALL regime-windowed surfaces
(epic decision): the ~15 advisory-window call sites in cli.py, the `_latest_regime_window`
consensus/card-frequency family (a new-era archetype's consensus windows at its stable_since),
and the FIELD: `build_global_field`'s "current regime" boundary becomes detection-derived (a
confirmed high-share disturbance opens a new global field era) instead of BAN_EVENTS-only.

Display estimates keep the existing flat-0.5 shrinkage in this feature — the hierarchical prior
lands in `-shrinkage` (same release, one user-visible shift; in-tree goldens may re-pin twice).
Discovery's windowing is NOT here (see `-discovery-gate`).

## Epic context

- Parent epic: `epic-stable-era-windows`
- Position in epic: the consumer swap — the epic's user-visible payoff; depends on the persisted
  era ledger.

## Inherited design decisions

- stable_since is the NEW DEFAULT horizon, honest degrade (scope decision).
- Scope reach: ALL regime-windowed surfaces (scope decision).
- Field window — global, detection-derived (design decision).
- Self-heal gate — auto-truncate, labeled (design decision).

## Research briefs

- `docs/briefs/change-point-detection.md` §7 (consumption seam, audit-line extension, fallback
  asymmetry: uncertainty degrades the WINDOW claim, never silently changes the number).

## Foundation references

- `docs/ARCHITECTURE.md` — analytics/matchup.py (`build_adaptive_matrix`, `AdaptiveMatrix.
  cell_windows`), advisory/window.py (`resolve_advisory_window`, `build_advisory_inputs`),
  advisory/field.py (`build_global_field`), generation/consensus.py (`_latest_regime_window`).
- Patterns: advisory-window-resolution-block (the ~15-site block being re-pointed),
  audit-echo-comment-lines, honest-degrade-marker, freshness-stripped-cli-body-golden (goldens
  will re-pin), opt-in-analytics-overlay (contrast: this is deliberately NOT opt-in — epic
  decision).

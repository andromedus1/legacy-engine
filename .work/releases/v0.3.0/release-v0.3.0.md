---
id: release-v0.3.0
kind: release
stage: released
tags: []
parent: null
depends_on: []
release_binding: v0.3.0
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Release v0.3.0

## Bound items

18 items (all active done items without binding; no unbound archived stubs existed):
- epic-subarchetype-resolution + 3 features + 4 stories (PRs #36-#39: discovery engine,
  split-variant matchup cells + labeler display-key fix, conditioned card win-rate + subgroup
  win%, discover apply + completion-review follow-ups)
- epic-deck-prep-arc + 5 features (the 2026-07-04 deck-prep analysis arc: Dimir boards,
  meta decks, Doomsday Tempo variant split, cross-venue comparison, loop reflection)
- feature-archetype-sweep-backtest + 3 stories (PR #35: advise sweep, ILP determinism fix,
  copy-count surfaces)

## Gate runs
- **gate-tests** (2026-07-11) — 7 findings (0 critical, 0 high, 3 medium, 4 low). Mediums drained:
  F1/F2 pinned full-body goldens (PR #41), F3 spec reconciliation in the sweep feature body. Lows →
  backlog (gate-tests-low-findings-v030). Verdict: bundle passes; every acceptance criterion covered.
- **gate-cruft** (2026-07-11) — 3 findings (0 high, 2 medium, 1 low). Mediums drained: dead noqa'd
  import + 3 test F401s (PR pending). Low (belt-and-braces except, keep-leaning) → backlog. Bundle
  notably clean; all 15 src files ruff-clean.
- **gate-docs** (2026-07-11) — 9 findings (root cause of 5: the #35 sweep never doc-rolled).
  8 drained in one pass (ARCHITECTURE/SPEC/CHANGELOG/README/pattern anchors); 1 research-tier
  no-edit. gate-docs-v030-drift → done.
- **gate-patterns** (2026-07-11) — 2 new patterns codified (opt-in-analytics-overlay,
  freshness-stripped-cli-body-golden); 3 pattern-doc inconsistencies fixed inline with the docs
  drain (no code divergence). gate-patterns-v0.3.0 → done.

## Shipped (2026-07-11)

- Mapping: tag-based — tag `v0.3.0` pushed on main (5a49aa2); CI green on every bundle PR (#35-#42).
- Items shipped: 22 (18 bound at planning + 5 gate/release-window items).
- Gate finding totals: tests 7 (0C/0H/3M/4L) · cruft 3 (0H/2M/1L) · docs 9 (8 drained, 1 no-edit)
  · patterns 2 new patterns + 3 doc-drift fixes. All Medium+ findings drained pre-ship.

## Shipped items

Bodies live in git history — read with `git show 5a49aa2~1:<path>`.

| id | title | kind | archived_atop | git ref |
|----|-------|------|---------------|---------|
| bug-discover-camp-name-collision | Bug: discover auto-naming can assign the SAME name to two camps | story | — | 5a49aa2 |
| epic-deck-prep-arc | Deck-prep dogfooding arc — Dimir + Doomsday Tempo across both metas, t | epic | — | 5a49aa2 |
| epic-deck-prep-arc-comparison | Dimir Tempo vs Doomsday Tempo — cross-meta comparison | feature | — | 5a49aa2 |
| epic-deck-prep-arc-dimir-boards | Dimir Tempo sideboard refresh — two collection-aware boards | feature | — | 5a49aa2 |
| epic-deck-prep-arc-doomsday-tempo | Doomsday Tempo — consensus subarchetype, same per-meta pattern | feature | — | 5a49aa2 |
| epic-deck-prep-arc-loop-reflection | Reflection — codify the loop for all meta decks + the simulation feed  | feature | — | 5a49aa2 |
| epic-deck-prep-arc-meta-decks | Meta decks — 4 lists: Dimir Tempo + whattoplay best-pick, per meta | feature | — | 5a49aa2 |
| epic-subarchetype-resolution | Subarchetype resolution | epic | — | 5a49aa2 |
| epic-subarchetype-resolution-card-winrate | Archetype/variant-conditioned card win-rate | feature | — | 5a49aa2 |
| epic-subarchetype-resolution-discovery | Subarchetype discovery engine | feature | — | 5a49aa2 |
| epic-subarchetype-resolution-discovery-cli | Discovery: staging registry + discover/promote CLI | story | — | 5a49aa2 |
| epic-subarchetype-resolution-discovery-cluster | Discovery: HDBSCAN clustering + two-gate validation + naming | story | — | 5a49aa2 |
| epic-subarchetype-resolution-discovery-repr | Discovery: flex-band representation + reduction | story | — | 5a49aa2 |
| epic-subarchetype-resolution-matchup-cells | Variant-conditioned matchup cells | feature | — | 5a49aa2 |
| feature-archetype-sweep-backtest | Archetype-sweep backtest loop — batch divergence mining for the sidebo | feature | — | 5a49aa2 |
| feature-archetype-sweep-backtest-copy-surfaces | Copy-count + solver pass-through surfaces on the backtest | story | — | 5a49aa2 |
| feature-archetype-sweep-backtest-ilp-determinism | ILP deterministic model construction | story | — | 5a49aa2 |
| feature-archetype-sweep-backtest-sweep-module | Sweep module + CLI — batch driver, clustering/ranking, `advise sweep` | story | — | 5a49aa2 |
| fix-variant-resolution-display-key | Fix: variant resolution keyed on base_archetype silently NULLs color-p | story | — | 5a49aa2 |
| gate-cruft-dead-imports-v030 | Dead noqa-suppressed import in _print_discovery_report + 3 pre-existin | story | — | 5a49aa2 |
| gate-docs-v030-drift | v0.3.0 doc drift: #35 sweep never rolled forward + stale pattern ancho | story | — | 5a49aa2 |
| gate-patterns-v0.3.0 | Patterns extracted for v0.3.0 | story | — | 5a49aa2 |

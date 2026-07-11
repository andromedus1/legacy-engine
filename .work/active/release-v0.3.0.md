---
id: release-v0.3.0
kind: release
stage: quality-gate
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

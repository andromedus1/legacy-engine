---
id: gate-patterns-v0.3.0
kind: story
stage: done
tags: [patterns]
parent: null
depends_on: []
release_binding: v0.3.0
gate_origin: patterns
created: 2026-07-11
updated: 2026-07-11
---

# Patterns extracted for v0.3.0

## New patterns codified
- `opt-in-analytics-overlay` — caller-intent-gated richer computation; off path is the literal
  identity, proven by a pinned full-body golden (5 occurrences; distinct from gated-additive's
  data-presence gate)
- `freshness-stripped-cli-body-golden` — pin CLI default bodies after stripping the freshness
  block (3 sites; the enforcement half of the overlay pattern)

## Inconsistencies flagged (fixed inline with gate-docs drain, no refactor stories needed)
- audit-echo count 59→94 + 2 shifted anchors; advisory-window-block 2 shifted anchors, count ~15,
  "every" scope claim tightened (sweep/discover/cards family deliberately uses
  _latest_regime_window), conformer list corrected. All doc-drift, no code divergence.

## Pattern files written
- .agents/skills/patterns/opt-in-analytics-overlay.md
- .agents/skills/patterns/freshness-stripped-cli-body-golden.md
- .claude/rules/patterns.md (digest: 2 new entries + corrected counts)

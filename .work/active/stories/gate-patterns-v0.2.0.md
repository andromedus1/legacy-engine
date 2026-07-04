---
id: gate-patterns-v0.2.0
kind: story
stage: done
tags: [patterns]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: patterns
created: 2026-07-04
updated: 2026-07-04
---

# Patterns extracted for v0.2.0

## New patterns codified
- `hybrid-derived-curated-registry` — derived long tail + curated overrides merged via a named precedence function (3 occurrences)
- `divergence-as-diagnostic-surface` — disagreement between two signals as a typed first-class output with tier annotation (5 sites)
- `closed-vocabulary-fail-fast-token` — frozenset allow-set + fail-fast membership check for enum-like curated tokens (3 vocabularies, 4 sites)

## Refuted candidates (recorded honestly)
None-gated multiplier step (implementation shape of existing gated-additive-augmentation);
closed-form Beta/Dirichlet marginal (2 sites only); xfail-with-reason (1 site). Test-side
counts-vs-share fixtures + would-fail-if-buggy solver tests noted as conventions, not promoted.

## Inconsistencies flagged (refactor stories, next release)
- `neutralized_by` capability vocabulary unenforced at load (linchpins.py:179-185) → gate-patterns-fix-neutralized-by-vocab
- `maindeck_coverage` truthiness gate diverges from the `is not None` gate convention (sideboard.py:1842) → gate-patterns-fix-gate-predicate-style

## Pattern files written
- .agents/skills/patterns/{hybrid-derived-curated-registry,divergence-as-diagnostic-surface,closed-vocabulary-fail-fast-token}.md
- .agents/skills/patterns/SKILL.md (index updated)
- .claude/rules/patterns.md (hook digest updated)
- .agents/skills/patterns/advisory-window-resolution-block.md (stale cli.py anchors fixed: 2191→2529, 3053→3666, ~13→~14 commands)

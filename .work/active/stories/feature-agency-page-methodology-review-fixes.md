---
id: feature-agency-page-methodology-review-fixes
kind: story
stage: implementing
tags: [analytics, advisory, honesty, bug, tests, docs, accessibility]
parent: feature-agency-page-methodology
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close agency-methodology review findings

Implement the receiver-confirmed findings from the feature's one standard review pass without
changing the pinned methodology or gated authority.

## Acceptance criteria

- [ ] On initial load, `_interactiveN` and P(best) display/sort semantics match the generated
      `ground_n`; changing the control still marks generated-gate evidence stale.
- [ ] Canonical grounding, grounding-path planning, and browser replay share one documented
      deterministic top-k ordering for equal field shares.
- [ ] Archetype and camp detail diagnostics have keyboard-operable disclosure controls with
      `aria-expanded` and `aria-controls` state kept in sync.
- [ ] The runbook gives the posterior soft-min equation and exact seed, draw count, temperature,
      precision scale, and unresolved-prior strength used for replay.
- [ ] Executed JS/behavioral and Python regressions cover the default state, tie case, and disclosure
      state; focused and full repository suites are green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.

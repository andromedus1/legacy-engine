---
id: feature-ranking-honesty-guards-review-fixes
kind: story
stage: implementing
tags: [advisory, analytics, honesty, bug, tests, docs]
parent: feature-ranking-honesty-guards
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close ranking-honesty review findings

Implement the receiver-confirmed findings from the feature's one standard review pass without
changing score policy or widening the feature scope.

## Acceptance criteria

- [ ] A custom `current_regime_n` with any missing row count never produces an exact denominator;
      complete counts remain exact and the old synthetic-one fallback remains only for non-currency
      Dirichlet behavior.
- [ ] When interactive `ground_n` differs from the generated gate, evidence display/grouping is
      recomputed from the interactive row or explicitly labeled/disabled as generated-gate state;
      behavior-level regression coverage prevents contradictory percentages/strata.
- [ ] Inactive/eligible classification uses raw count/share before rounding and distinguishes exact
      zero from a positive share below `0.00005`.
- [ ] CLI help, architecture/current runbook assertions, and relevant spec text describe custom
      currency syntax, count completeness, field-window independence, evidence strata, and all
      `n/a`/exclusion reasons.
- [ ] The knowledge index is regenerated through its owning command, not hand-edited.
- [ ] Focused regressions and the full repository suite are green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.

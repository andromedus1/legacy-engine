---
id: feature-ranking-honesty-guards-review-fixes
kind: story
stage: done
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

## Implementation notes

- Custom currency rejects partial per-row counts while preserving synthetic-one counts solely for
  the pre-existing non-currency Dirichlet fallback. Complete per-row counts and `# effective_n`
  remain exact bases.
- Ranking candidacy now consumes unrounded current presence. Interactive sample-gate changes label
  evidence as generated-gate state and disable generated-stratum grouping until the gate returns.
- CLI help, SPEC, ARCHITECTURE, and the Best Call runbook now state custom syntax/completeness,
  independent field/matchup windows, all evidence strata, and `n/a` exclusion reasons.
- The knowledge-index skill initially found four pre-existing schema errors. Minimal body-grounded
  metadata repair (`70f6c59`) allowed normal linted regeneration with 0 errors and 11 existing
  warnings; `--no-lint` was not used.
- Verification: focused review suite 238 passed; full repository suite 3644 passed, 1 skipped.
- Design deviations: none. Ranking scores, thresholds, source ordering, and Monte Carlo policy are
  unchanged.

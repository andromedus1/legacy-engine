---
id: feature-ranking-measurement-integrity-review-fixes
kind: story
stage: done
tags: [analytics, advisory, honesty, bug, tests]
parent: feature-ranking-measurement-integrity
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close ranking-measurement review findings

Implement the receiver-confirmed findings from the feature's one standard review pass without
changing ranking policy beyond the accepted design.

## Acceptance criteria

- [ ] Python and browser recomputation consume one canonical serialized cell projection; awkward
      shares/rates cannot pass parity while changing the same-threshold displayed result.
- [ ] Era and fallback candidates serialize their own concentration evidence, and interactive
      source changes select or clear the warning with the numeric source.
- [ ] Every rendered row states both `n>=10` and display-grade opponent counts, including an
      unobserved-floor row.
- [ ] Selected ranking sources carry pair-window provenance, ranking comparison sites use the
      shared clamp contract, and invalid provenance makes the headline ineligible with a reason.
- [ ] Strict-common diagnostics separately label contributing and display-grade coverage and show
      the exact common start even when the estimate is unavailable.
- [ ] Focused regressions cover each finding; the integrated feature and full repository suites are
      green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.

## Implementation notes

- The rounded typed ledger is now the canonical serialized cell projection used by Python row
  reconciliation and browser source selection; awkward share/rate regression coverage proves
  same-threshold idempotence.
- Era and fallback candidates carry their own concentration evidence and validated `PairWindow`;
  interactive selection moves or clears the warning with the selected numeric source, and invalid
  provenance suppresses headline fields with a reason.
- Floor audit output always states n>=10 and display-grade counts, including the unobserved-floor
  warning. Strict-common diagnostics separately report contributing/display-grade coverage and
  retain the exact start for null estimates.
- Focused verification: 517 passed across the ranking, refresh, field, matchup, and era-contract
  suites. Full verification: `uv run --no-sync python -m pytest -q` — 3638 passed, 1 skipped.
- Design deviations: none. No ranking policy, thresholds, source order, or estimator blending
  changed.

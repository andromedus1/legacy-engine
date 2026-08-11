---
id: feature-decision-data-currency-review-fixes
kind: story
stage: implementing
tags: [ingestion, infra, analytics, bug, tests]
parent: feature-decision-data-currency
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close decision-data currency review findings

Implement the receiver-confirmed findings from the feature's one standard review pass without
expanding the refresh scope or mutating raw provider data.

## Acceptance criteria

- [ ] Manifest-present plus release-scan failure keeps last-good aliases and marks the coverage
      report degraded with a reason naming currency uncertainty.
- [ ] Ranking generation uses a same-directory temporary file and atomic replacement; injected
      write failure leaves an existing ranking output byte-identical.
- [ ] B&R audit data is independent of source-refresh success and never labels `unknown` as
      operator-confirmed.
- [ ] Empty arrays, top-level error objects, missing required provenance, and implausibly incomplete
      all-cards candidates are rejected before last-good download or alias-state replacement.
- [ ] Focused regressions cover each failure path; the integrated feature and full repository suites
      are green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.

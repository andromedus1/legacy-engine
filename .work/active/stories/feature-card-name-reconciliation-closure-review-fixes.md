---
id: feature-card-name-reconciliation-closure-review-fixes
kind: story
stage: done
tags: [ingestion, data-quality, benchmark, bug, tests]
parent: feature-card-name-reconciliation-closure
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Close card-name reconciliation review findings

Implement the receiver-confirmed blocker and connected important findings from the feature's one
standard review pass without weakening the frozen benchmark or raw-provider authority boundaries.

## Acceptance criteria

- [x] Missing provider provenance cannot satisfy a provider-scoped serialization rule, including
      when the same observed spelling also has supported-provider rows.
- [x] A malformed benchmark schedule is rejected before reconciliation can mutate derived card
      names.
- [x] Typed-rule evidence and unresolved-gap provider/event provenance remain visible in audit
      output.
- [x] The package registry fails fast when malformed and rejects duplicate prefixes within one rule.
- [x] Focused boundary regressions and the full repository suite are green.

## Review closure contract

This is the named fix set for a `standard`-weight review. Green implementation verification returns
the parent feature directly to `done`; do not run a second independent review pass.

## Implementation notes

- Preserved missing tournament-source provenance as an explicit provider-set member, so a spelling
  observed under both MTGmelee and a null/missing source cannot use an MTGmelee-only rule.
- Moved frozen-schedule parsing ahead of the database connection and reconciliation; malformed input
  now proves byte-for-byte derived names remain untouched.
- Added typed-rule evidence to resolution records and verbose audits, plus deterministic JSON gap
  lines carrying provider, event URI, first date, row, and deck evidence.
- Package registry import now fails fast on malformed source-of-truth data and rejects duplicate
  prefixes both within and across typed rules.
- Focused reconciliation/coverage/benchmark tests: `34 passed`. Full repository:
  `3823 passed, 1 skipped in 216.05s`. Ruff, compile, diff, and linted knowledge-index checks are
  green; the index retains 11 standing warnings and 0 errors.
- No protocol, source corpus, estimator, production ranking, or benchmark artifact was changed or
  launched. The fresh-copy gate remains honestly closed at 60 rows / 53 planned-cutoff names plus
  2 rows / 2 post-last-cutoff names.

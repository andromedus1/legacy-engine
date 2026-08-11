---
id: feature-ranking-future-only-benchmark-review-fixes
kind: story
stage: done
tags: [analytics, advisory, testing, honesty, bug, docs]
parent: feature-ranking-future-only-benchmark
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close future-only benchmark review findings

Implement the receiver-confirmed findings from the feature's one standard review pass. The
benchmark remains non-authoritative until this exact fix set verifies green.

## Acceptance criteria

- [x] B&R boundary folds either freeze from a defined non-empty pre-cutoff evidence horizon or carry
      an explicit not-evaluable reason while a valid post-boundary origin supports multi-regime runs.
- [x] Retrospective held-out classification is bound to frozen parent-taxonomy identity and rejects
      post-freeze relabeling; contemporaneous taxonomy identity remains strict.
- [x] The preregistration artifact/hash contains the planned fold schedule and as-of B&R ledger
      identity; freeze/evaluate/run consume that frozen plan rather than mutable globals/DB state.
- [x] Held-out extraction emits a classified deck/field-mass ledger and the 80% claim gate uses that
      denominator independently of match activity.
- [x] Regret includes the declared structural mirror utility, uses event-block oracle uncertainty,
      names practical-tie/unstable/insufficient-support censoring, and aggregate claims require the
      preregistered stable-regret evidence rather than point regret alone.
- [x] Markdown/JSON expose all promised proper-score, calibration, coverage, rank/top-k/regret,
      uncertainty, exclusion, player, external, and censor evidence.
- [x] External snapshots validate declared taxonomy and report missing/common-case coverage against
      the full eligible case set.
- [x] Freeze/run refuse to overwrite a different artifact/checksum at an existing deterministic
      path while allowing byte-identical idempotent replay.
- [x] Hermetic regressions reproduce every review probe; focused and full repository verification
      are green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.

## Implementation notes

- Execution capability: inherited frontier implementation worker at high effort because this repair
  changes the statistical evidence contract, temporal immutability, and claim gates together.
- Review weight: `standard`, inherited from the completed parent review. This is the named fix set;
  no second independent review pass was run.
- Files changed: benchmark contracts/evaluator, DuckDB workflow adapter, benchmark CLI, three
  behavioral test modules, the ranking runbook, SPEC/ARCHITECTURE, and generated knowledge indexes.
- Tests added: hermetic regressions cover frozen fold/B&R identity, boundary-origin field evidence,
  retrospective relabel/rule drift, deck-mass coverage and its evaluation hash, structural-mirror
  regret censoring, external taxonomy/coverage, complete report evidence, and immutable idempotent
  replay. A new constant-probability calibration probe also protects the honest-null path.
- Simplification: one protocol object owns plan identity; one held-out artifact owns separate match
  and deck ledgers; canonical artifact writers share the refuse-different/allow-identical contract.
- Discrepancies from design: the B&R-boundary policy uses the design-permitted fixed trailing 28-day
  pre-cutoff field horizon and records it as degraded evidence rather than introducing an empty-fold
  prediction schema. Retrospective replay binds to and reuses the frozen package parent-rule hash.
- Verification: focused benchmark suite 22 passed; broader ranking/matchup/era suite exited green;
  full repository suite 3,692 passed, 1 skipped in 193.74s; focused Ruff, compilation, and diff
  checks passed. Knowledge-index regeneration: 0 errors, 11 pre-existing warnings. Mandatory fresh
  documentation/code re-audit: 0 Critical/High/Medium/Low after closing its deck-ledger hash finding.
- Adjacent issues parked: none.

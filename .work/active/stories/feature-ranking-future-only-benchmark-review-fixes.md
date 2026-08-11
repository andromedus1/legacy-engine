---
id: feature-ranking-future-only-benchmark-review-fixes
kind: story
stage: implementing
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

- [ ] B&R boundary folds either freeze from a defined non-empty pre-cutoff evidence horizon or carry
      an explicit not-evaluable reason while a valid post-boundary origin supports multi-regime runs.
- [ ] Retrospective held-out classification is bound to frozen parent-taxonomy identity and rejects
      post-freeze relabeling; contemporaneous taxonomy identity remains strict.
- [ ] The preregistration artifact/hash contains the planned fold schedule and as-of B&R ledger
      identity; freeze/evaluate/run consume that frozen plan rather than mutable globals/DB state.
- [ ] Held-out extraction emits a classified deck/field-mass ledger and the 80% claim gate uses that
      denominator independently of match activity.
- [ ] Regret includes the declared structural mirror utility, uses event-block oracle uncertainty,
      names practical-tie/unstable/insufficient-support censoring, and aggregate claims require the
      preregistered stable-regret evidence rather than point regret alone.
- [ ] Markdown/JSON expose all promised proper-score, calibration, coverage, rank/top-k/regret,
      uncertainty, exclusion, player, external, and censor evidence.
- [ ] External snapshots validate declared taxonomy and report missing/common-case coverage against
      the full eligible case set.
- [ ] Freeze/run refuse to overwrite a different artifact/checksum at an existing deterministic
      path while allowing byte-identical idempotent replay.
- [ ] Hermetic regressions reproduce every review probe; focused and full repository verification
      are green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.

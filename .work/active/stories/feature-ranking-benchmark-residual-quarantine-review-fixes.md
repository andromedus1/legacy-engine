---
id: feature-ranking-benchmark-residual-quarantine-review-fixes
kind: story
stage: done
tags: [analytics, advisory, testing, data-quality, bug]
parent: feature-ranking-benchmark-residual-quarantine
depends_on: [feature-ranking-benchmark-residual-quarantine-artifact-run]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Close residual-quarantine standard-review findings

## Brief

Implement and verify the receiver-confirmed blocker set from the feature's single standard review:
outcome-invariant ledger identity, conservative blank/ambiguous identity handling, exact-time claim
and summary invariants, frozen-v1 artifact compatibility, workflow-level policy/ledger binding, and
complete Markdown evidence. The invalid in-flight v2 replay was stopped; restart it in a new ignored
artifact directory only after corrected code and tests are committed.

## Acceptance criteria

- [ ] Training result/standing/stored-label and held-out result/classification mutations leave the
  quarantine selection and digest identical.
- [ ] A corrupt deck with blank or ambiguous identity cannot retain an affected round or pass with a
  falsely zero round fraction.
- [ ] Same-cutoff-day registration is posthoc; no parsed summary can exceed its claim ceiling.
- [ ] Exact legacy v1 protocol, snapshot, prediction, evaluation, summary, and page identities remain
  compatible when quarantine fields are at defaults.
- [ ] Freeze/evaluate reject absent, mismatched, failed-ceiling, tampered, or retained-corpus-incoherent
  quarantine evidence even through direct typed workflow calls.
- [ ] Markdown carries the exact exclusion evidence promised by the runbook.
- [ ] Focused and full repository verification are green; corrected v2 artifacts never overwrite or
  reuse the invalid partial attempt.

## Implementation notes
- Execution capability: inline standard implementation of the receiver-confirmed review blockers.
- Review weight: standard review already completed; no second review commissioned.
- Files changed: `src/legacy_engine/advisory/ranking_benchmark.py`, `src/legacy_engine/workflows/ranking_benchmark.py`, `src/legacy_engine/cli.py`, focused benchmark tests, and this item.
- Tests added/removed: adversarial outcome/label mutation, blank/duplicate identity, exact registration, summary ceiling, v1 hash, manifest/ledger/retained-corpus, held-out binding, and Markdown evidence tests; none removed.
- Simplification: ledger digest explicitly excludes the separate retained-corpus hash, keeping identity outcome-blind while preserving corpus coherence checks.
- Discrepancies from design: none; direct CLI evaluation now requires the sibling immutable manifest and snapshot so the workflow cannot silently skip evidence validation.
- Adjacent issues parked: none.
- Verification: 36 focused tests passed; full suite passed with `PYTHONPATH=.` (3,835 passed, 1 skipped); changed advisory/workflow/test Ruff passed; compileall passed. Default full-suite invocation remains unable to import `tests` without repository-root `PYTHONPATH`.

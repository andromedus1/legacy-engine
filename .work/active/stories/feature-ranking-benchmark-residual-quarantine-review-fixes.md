---
id: feature-ranking-benchmark-residual-quarantine-review-fixes
kind: story
stage: implementing
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

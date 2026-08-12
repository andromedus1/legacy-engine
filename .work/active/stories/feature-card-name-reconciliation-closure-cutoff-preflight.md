---
id: feature-card-name-reconciliation-closure-cutoff-preflight
kind: story
stage: implementing
tags: [ingestion, data-quality, benchmark]
parent: feature-card-name-reconciliation-closure
depends_on: [feature-card-name-reconciliation-closure-provider-serialization]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Report all benchmark-relevant card metadata gaps

## Brief

Implement Unit 2 from the parent design: a typed cutoff-aware residual ledger and explicit-DB CLI
preflight that prints every cohort and fails only for gaps entering a planned training cutoff.

## Acceptance criteria

- The parent Unit 2 acceptance criteria are green.
- Protocol parsing and date-boundary behavior have hermetic regressions.
- Output is complete, machine-scannable, and retains fail-closed gap names.

---
id: epic-recurrent-stable-era-evidence-best-call-integration-current-diagnostics
kind: story
stage: implementing
tags: [analytics, advisory, ui, testing]
parent: epic-recurrent-stable-era-evidence-best-call-integration
depends_on: [epic-recurrent-stable-era-evidence-best-call-integration-publication-contract]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Publish current-target evidence diagnostics

## Brief

Attach the typed evidence projection to the current Best Call artifact and render it through the
existing row disclosures without changing ranking, recommendation, field, plan, or control
authority.

## Implementation

Implement Unit 2, **Publish current-target diagnostics in the existing report**, from the parent
feature. Reuse the current table/disclosure/audit interaction grammar. Do not expose a challenger
winner, turn refused all-case output into a magnitude, or let browser controls recompute frozen
diagnostics.

## Acceptance

Satisfy every Unit 2 acceptance criterion in the parent feature: exact authority parity, visible
diagnostic/decomposition/component/concentration/confidence/refusal semantics, camp treatment,
explicit run selection, legacy no-request behavior, and honest degraded output.

## Tests

Extend `tests/test_refresh_best_call_ranking.py` with generator, blob, DOM, and executed-JS cases for
all direct views, all six challengers, every service state, camp borrowing, thin/concentrated data,
hostile content, fixed registry order, unchanged authority bytes, and output preservation on a bad
requested run.

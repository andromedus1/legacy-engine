---
id: epic-recurrent-stable-era-evidence-amplification-contract
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-amplification
depends_on: [epic-recurrent-stable-era-evidence-interval-consumption]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Canonical amplification corpus and challenger contract

## Brief

Implement Unit 1 from the parent feature: consume the interval authority's canonical selected rows,
orient every physical outcome once, freeze structure/profile identities, preserve direct baseline
bytes, and define shared decomposition, support, concentration, imputation, and refusal types.

## Implementation

See `epic-recurrent-stable-era-evidence-amplification` Unit 1 for exact interfaces, notes, and
acceptance criteria. Amplification must block on an aggregate-only interval handoff and must never
query or infer a parallel eligible corpus.

## Acceptance

- One exact gap-preserving corpus, physical orientation, clock, and baseline feeds every candidate.
- Current/history/borrowed sets and ablations are auditable without fabricated additive percentages.
- Invalid profile authority, outcome-bearing structure, duplicate rows, or missing provenance fails
  before fitting.

## Tests

Run focused corpus/profile/property tests, interval contract tests, Ruff on touched files, and
compileall as specified by the parent feature.

## Implementation evidence

- Added `analytics.amplification.models`, `corpus`, and `profile` plus the checked-in diagnostic
  profile. `build_interval_evidence_corpus` consumes only `IntervalAdaptiveMatrix.selected_outcomes`,
  rejects duplicate/non-canonical physical rows, and derives current/history origins by exact ids.
- Baseline cells are copied and serialized digests are bound before challenger execution; no aggregate
  reconstruction or parallel database selection exists.
- Verification: `.venv/bin/python` profile load, Ruff, and compileall pass.

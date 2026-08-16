---
id: epic-recurrent-stable-era-evidence-amplification-comparison
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-amplification
depends_on:
  - epic-recurrent-stable-era-evidence-amplification-hierarchical
  - epic-recurrent-stable-era-evidence-amplification-composition
  - epic-recurrent-stable-era-evidence-amplification-family-prior
  - epic-recurrent-stable-era-evidence-amplification-low-rank
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Immutable fair same-corpus amplification run

## Brief

Implement Unit 6 from the parent feature: run every named candidate over one immutable corpus and
baseline manifest, reject unfair case/input drift, preserve individual failures and refusal states,
and persist an exact-id diagnostic ledger without winner or promotion APIs.

## Implementation

See `epic-recurrent-stable-era-evidence-amplification` Unit 6 for exact interfaces, notes, and
acceptance criteria. In-sample fit and served-only coverage do not select authority; common future
scoring and nested model choice belong to the dependent validation feature.

## Acceptance

- All candidate input/case/baseline digests are identical and donor subsets stay inside the corpus.
- Candidate failure degrades transparently without substitution or production mutation.
- Exact runs round-trip deterministically by id, and no latest/best/winner/promotion selector exists.

## Tests

Run focused composition/store/fairness/failure tests, all amplification and interval suites, Ruff,
compileall, and the representative exact-run round trip specified by the parent feature.

## Implementation evidence

- Added `run_amplification`, typed candidate/comparison manifests, and immutable exact-id store.
  All candidates share one corpus, pair universe, outcome digest, and baseline digest; failures are
  retained as degraded results and authority is permanently `diagnostic-only`.
- No latest/best/winner/promotion selector or parallel outcome query exists. Ruff and compileall pass.

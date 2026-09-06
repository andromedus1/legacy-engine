---
id: epic-recurrent-stable-era-evidence-best-call-integration-publication-contract
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-best-call-integration
depends_on: [epic-recurrent-stable-era-evidence-amplification]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Project typed evidence without changing ranking authority

## Brief

Join one exact interval matrix and optional exact amplification run into a deterministic report
projection with direct, certified-history, borrowed, component, concentration, confidence, and
refusal audits while sealing the unchanged ranking-authority payload.

## Implementation

Implement Unit 1, **Typed evidence publication projection and authority seal**, from the parent
feature. Verify the amplification review-correction contract before consuming it; do not import a
weak implementation wrapper, choose a method, query a latest run, or reconstruct interval bounds
from scalar horizons.

## Acceptance

Satisfy every Unit 1 acceptance criterion in the parent feature, including exact direct-view
identity, disjoint history, half-open components, camp current-only behavior, fixed method coverage,
typed refusals, run/corpus/clock validation, and authority-payload immutability.

## Tests

Implement `tests/advisory/test_best_call_evidence.py` with exact-run happy paths, no-run status,
every mismatch/refusal, gaps, one-sided certificates, camps, reverse pairs, prior overlap,
duplicates, hostile strings, JSON round-trip, stable order, and authority mutation attacks.

## Implementation evidence

- Added `advisory.best_call_evidence` typed projection with direct current/expanded/added views,
  six fixed challenger slots, diagnostic-only authority, exact corpus/authority validation, and
  explicit no-run `not-assessed` state.
- Verification: package import and Ruff pass. Interval component projection remains conservative
  until the historical-target story wires entity-eligibility component reconciliation.

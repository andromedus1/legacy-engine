---
id: feature-agency-page-methodology-kernel
kind: story
stage: done
tags: [analytics, advisory]
parent: feature-agency-page-methodology
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Typed methodology projections and posterior lean

## Brief

Extend the package-owned ranking measurement contract with the four predeclared methodology
projections, a seeded precision-weighted posterior smooth floor, and honest cross-row rank spans.
Existing gated measurement output remains byte-for-byte authoritative.

## Implementation

Implement Unit 1 in the parent feature's `## Implementation Units` section. This is the trickiest
unit and must land before any report integration.

## Implementation notes

- Execution capability: inherited frontier model at high effort; posterior math and rank eligibility
  directly affect the headline ranking's diagnostic evidence.
- Review weight: standard, inherited from the autopilot caller.
- Files changed: `src/legacy_engine/advisory/ranking_measurement.py` and
  `tests/test_ranking_measurement.py`.
- Tests added/removed: added source/rate-policy truth tables, canonical gated parity, seeded posterior
  bounds and gate independence, explicit unresolved prior mass, invalid configuration, competition
  ties, and complete-only stability spans; no tests removed.
- Simplification: extracted one projection summarizer used by the canonical row and methodology
  variants; retained one selected-cell ledger and one fixed four-variant registry.
- Discrepancies from design: `VariantRowMeasurement` also carries `valid` and `reason` so invalid
  pair-window provenance degrades explicitly instead of producing a variant score.
- Adjacent issues parked: none.
- Verification: `tests/test_ranking_measurement.py` — 15 passed; combined ranking generator and
  positioning regressions — 124 passed.

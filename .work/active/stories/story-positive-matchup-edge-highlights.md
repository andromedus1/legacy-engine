---
id: story-positive-matchup-edge-highlights
kind: story
stage: implementing
tags: [analytics, ui]
parent: null
depends_on: [story-fix-blowouts-use-raw-win-rate]
release_binding: null
gate_origin: null
created: 2026-08-02
updated: 2026-08-02
---

# Add positive matchup edge highlights to Best Call ledgers

## Brief

Extend each archetype and camp matchup dropdown with two measured, raw-WR positive tiers symmetric
to the loss-side blowout tiers: **Edge** for 55–60% and **Dominant** for greater than 60%. Give each
tier its own positive visual treatment and chip, and extend the inline legend and methodology copy
so all four bands are immediately understandable.

## Acceptance criteria

- Measured rows with raw WR from 55% through 60%, inclusive at 60%, render as `edge`.
- Measured rows with raw WR greater than 60% render as `dominant`.
- The two positive tiers never affect aggregate blowout counts, agency, adjusted WR, floor,
  coverage, grounding, or ranking.
- Unmeasured and family-lean rows do not receive these highlights.
- The ledger legend and methodology explain all four raw-WR bands.
- The production Best Call HTML is regenerated and verified.

## Design decisions

- **Names**: `Edge` (55–60%) and `Dominant` (>60%) — concise, readable, and less awkward than
  “reverse blowout.”
- **Evidence contract**: reuse the existing measured-cell gate and raw observed WR used by the
  restored blowout tiers.
- **UI scope**: minor composition within the approved Best Call ledger; inherit the existing
  page design rather than creating a new mockup.

## Simplification opportunities

Keep classification inline beside the existing loss bands so one mutually exclusive raw-WR ladder
owns all four row treatments; do not introduce a second metric or payload field.

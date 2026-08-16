---
id: epic-recurrent-stable-era-evidence-amplification-composition
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-amplification
depends_on: [epic-recurrent-stable-era-evidence-amplification-contract]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Outcome-blind composition-kernel borrowing challenger

## Brief

Implement Unit 3 from the parent feature: freeze outcome-free composition vectors, select both-axis
similarity donors without target outcomes, borrow only exact donor-pair interval rows, and expose
donor, event, component, and sensitivity concentration.

## Implementation

See `epic-recurrent-stable-era-evidence-amplification` Unit 3 for exact interfaces, notes, and
acceptance criteria. Donor identities/weights are outcome-blind, target rows are excluded from the
prior, and missing or dominated structure refuses rather than fabricating a flat answer.

## Acceptance

- Target outcomes cannot alter donor structure, and reverse predictions remain complementary.
- Donor rows obey their own interval gaps/clocks and never overlap target direct evidence.
- Unsupported, concentrated, or composition-sensitive borrowing is typed and non-authoritative.

## Tests

Run focused composition/donor, leakage, gap, reversal, concentration, and missing-structure tests
plus the shared amplification contract suite.

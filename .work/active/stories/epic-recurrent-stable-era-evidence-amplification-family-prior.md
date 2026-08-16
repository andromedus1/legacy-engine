---
id: epic-recurrent-stable-era-evidence-amplification-family-prior
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-amplification
depends_on: [epic-recurrent-stable-era-evidence-amplification-contract]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Multi-resolution strategic-family prior challenger

## Brief

Implement Unit 4 from the parent feature: adapt the fixed composition-family hierarchy to exact
interval rows, walk a visible fine-to-coarse leave-out ladder, and gate every rung on support,
concentration, heterogeneity, and member conflict.

## Implementation

See `epic-recurrent-stable-era-evidence-amplification` Unit 4 for exact interfaces, notes, and
acceptance criteria. Frozen active members contribute their own outcomes in this challenger; camps
inherit only structural family relation, never parent history or certificate authority.

## Acceptance

- Ladder order and every skipped/used rung are explicit and deterministic.
- Target evidence is excluded from priors, and family/member conflicts can falsify borrowing.
- No admissible rung falls back to unchanged direct evidence with a named refusal.

## Tests

Run focused family ladder, assigned-member, camp, leave-out, heterogeneity, and concentration tests
plus existing superarchetype chain coverage.

## Implementation evidence

- Added typed family ladder rung/fit contracts and a diagnostic-only adapter over canonical rows.
  Postdated structure snapshots fail fast; absent frozen family support is refused explicitly.
- Ruff and compile checks pass.

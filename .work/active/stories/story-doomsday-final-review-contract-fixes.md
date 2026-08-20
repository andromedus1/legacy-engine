---
id: story-doomsday-final-review-contract-fixes
kind: story
stage: implementing
tags: [analytics, testing]
parent: null
depends_on:
  - research-handoff-doomsday-splash-variants-5
release_binding: null
gate_origin: null
research_origin: doomsday-splash-variants
created: 2026-08-20
updated: 2026-08-20
---

# Close aggregate Doomsday autopilot review findings

The single standard-weight final completion review found that list versions were not bound to a
registry hash and that semantically invalid matches could count toward the preregistered threshold.
It also found boundary-state gaps, missing matchup-block deltas, and one alternate-deck test that
depended on ignored local data.

## Acceptance

- Manifest-backed list versions preserve old hashes explicitly and rows bind id + version + hash.
- Only coherent, ordered, single-pilot/date/version completed matches count toward the threshold.
- Conditional fields reject semantically impossible sentinel, mulligan, and boarding values.
- Output includes per-matchup-block paired deltas with denominators.
- Alternate card/source validation is hermetic in a clean checkout.
- Focused, all-Doomsday, and full repository verification are green.

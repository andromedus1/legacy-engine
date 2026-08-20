---
id: story-doomsday-final-review-contract-fixes
kind: story
stage: done
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

## Implementation notes

- Added an append-only `versions` registry to every canonical candidate. The validator now resolves
  `list_id + list_version` to its registered hash instead of accepting any label beside the current
  artifact hash.
- Completed-match validation now holds pilot, date, version, and hash constant; requires pre-board
  rows before post-board rows; requires the single terminal result on the final post-board row; and
  rejects a draw after either side has already recorded two game wins.
- Closed sentinel, London-mulligan, splash-observation, and positive boarding-count boundaries.
- Added per-matchup-block paired deltas while retaining the candidate-level descriptive aggregate.
- Replaced the optional ignored-DuckDB card check with six tracked source 75s, explicit Oracle-name
  normalization, and exact application of the two Fantasticar reconstruction ledgers.

## Verification

- `pytest -q tests/test_doomsday_variant_results.py tests/test_doomsday_alternate_variants.py` —
  57 passed.
- All five Doomsday test modules — 86 passed.
- `git diff --check` — clean.
- Full repository suite — 4,090 passed, 1 unrelated existing skip.

## Review

Bounded standalone-story review: **approved**. The implementation closes every finding from the
single final aggregate autopilot review without widening the deck corpus or changing its evidence
postures. The public CSV command accepts the valid fixture, prints both candidate-level and
matchup-block denominators, and remains explicitly descriptive with no ranking. Version history is
append-only in the manifest, invalid matches cannot count as completed, and the alternate source
contract no longer depends on ignored local data. No critical or important issue remains.

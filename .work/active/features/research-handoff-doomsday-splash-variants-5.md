---
id: research-handoff-doomsday-splash-variants-5
kind: feature
stage: review
tags: [advisory, analytics]
parent: null
depends_on:
  - research-handoff-doomsday-splash-variants-1
  - research-handoff-doomsday-splash-variants-2
  - research-handoff-doomsday-splash-variants-3
  - research-handoff-doomsday-splash-variants-4
release_binding: null
gate_origin: null
research_origin: doomsday-splash-variants
created: 2026-08-20
updated: 2026-08-20
---

# Define the Doomsday variant comparison program

Define a repeatable playtest and evidence-capture protocol across the candidate 75s. Keep opening-
hand decisions, actual combo turns, splash-mana effects, Wasteland exposure, boarding changes,
protection-card relevance, and alternate-plan outcomes distinct. Use the results to decide which
directions should later converge into an interchangeable-sideboard series.

## Research grounding

**Source**: `.research/analysis/campaigns/doomsday-splash-variants/parent.md` (slug:
`doomsday-splash-variants`)

Published 5-0s and event placements establish viable registrations but do not isolate package
effects; a purpose-built comparison program is required before optimizing a shared maindeck and
rotating sideboards.

## Design

### Decision

Adopt a preregistered, paired-match playtest protocol with a machine-readable game log. A prose-only
guide would be easy to interpret inconsistently; a full analytics subsystem is premature before
real games exist. The middle path is a stable CSV contract, controlled matchup blocks, and a small
offline validator/summarizer that reports descriptive results without claiming causal certainty.

### Files and interfaces

- `decks/doomsday-variants/playtest-protocol.md` defines units (game, pre/post-board pair, match,
  matchup block), randomized play/draw and list order, mulligan/boarding procedure, stopping rules,
  and interpretation limits.
- `decks/doomsday-variants/playtest-log.csv` is a header-only template. Required fields keep opening
  decisions, combo timing, splash mana, Wasteland exposure, boarding, protection relevance, and
  alternate-plan results separate.
- `scripts/doomsday_variant_results.py LOG.csv` validates rows and emits per-list and paired-delta
  descriptive summaries. Invalid enums, missing required fields, unknown list ids, impossible turn
  values, and inconsistent conditional fields fail fast with row-specific errors.
- `decks/doomsday-variants/manifest.json` is extended from the four current registrations to a
  complete playtest registry covering every finished list from features 1–4 (current, dated,
  chassis, and alternate). The JSON remains the list-id authority; the script must derive valid
  ids and deck paths from it rather than maintain a second enumeration. Entries added for
  reconstructed prototypes must retain their evidence posture and may not masquerade as exact
  source registrations.

### Measurement contract

Primary learning measures are keep rate, mulligans, actual combo-turn distribution, game and match
wins, and paired matchup-block delta versus the Dimir control. Diagnostic measures are splash-mana
keep/sequencing effects, color failure, Wasteland exposure and punishment, cards boarded in/out,
protection presented/live/relevant, and alternate-plan deployment/wins. Published finishes remain
context only and are never merged into playtest outcomes.

### Implementation order

1. Define the log schema and adversarial invalid examples first; ambiguity here would contaminate
   every later result.
2. Author the protocol and stopping rule around the schema.
3. Implement the validator and minimal descriptive summary.
4. Validate the empty template and synthetic valid/invalid fixtures; run the broader focused tests.

### Acceptance criteria

- A new tester can identify the experimental unit, list version, opponent archetype/list, play/draw,
  pre/post-board state, and stopping rule without consulting chat history.
- The log records every campaign-requested variable in a distinct field and supports explicit
  `not_seen`/`not_applicable` states instead of silent blanks.
- List order and play/draw are balanced within matchup blocks; each experimental list is paired
  against the Dimir control under the same opponent list/version.
- Every parser-valid artifact delivered by features 1–4 is registered, while each unique normalized
  75 has exactly one stable experimental id, evidence posture, and deck hash. Duplicate artifacts
  must alias the canonical id rather than split denominators.
- Summaries display denominators and remain descriptive; low sample sizes are labeled and no win-
  rate ranking is emitted before the preregistered stopping threshold.
- The validator rejects malformed or internally inconsistent rows and accepts the distributed
  template plus valid fixture.

### Verification

- Unit tests cover enum/schema rejection, conditional consistency, manifest-derived list ids,
  aggregation denominators, paired deltas, and thin-sample labeling.
- Run focused tests, CLI help/smoke invocation, and `git diff --check`.

### Risks

- Pilot learning and matchup-order effects can masquerade as list effects. Mitigation: randomized
  balanced blocks and explicit pilot/date fields.
- Card substitutions can silently change a list mid-program. Mitigation: list-version and deck-hash
  fields; changed hashes begin a new version.
- Sparse data invites premature conclusions. Mitigation: preregistered threshold, denominators, and
  descriptive-only output below it.

## Implementation notes
- Execution capability: GPT-5.6 Luna high; cohesive registry, protocol, validator, and descriptive CLI implementation.
- Review weight: standard (default).
- Files changed: `decks/doomsday-variants/manifest.json`; `decks/doomsday-variants/README.md`; `decks/doomsday-variants/playtest-protocol.md`; `decks/doomsday-variants/playtest-log.csv`; `decks/README.md`; `scripts/doomsday_variant_results.py`; `tests/test_doomsday_variant_results.py`; `tests/fixtures/doomsday_variants/playtest-valid.csv`; `tests/test_doomsday_variant_decks.py`.
- Tests added/removed: added manifest completeness, CSV acceptance, enum/conditional rejection, paired-delta, thin-sample, and CLI-contract coverage; adapted the former four-registration contract to validate its current subset while the expanded manifest accounts for all 15 artifacts as 14 unique experimental 75s. Initial Doomsday-focused suite passed (58 tests).
- Simplification: the CLI derives candidate IDs, paths, and hashes directly from the manifest; no second list enumeration or premature ranking layer was introduced.
- Discrepancies from design: the finished corpus exposed that the Battlegrounds Esper and
  Bilbo/Tamiyo files are identical. The manifest therefore owns 14 unique experimental IDs and one
  explicit artifact alias instead of inventing a fifteenth arm with duplicated denominators.
- Adjacent issues parked: none.

### Standard-review fix verification

- Canonicalized the 15 artifacts into 14 unique experimental 75s plus one explicit alias for the
  duplicate Battlegrounds Esper/Bilbo-Tamiyo registration.
- Bound every log row to the manifest's `deck_sha256`; hardened manifest root, path containment,
  unique hash/path, declared count, evidence-posture, and alias contracts.
- Enforced one candidate plus control per block, globally unique two-row pairs, matched opponent /
  board / play-draw / list-order / pilot conditions, balanced assignments, and coherent completed
  matches with one terminal post-board result.
- Fixed the threshold at 20 completed matches, tightened both directions of conditional-state
  validation, and rendered mulligan plus combo-turn measures with denominators.
- Added adversarial coverage for every review reproduction. Verification: 25 playtest-contract
  tests and 75 integrated Doomsday tests pass; empty-template and valid-fixture CLI smoke pass;
  `git diff --check` is clean.

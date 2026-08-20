---
id: research-handoff-doomsday-splash-variants-2
kind: feature
stage: review
tags: [advisory, generation]
parent: null
depends_on: []
release_binding: null
gate_origin: null
research_origin: doomsday-splash-variants
created: 2026-08-20
updated: 2026-08-20
---

# Reconstruct BUG and refresh Grixis Doomsday

Produce a legal post-Fantasticar pure BUG candidate using the evidenced Veil, Carpet,
Witherbloom Charm, and Abrupt Decay lineage. Separately refresh the dated Grixis Hexing Squelcher,
Pyroblast, and fair-creature configuration against the current field while preserving the
distinction between currency and legality.

## Research grounding

**Source**: `.research/analysis/campaigns/doomsday-splash-variants/parent.md` (slug:
`doomsday-splash-variants`)

Pure BUG has a broad pre-ban lineage but its representative 75 used a now-banned card; Grixis is a
repeatable six-pilot package whose evidence ends in June rather than an illegal configuration.

## Design decisions

- **Autopilot evidence cutoff:** use the completed campaign refresh as the reproducible design
  snapshot: the dispatch records a manual refresh on 2026-08-20 through events dated 2026-08-19.
  The local scheduled-status projection is stale and reports a pending format-monitor action, but
  the campaign explicitly explains that manual refreshes do not terminalize that projection. The
  implementer must run the read-only currency check below and record the database maximum actually
  observed; this feature must not trigger a second network refresh merely to clear the status
  banner.
- **BUG reconstruction:** preserve wakame's July 13 pure-BUG registration except for six disclosed
  slots: replace the four banned Fantasticars with the observed current post-ban `3 Personal Tutor
  + 1 Thassa's Oracle` recovery module, and replace two sideboard Duress with the independently
  observed two-Abrupt-Decay BUG module. The first splice restores legality; the second deliberately
  makes the requested Decay branch testable. Their combination is inferred and must never be called
  a published or proven 75.
- **Grixis refresh:** preserve nevilshute's May 31 registration card-for-card because the attested 75
  is legal after the Fantasticar ban. “Refresh” means rechecking legality, current-corpus adoption,
  and present-field relevance; it does not authorize changing cards merely to make the dated list
  look current. If the read-only cutoff query finds a newer post-ban exact Grixis/Squelcher 75, stop
  and record that implementation discovery in this item before replacing the pinned candidate.
- **Provenance:** every deck file carries `Status`, `Evidence through`, `Observed source`, and
  `Reconstruction` comment headers. The companion workbook separates `observed-current`,
  `observed-historical`, and `inferred-reconstruction` statements. Published finishes establish
  registrations, not package-controlled matchup superiority.
- **Dispatch:** direct-read only. This is a bounded, tightly coupled static-artifact feature; child
  stories and exploratory agents would add handoff cost without independent write ownership.
- **UI and foundations:** no UI surface is introduced, so no mockup is needed. The feature adds
  optional deck-study artifacts and does not invalidate an assertion in VISION, SPEC, ARCHITECTURE,
  or PRINCIPLES; foundation updates are therefore out of scope.

## Architectural choice

Three approaches were considered:

1. **Historical reproductions only.** Preserve the exact July BUG and May Grixis lists. This is the
   clearest historical record, but the BUG list contains four banned Fantasticars and fails the
   request for a playable candidate.
2. **Evidence-ledger composites (selected).** Keep one exact historical anchor per branch, change
   only the slots required by legality or the explicitly requested package, and disclose every
   changed slot beside the resulting 75. This yields playable test instruments while preserving the
   observed-versus-inferred boundary.
3. **Engine-optimized refresh.** Generate or tune both lists against the current field. This would
   imply more precision than the campaign supports: the ranking has no proof-grade grounded rows,
   matchup effects are not isolated, and tuning would confound the splash comparison with a new
   chassis.

Choose option 2. The deck files remain ordinary repository import text, while a small adjacent
workbook owns source/cutoff/reconstruction context. Do not create a generator, a second deck schema,
or a network-dependent update path for two curated candidates.

## Exact deliverables

### BUG 75: `decks/doomsday-variants/dated/bug-veil-carpet-reconstructed.txt`

The maindeck is wakame's attested July 13 BUG 60 minus `4 The Fantasticar`, plus `3 Personal Tutor`
and a second `Thassa's Oracle`. The sideboard is wakame's 15 minus `2 Duress`, plus `2 Abrupt Decay`.
The exact parser-visible contents are:

```text
1 Bayou
4 Brainstorm
1 Cavern of Souls
1 Consider
4 Dark Ritual
3 Daze
4 Doomsday
1 Edge of Autumn
3 Flow State
4 Force of Will
1 Island
1 Lion's Eye Diamond
4 Lotus Petal
4 Misty Rainforest
3 Personal Tutor
4 Polluted Delta
4 Ponder
1 Quantum Riddler
1 Street Wraith
2 Thassa's Oracle
3 Thoughtseize
1 Tropical Island
1 Undercity Sewers
3 Underground Sea
1 Witherbloom Charm

Sideboard
2 Abrupt Decay
3 Carpet of Flowers
1 Consign to Memory
2 Force of Negation
1 Jace, Wielder of Mysteries
2 Surgical Extraction
2 Veil of Summer
2 Witherbloom Charm
```

Required headers classify the July 13 source list, the post-ban Personal Tutor/Oracle replacement,
and the Decay overlay separately. The design intentionally retains Bayou, Tropical Island, and the
main Witherbloom Charm: this is a pure-BUG base-defining candidate, not a sideboard-only green pivot.

### Grixis 75: `decks/doomsday-variants/dated/grixis-squelcher-refresh.txt`

The candidate preserves nevilshute's attested May 31 75 exactly unless the current-corpus check
finds a newer exact post-ban registration:

```text
1 Badlands
1 Bloodstained Mire
4 Brainstorm
1 Cavern of Souls
1 Consider
4 Dark Ritual
3 Daze
4 Doomsday
2 Edge of Autumn
4 Flow State
1 Flusterstorm
4 Force of Will
1 Hexing Squelcher
1 Island
1 Jace, Wielder of Mysteries
1 Lion's Eye Diamond
3 Lotus Petal
4 Polluted Delta
4 Ponder
3 Scalding Tarn
2 Street Wraith
1 Swamp
1 Thassa's Oracle
3 Thoughtseize
1 Undercity Sewers
3 Underground Sea
1 Volcanic Island

Sideboard
4 Barrowgoyf
1 Brazen Borrower
2 Force of Negation
2 Hexing Squelcher
2 Long Goodbye
1 Molten Collapse
2 Pyroblast
1 Sheoldred, the Apocalypse
```

This is `observed-historical` and legal-at-cutoff, not `observed-current`. The workbook must name
that no Squelcher list appeared after June 27 in the campaign snapshot and that the current-field
read is a test rationale, not evidence that any card here is superior in a matchup.

### Provenance workbook: `decks/doomsday-variants/dated/README.md`

This file is the authoritative manifest for these two candidates. For each id it records filename,
status, observed source path and source anchor, evidence date/cutoff, legality snapshot date,
observed package, inferred substitutions, unchanged-card count, and one bounded learning question.
It links the campaign parent and source-direct attestations rather than reproducing research claims
from memory. It does not duplicate full cardlists or claim a matchup ranking.

## Current-snapshot and reconstruction method

1. Read `data/ops/status/decision-refresh.json` with
   `.venv/bin/python scripts/session_ops_status.py` and retain its banner in implementation notes.
   Because the campaign documents a later manual refresh, status staleness is a warning rather than
   authority to perform network mutation.
2. Query `data/legacy.duckdb` read-only for the maximum Doomsday tournament date, post-2026-08-10
   exact BUG signatures, and post-2026-08-10 Hexing Squelcher signatures. Record the query cutoff and
   result in the dated workbook. Do not derive card quality from row counts.
3. Re-read the two source-direct list attestations and their underlying cached tournament JSON:
   `.research/attestation/ddv-packages-list-bug-wakame-preban.md` and
   `.research/attestation/ddv-packages-list-grixis-nevilshute.md`. Extract counts mechanically; do
   not type the historical bases from memory.
4. Apply the BUG substitution ledger as a net-zero transformation: `-4 The Fantasticar`,
   `+3 Personal Tutor`, `+1 Thassa's Oracle`; then `-2 Duress`, `+2 Abrupt Decay` in the sideboard.
   Assert 60/15 immediately after each zone transformation. The observed replacement anchors are
   `.research/attestation/ddv-landscape-current-db.md` (current Personal Tutor branch) and the
   campaign's attested two-Decay BUG lineage; the exact splice remains inferred.
5. Copy the Grixis registration exactly from its cached source, then validate it at the same dated
   snapshot. A zero-current-row result changes the evidence label, not legality. Any newer exact
   post-ban Grixis result is a design-changing discovery and must be documented before substitution.
6. Parse each emitted file with `legacy_engine.models.decklist.parse_decklist`, require exactly 60
   and 15, and run `legacy_engine.ingestion.banlist.validate_deck` with
   `banlist_as_of(date(2026, 8, 20))`. The current ban-list check must also pass; if it differs from
   the pinned snapshot, preserve the failure as a blocker rather than silently editing around it.

## Implementation Units

### Unit 1: Reconstruct and attest the BUG candidate (trickiest unit)

**Files:** `decks/doomsday-variants/dated/bug-veil-carpet-reconstructed.txt`,
`decks/doomsday-variants/dated/README.md`

```python
BUG_MAIN_SUBSTITUTIONS: tuple[tuple[str, int], ...] = (
    ("The Fantasticar", -4),
    ("Personal Tutor", 3),
    ("Thassa's Oracle", 1),
)
BUG_SIDE_SUBSTITUTIONS: tuple[tuple[str, int], ...] = (
    ("Duress", -2),
    ("Abrupt Decay", 2),
)
```

**Implementation notes:**

- Build from the cached source extract and apply the net-zero ledger; the constants above describe
  the audit contract, not a new production module to create.
- Comment headers precede the card rows and are ignored by the canonical parser. Use these exact
  labels: `Status`, `Evidence through`, `Observed source`, and `Reconstruction`.
- Mark the full 75 `inferred-reconstruction`; mark the unchanged source counts and each replacement
  module by their narrower observed provenance in the workbook.

**Acceptance criteria:**

- [ ] The file parses to the exact BUG 60+15 printed above.
- [ ] The combined 75 has zero Fantasticar, exactly three Personal Tutor, two Oracle, three Carpet,
      two Veil, three Witherbloom Charm, and two Abrupt Decay.
- [ ] The substitution ledger is count-neutral per zone and every inferred change is disclosed.
- [ ] Dated and current legality validation return no violations.

### Unit 2: Refresh without rewriting the legal Grixis candidate

**Files:** `decks/doomsday-variants/dated/grixis-squelcher-refresh.txt`,
`decks/doomsday-variants/dated/README.md`

```python
GRIXIS_EXPECTED_PACKAGE: dict[str, int] = {
    "Hexing Squelcher": 3,
    "Pyroblast": 2,
    "Molten Collapse": 1,
    "Barrowgoyf": 4,
    "Badlands": 1,
    "Volcanic Island": 1,
}
```

**Implementation notes:**

- Extract the May 31 list mechanically and compare normalized `(zone, card, count)` tuples to the
  emitted file. Any difference is an inferred change and therefore violates this unit unless the
  newer-result exception in the design decisions is activated and recorded.
- Record the latest Squelcher event date and post-ban row count from the read-only query. Keep
  `legal-at-cutoff` and `observed-current` as separate fields.

**Acceptance criteria:**

- [ ] The file parses to the exact Grixis 60+15 printed above and matches the cached source tuples.
- [ ] The expected red/fair package is present with the exact combined counts above.
- [ ] Dated and current legality validation return no violations.
- [ ] The headers and workbook call the list dated/legal and do not imply a post-ban finish.

### Unit 3: Lock the provenance and validation contract

**Files:** `decks/doomsday-variants/dated/README.md`, `tests/test_doomsday_dated_variants.py`

```python
from pathlib import Path

CANDIDATE_DIR = Path("decks/doomsday-variants/dated")
CANDIDATE_FILES: tuple[str, ...] = (
    "bug-veil-carpet-reconstructed.txt",
    "grixis-squelcher-refresh.txt",
)

def _read_candidate(name: str) -> tuple[str, dict[str, int], dict[str, int]]: ...
def _assert_exact_registration(
    mainboard: dict[str, int],
    sideboard: dict[str, int],
    *,
    expected_main: dict[str, int],
    expected_side: dict[str, int],
) -> None: ...
```

**Implementation notes:**

- Use `parse_decklist` and `validate_deck`; do not add a second parser or deck validator.
- Keep exact expected dictionaries in the test as the executable registration contract. This
  deliberate duplication protects the curated artifact from unnoticed edits; the deck file remains
  the user-facing import source.
- Verify headers as labels, not research prose. The workbook remains the detailed provenance source.
- This test is hermetic: it reads tracked files and the package-shipped ban ledger, not DuckDB or the
  network. The one-time currency query is implementation evidence recorded in the item/workbook.

**Acceptance criteria:**

- [ ] Tests fail on a missing candidate, malformed line, 59/61 main, 14/16 sideboard, changed exact
      registration, banned card, copy-limit violation, absent provenance header, or reintroduced
      Fantasticar.
- [ ] Tests distinguish the BUG inferred reconstruction from the Grixis observed historical list.
- [ ] `README.md` manifest entries and files agree on ids, paths, status, evidence date, and source.

## Implementation Order

1. **Unit 1 — BUG reconstruction first:** it contains the legality repair and the highest-judgment
   cross-list splice; failure here invalidates the selected architecture.
2. **Unit 2 — Grixis current check and exact preservation:** establish whether the newer-result
   exception is inactive, then emit the observed 75.
3. **Unit 3 — provenance workbook and executable contract:** finalize the manifest from the emitted
   registrations and lock counts, labels, and legality with focused tests.

No child stories are created. The units share one small artifact set and must remain consistent in
one implementation stride.

## Testing and validation

### Focused automated test

`tests/test_doomsday_dated_variants.py` uses `TestDoomsdayDatedVariants` with parametrized candidate
cases. It verifies parser success, exact 60/15 counts and dictionaries, combined copy limits via
`validate_deck`, pinned and current ban-list legality, required header labels, Fantasticar absence,
and package-specific counts. No fixture factory is warranted for two immutable registrations.

Run:

```bash
.venv/bin/pytest tests/test_doomsday_dated_variants.py -q
```

### Read-only evidence verification

- Compare BUG and Grixis source tuples directly from their cached JSON with the emitted unchanged
  subsets.
- Query `data/legacy.duckdb` for cutoff/current adoption and record the result; do not make the test
  depend on the mutable database.
- Run a parser/count/legality smoke check on both files with the canonical functions.

### Repository validation

```bash
.venv/bin/pytest tests/test_generation_export.py tests/test_banlist.py -q
git diff --check -- .work/active/features/research-handoff-doomsday-splash-variants-2.md decks/doomsday-variants/dated tests/test_doomsday_dated_variants.py
```

## Risks

- **Riskiest assumption — the post-ban Tutor/Oracle module composes with the BUG source shell.** No
  published list attests this exact splice; pile resources and tutor tempo may differ with main
  Witherbloom Charm and Quantum Riddler. **Fallback:** keep the 75 labeled inferred and use the
  comparison program as a learning test; if initial pile rehearsal fails, preserve this artifact
  and revise through a new version rather than rewriting its provenance.
- **A newer result invalidates the currency classification.** The campaign cutoff may already trail
  a newly ingested event. **Fallback:** the read-only current query runs before authorship; a newer
  exact BUG/Grixis registration pauses the affected unit for an item-body discovery rather than
  silently mixing sources.
- **Legality and currency get collapsed.** A dated list can remain legal, while a current-looking
  composite can remain unvalidated. **Fallback:** separate fields and tests; never use “current” as
  a legality synonym.
- **The Decay overlay confounds the Fantasticar repair.** Two independent changes mean a bad result
  cannot identify which splice mattered. **Fallback:** log the Decay substitution explicitly and
  compare it against the historical sideboard in playtest notes; do not attribute outcomes from one
  run to a specific card package.
- **Current-field prose overreaches weak analytics.** The ranking surface has zero proof-grade
  grounded rows. **Fallback:** workbook language stays at card-role/test-question level and records
  no matchup win-rate or superiority claim.
- **Parallel feature ownership collides at the root manifest.** Features 1 and 4 also create
  Doomsday variant artifacts. **Fallback:** this feature owns only `dated/`; the downstream
  comparison-program feature, which depends on all candidate features, consolidates the root
  manifest after their directories exist.

## Implementation notes

- Execution capability: GPT-5.6 Luna high — bounded static artifacts, source-ledger reconstruction,
  and focused parser/legality tests required high judgment around provenance but no broad code
  surface.
- Review weight: standard (default).
- Files changed: `decks/doomsday-variants/dated/bug-veil-carpet-reconstructed.txt`,
  `decks/doomsday-variants/dated/grixis-squelcher-refresh.txt`,
  `decks/doomsday-variants/dated/README.md`,
  `tests/test_doomsday_dated_variants.py`, and this item.
- Tests added/removed: added the hermetic `TestDoomsdayDatedVariants` contract coverage for exact
  registrations, provenance labels, package counts, pinned/current legality, and manifest status
  separation; no tests removed.
- Simplification: no production abstraction or second parser/validator added; the immutable
  registrations remain plain import text and tests reuse canonical parser and ban-list functions.
- Discrepancies from design: read-only DuckDB reports maximum Doomsday date `2026-08-18` (the
  all-format database maximum is later); its Squelcher query observes 12 stored source rows while
  the source-direct campaign extract reports nine 2026 entries, consistent with the documented
  duplicate/source-entry caveat. Neither changes the design outcome: zero post-ban BUG or Squelcher
  rows, and the latest Squelcher date remains `2026-06-27`.
- Adjacent issues parked: none.

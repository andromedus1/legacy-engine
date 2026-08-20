---
id: research-handoff-doomsday-splash-variants-4
kind: feature
stage: done
tags: [advisory, generation]
parent: null
depends_on: []
release_binding: null
gate_origin: null
research_origin: doomsday-splash-variants
created: 2026-08-20
updated: 2026-08-20
---

# Prototype alternate Doomsday modules

Build bounded learning prototypes for the evidence-supported long tail: Paradigm Shift/Oracle,
Emrakul/Shelldock, Moonshadow, Cori-Steel Cutter, Chancellor of the Annex, and selected recurring
value threats. Preserve historical, concentrated-pilot, and Fantasticar-legality qualifications;
do not present the prototypes as current stock lists.

## Research grounding

**Source**: `.research/analysis/campaigns/doomsday-splash-variants/parent.md` (slug:
`doomsday-splash-variants`)

These packages recur beyond singleton noise and are useful learning directions, but their evidence
is dated, heterogeneous, or attached to a banned historical chassis.

## Design

### Decision

Use one **module workbook** plus six parser-valid prototype 75s. This is preferable to either a
single omnibus list (which confounds the modules) or six full primers (which would imply more
confidence than the evidence supports). Each 75 gets an explicit evidence-status header and a
short substitution ledger naming the observed source, any Fantasticar-era cards removed, and the
inferred replacements.

The prototypes are learning instruments, not stock recommendations:

1. Paradigm Shift + extra Thassa's Oracle
2. Emrakul, the Aeons Torn + Shelldock Isle
3. Moonshadow creature switch
4. Cori-Steel Cutter + Barrowgoyf red hybrid
5. Chancellor of the Annex protection package
6. recurring value threats (Quantum Riddler / Jace / Sheoldred-class slots)

### Files and contract

- `decks/doomsday-variants/alternate/README.md` is the authoritative module workbook. It records
  observed facts separately from inferred post-ban substitutions, module purpose, sequencing
  caveats, and the measurement question for each prototype.
- `decks/doomsday-variants/alternate/*.txt` contains exactly 60 maindeck cards followed by a
  `Sideboard` marker and exactly 15 sideboard cards in the repository's import-text convention.
- Each list header includes `Status`, `Evidence through`, `Observed source`, and `Reconstruction`
  fields. No list may contain The Fantasticar.
- The manifest section in the workbook is the single source of truth for prototype id, filename,
  module, evidence posture, and source citation.

### Implementation order

1. Reconstruct the Moonshadow and Cutter prototypes first because removing the banned Fantasticar
   chassis without erasing the module is the highest-judgment unit.
2. Build the Paradigm, Shelldock, Chancellor, and value prototypes from exact recurring source
   lists, changing only what legality or the explicit learning question requires.
3. Author the workbook from the completed lists; do not duplicate full deck contents in prose.
4. Run count, duplicate-section, banned-card, and card-name checks over all six files.

### Acceptance criteria

- Six distinct, importable 75s exist and each isolates the named module as far as its observed
  chassis permits.
- Historical, concentrated-pilot, and reconstruction qualifications are visible before the card
  list and in the workbook; no prototype is called current stock.
- Every inferred card substitution is disclosed, and observed finish/adoption evidence is not
  rewritten as matchup or performance superiority.
- Every list is 60+15, contains four or fewer copies of nonbasic/non-exempt cards, contains no
  Fantasticar, and resolves against the local card dimension except for an explicitly documented
  coverage gap.

### Verification

- Add a lightweight data test that scans the variant directory for section counts, copy limits,
  the Fantasticar exclusion, manifest/file agreement, and card-dimension name coverage.
- Run that test plus `git diff --check`.

### Risks

- Replacing Fantasticar can accidentally create a new chassis claim. Mitigation: minimal disclosed
  substitutions and prototype language.
- Shelldock and Chancellor packages can look like ordinary sideboard cards without their setup
  constraints. Mitigation: workbook sequencing notes and a dedicated measurement question.
- Six lists may drift independently. Mitigation: machine-checked manifest and shared validation.

## Implementation notes
- Execution capability: GPT-5.6 Luna high; cohesive data-and-test implementation with six bounded import-text artifacts.
- Review weight: standard (default).
- Files changed: `decks/doomsday-variants/alternate/README.md`; six files under `decks/doomsday-variants/alternate/`; `tests/test_doomsday_alternate_variants.py`.
- Tests added/removed: added 21 focused checks for workbook/file agreement, parser section counts, copy limits, module presence, provenance headers, card-dimension coverage, reconstruction disclosure, and pinned/current banlist legality. Focused plus existing Doomsday parser/banlist suites pass (34 tests).
- Simplification: kept each reconstruction to the smallest disclosed maindeck splice (`The Fantasticar` removal plus `Personal Tutor` replacement); no shared production abstraction or central manifest changes.
- Discrepancies from design: Cutter uses the exact valid 2026-07-17 Eureka22422 5-0 registration as its source anchor; the July 21 Last Chance lists are also valid 60+15 registrations, but the July 17 5-0 was selected as the evidence anchor. The emitted Cutter reconstruction remains only `-3 The Fantasticar +3 Personal Tutor`.
- Review fixes: narrowed Moonshadow's Fantasticar claim to the seven late-June lineage lists, acknowledged the exact legal Enrichetta 2026-01-29 comparator, and strengthened manifest/section-marker tests.
- Adjacent issues parked: none.

## Review (2026-08-20)

**Verdict**: Approve after changes

**Blockers**: resolved inline — Moonshadow evidence is scoped to the seven late-June
Fantasticar/Bauble lists and separately acknowledges the exact legal January registration.
**Important**: resolved inline — Cutter source selection no longer calls valid July 21 lists
invalid, and tests now enforce the exact six manifest pairs plus one Sideboard marker per file.
**Nits**: none
**Rejected**: `Spectral Restitching` to `Hide on the Ceiling` is canonical Oracle-name resolution,
not an undisclosed card substitution.

**Notes**: Standard-weight substrate review used exactly one fresh-context balanced pass. Commit
`da10fea` resolves every receiver-confirmed finding; 34 focused/related tests pass and the diff is
clean. No second independent pass runs under standard weight. Security, migration, concurrency,
UI, and deployed-operational lenses were inapplicable.

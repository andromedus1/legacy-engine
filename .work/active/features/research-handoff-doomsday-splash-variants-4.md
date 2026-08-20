---
id: research-handoff-doomsday-splash-variants-4
kind: feature
stage: implementing
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

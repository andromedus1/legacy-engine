---
id: research-handoff-doomsday-splash-variants-3
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

# Build representative Doomsday chassis variants

Produce representative candidate 75s for the three evidenced game-one structural directions:
Personal Tutor turbo, Tamiyo/Bilbo/Unearth value, and Wasteland/Murktide tempo. Keep structural
labels separate from unmeasured claims about kill speed or matchup superiority.

## Research grounding

**Source**: `.research/analysis/campaigns/doomsday-splash-variants/parent.md` (slug:
`doomsday-splash-variants`)

The refreshed post-ban sample shows that these chassis coexist independently of sideboard color,
so chassis choice must be learned rather than hidden inside splash comparisons.

## Design decisions

- **Autopilot judgment:** use one exact published post-ban registration for each structural label,
  not a synthesized median or an optimized list. This preserves source provenance and avoids
  turning selected card frequencies into unsupported deckbuilding claims.
- **Structural labels are game-one construction labels:** `personal-tutor-turbo`,
  `tamiyo-bilbo-unearth-value`, and `wasteland-murktide-tempo` describe visible maindeck structure.
  “Turbo” does not assert a measured kill turn, “value” does not assert matchup advantage, and
  “tempo” does not assert comparative win rate.
- **Selected registrations:** clan's 2026-08-18 League 5-0 for Personal Tutor turbo;
  Battlegrounds' 2026-08-12 League 5-0 for Tamiyo/Bilbo/Unearth value; HJ_Kaiser's 2026-08-12
  Challenge seventh-place list for Wasteland/Murktide tempo. They are selected because each is a
  clean, current example of the target signature, not because its recorded finish proves the
  chassis superior.
- **Keep card files parser-compatible and self-describing:** each file uses the canonical
  `N Card Name` plus `Sideboard` format and a fixed `# key: value` comment header. The public
  `legacy_engine.models.decklist.parse_decklist` already ignores these comments.
- **Legality is live and version-stamped:** acceptance compares the header's legality snapshot with
  `current_banlist().as_of` and requires `validate_deck` to return no errors. A later B&R change is
  intended to fail this contract and force a candidate refresh.
- **Direct-read only:** this is a bounded static-artifact feature with known source files and one
  existing parser/validator seam. No exploratory or advisory sub-agent is warranted.
- **No UI work:** no user-interface surface changes, so mockups are not applicable.

## Architectural choice

### Options considered

1. **Source-exact registrations with in-file provenance headers — chosen.** Three text files copy
   the selected cached registrations exactly; comment headers bind structural label, source, result,
   research origin, and legality snapshot. A focused test compares each parsed file directly with
   its cached JSON source. This is the smallest reversible design and makes transcription drift
   fail loudly.
2. **Corpus-derived representative composites.** Build each 75 from modal or median card counts
   across its current chassis family. This would represent the family rather than one pilot, but it
   would introduce unsupported tie-breaking, may produce a 75 nobody registered, and would blur
   observed structure with generated recommendation.
3. **Manifest-driven generation.** Add a YAML/JSON registry and generate all three text files from
   it. This would centralize metadata, but creates a generator, schema, and synchronization surface
   for only three immutable source extracts. The exact cached registration is already the source of
   truth, so generation does not earn its complexity here.

Option 1 is chosen. It matches the consumer: players need readable/importable 75s, while tests need
an exact source comparison. It also keeps future design work free to synthesize or tune lists under
separate labels rather than silently changing what “representative” meant here.

## Provenance and artifact contract

Every deck file begins with these exact header keys:

```text
# structural_label: <closed label>
# color_configuration: <dimir|esper>
# evidence_scope: exact-published-registration
# source_player: <pilot>
# source_result: <published result>
# source_date: <YYYY-MM-DD>
# source_path: <repository-relative cached JSON path>
# source_url: <published event/deck anchor>
# research_origin: .research/analysis/campaigns/doomsday-splash-variants/parent.md
# legality_snapshot: <current BanListSnapshot.as_of>
# claim_boundary: construction label only; no measured kill-speed or matchup-superiority claim
```

The closed structural labels and exact source bindings are:

| Label | Deliverable | Source registration | Required maindeck signature |
|---|---|---|---|
| `personal-tutor-turbo` | `decks/doomsday-personal-tutor-turbo-75.txt` | clan, `data/cache/Tournaments/MTGO/2026/08/18/legacy-league-2026-08-1810967.json`, 5-0 | 3 Personal Tutor, 3 Lotus Petal, 2 Thassa's Oracle, 2 Street Wraith; no main Bilbo, Tamiyo, Murktide, or Wasteland |
| `tamiyo-bilbo-unearth-value` | `decks/doomsday-tamiyo-bilbo-unearth-value-75.txt` | Battlegrounds, `data/cache/Tournaments/MTGO/2026/08/12/legacy-league-2026-08-1210967.json`, 5-0 | 4 Tamiyo, 4 Bilbo, 1 Unearth; no main Personal Tutor, Murktide, or Wasteland |
| `wasteland-murktide-tempo` | `decks/doomsday-wasteland-murktide-tempo-75.txt` | HJ_Kaiser, `data/cache/Tournaments/MTGO/2026/08/12/legacy-challenge-32-2026-08-1212851626.json`, 7th Place | 3 Wasteland, 2 Murktide, 4 Tamiyo; no main Personal Tutor, Bilbo, or Unearth |

The complete mainboard and sideboard dictionaries must equal the selected source registration;
the signatures above classify the examples but never replace exact equality.

## Implementation Units

### Unit 1: Source-fidelity, structure, count, and legality contract

**File:** `tests/test_doomsday_chassis_variants.py`

This is the trickiest unit because a plausible-looking 60/15 can still be the wrong pilot, wrong
board, stale legality snapshot, or an accidental hybrid of multiple lists. Design this contract
first and make it fail against missing artifacts before transcribing any deck.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

StructuralLabel = Literal[
    "personal-tutor-turbo",
    "tamiyo-bilbo-unearth-value",
    "wasteland-murktide-tempo",
]

@dataclass(frozen=True)
class ChassisCase:
    label: StructuralLabel
    color_configuration: Literal["dimir", "esper"]
    deck_path: Path
    source_path: Path
    source_player: str
    source_result: str
    source_date: str
    required_main: dict[str, int]
    forbidden_main: frozenset[str]

def _parse_provenance_header(text: str) -> dict[str, str]: ...
def _load_source_registration(
    path: Path,
    player: str,
) -> tuple[dict[str, int], dict[str, int], str]: ...
```

**Implementation notes:**

- Parameterize one `ChassisCase` per table row above; do not duplicate three separate test classes.
- Parse deck cards with `legacy_engine.models.decklist.parse_decklist`, not the advisory private
  wrapper and not a new parser.
- Read cached JSON directly and select exactly one `Decks` entry by case-sensitive `Player`; fail
  with an assertion naming path/player when zero or multiple rows match.
- Convert `Mainboard` and `Sideboard` arrays to `{CardName: Count}` dictionaries and compare both
  zones for exact equality with the parsed artifact.
- Require header keys exactly as specified, header source path/player/result/date to match the
  `ChassisCase`, `evidence_scope` and `claim_boundary` to remain literal, and `source_url` to be
  nonempty and use the selected event/deck anchor.
- Assert main total `== 60` and side total `== 15` explicitly; `validate_deck` permits a short
  sideboard and therefore cannot own the exact-75 invariant by itself.
- Bind `snapshot = current_banlist()`, assert `header["legality_snapshot"] ==
  snapshot.as_of.isoformat()`, then require `validate_deck(main, side, snapshot) == []`.
- Assert each required and forbidden maindeck signature. Do not inspect sideboard signatures when
  assigning the game-one chassis label.

**Acceptance Criteria:**

- [ ] All three files parse through the canonical parser without special-case handling.
- [ ] Each parsed mainboard and sideboard exactly equals one selected cached source registration.
- [ ] Every artifact is exactly 60 main plus 15 side and passes the current version-stamped Legacy
      legality snapshot with no errors.
- [ ] Each header is complete, matches its source and structural label, and carries the literal
      claim boundary.
- [ ] Required/forbidden maindeck signatures keep the three structural labels distinct.
- [ ] Removing a card, moving a card between boards, changing a source/player header, adding The
      Fantasticar, or changing a defining signature makes a focused assertion fail.

---

### Unit 2: Three source-exact chassis 75s

**Files:**

- `decks/doomsday-personal-tutor-turbo-75.txt`
- `decks/doomsday-tamiyo-bilbo-unearth-value-75.txt`
- `decks/doomsday-wasteland-murktide-tempo-75.txt`

**Text interface:**

```text
# <provenance header contract from above>
N Card Name
...

Sideboard
N Card Name
...
```

**Implementation notes:**

- Copy counts and exact card names from the selected raw `Mainboard`/`Sideboard` arrays; do not
  replace cards, normalize basics, combine registrations, or tune sideboards.
- Keep one blank line immediately before `Sideboard`; either the blank or marker is accepted by the
  parser, while the marker keeps the boundary obvious to a human.
- Preserve punctuation and apostrophes verbatim (`Thassa's Oracle`, `Bilbo, Thief in the Night`,
  `Jace, Wielder of Mysteries`).
- Record the observed result only as source provenance. Do not add primer language claiming the
  result was caused by the chassis.
- The Battlegrounds artifact legitimately carries Esper Teferi/Swords cards. Its structural label
  describes the game-one Bilbo/Tamiyo/Unearth chassis; `color_configuration: esper` keeps the
  overlapping color module visible.

**Acceptance Criteria:**

- [ ] The Personal Tutor deliverable is a verbatim rendering of clan's selected 75.
- [ ] The value deliverable is a verbatim rendering of Battlegrounds' selected 75.
- [ ] The tempo deliverable is a verbatim rendering of HJ_Kaiser's selected 75.
- [ ] The three headers use distinct structural labels and preserve color configuration separately.
- [ ] No file contains generated-consensus, optimized, matchup-ranked, or measured-speed wording.

---

### Unit 3: Deck-corpus discovery entry

**File:** `decks/README.md`

**Implementation notes:**

- Add a compact “Doomsday chassis registrations” table linking the three files and naming their
  structural label, pilot/date/result, and source-exact status.
- State once that these are observed 75s selected for chassis learning, not consensus decks,
  matchup rankings, or speed measurements.
- Clarify the existing format description: ordinary deck-prep inputs may be maindeck-only, while
  `*-75.txt` packages include an explicit `Sideboard` section. Do not rewrite unrelated deck notes.

**Acceptance Criteria:**

- [ ] All three artifacts are discoverable from `decks/README.md` with accurate labels and source
      provenance.
- [ ] README language preserves the construction-only claim boundary and distinguishes 75s from
      maindeck-only deck-prep inputs.

## Implementation Order

1. **Unit 1 — source-fidelity contract:** implement the parameter table and failing validation
   harness first; it is the highest-risk unit and defines the artifact boundary.
2. **Unit 2 — exact 75s:** transcribe each source registration until its parameterized contract is
   green, one file at a time.
3. **Unit 3 — discovery entry:** document only the verified labels and source registrations after
   all three exact comparisons pass.

No child stories are spawned. The units share one small contract and should land in one stride;
splitting them would create handoff overhead without independent implementation value.

## Testing

### Focused contract tests

Run:

```bash
.venv/bin/pytest tests/test_doomsday_chassis_variants.py -q
```

Coverage must include, per `ChassisCase`:

- canonical text parsing and comment-header tolerance;
- exact main/side comparison against cached raw JSON;
- exact 60/15 counts;
- current `BanListSnapshot` date match and zero `validate_deck` errors;
- structural required/forbidden card signatures; and
- provenance/header equality.

### Integration/regression seam

Run the existing parser/export and ban-list suites to ensure the new artifacts depend only on
stable project contracts:

```bash
.venv/bin/pytest tests/test_generation_export.py tests/test_banlist.py -q
```

No network, DuckDB refresh, or generated-output snapshot is required. The cached tournament JSON
and package-shipped ban-list registry are the deterministic sources.

## Risks

- **Chassis and splash overlap:** the value source is Esper and all sideboards carry their own
  interaction choices, so readers may attribute color-package effects to chassis. **Fallback:** keep
  `structural_label` and `color_configuration` separate and repeat the claim boundary in README.
- **Verbatim transcription drift:** a valid-looking 75 may differ from the selected source by one
  card or board location. **Fallback:** exact dictionary equality to raw JSON, not sampled counts.
- **Future B&R invalidates a candidate:** `current_banlist()` can advance after these files land.
  **Fallback:** allow the test to fail loudly, then replace the candidate with a newly evidenced
  legal registration or explicitly reclassify it as historical in a separately scoped change.
- **Cached-source path movement:** cache maintenance could relocate a file while preserving the
  event URI. **Fallback:** update the provenance path and test case together only after resolving
  the same event/player registration; never silently fall back to a database aggregate.
- **Recorded finish invites causal interpretation:** 5-0 and seventh-place labels are salient but
  uncontrolled. **Fallback:** retain results only in provenance fields and prohibit superiority or
  measured-speed wording in the artifact/README contract.

## Implementation notes

- Execution capability: GPT-5.6 Luna high — bounded static-artifact transcription with a focused
  parser/source/legality contract.
- Review weight: standard (default).
- Files changed: `tests/test_doomsday_chassis_variants.py`; the three `decks/doomsday-*-75.txt`
  registrations; `decks/README.md`.
- Tests added/removed: added six parameterized tests covering canonical parsing, exact cached
  main/side equality, 60/15 totals, current version-stamped legality, structural signatures, and
  provenance/header equality; none removed.
- Simplification: none; the implementation uses the existing canonical parser and ban-list
  validator without new generation or registry machinery.
- Discrepancies from design: none.
- Adjacent issues parked: none.

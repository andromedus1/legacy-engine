---
provenance: agent-synthesis
updated: 2026-08-20
temporal_contract: snapshot
snapshot_cutoff: 2026-08-20
---

# Doomsday pivot outcome surface and publication bias

## Finding

The apparent post-ban Personal Tutor advantage over the Wasteland chassis survives reasonable
restrictions only as a small descriptive direction, not as a demonstrated performance penalty.
The unrestricted published records are 22-5 for five Personal Tutor lists and 7-9 for three
Wasteland lists, approximately a 38-point difference in recorded match-win percentage. Removing the selected
League 5-0 publications changes the comparison to 7-5 versus 7-9, approximately a 15-point difference.
Restricting both arms to MTGO Challenges changes it again to 7-5 versus 7-7, approximately an 8-point
difference. `[ddp-outcome-current-corpus]{4}`

{inferred: evidential interpretation} The direction therefore persists under the available
sensitivity cuts, but most of its magnitude collapses when publication mechanism and event type are
made more comparable. The Challenge-only Wasteland arm is two different lists from one pilot; the
Tutor arm is two lists from two pilots. That is insufficient for a causal conclusion that tempo
hybridization weakens Doomsday. `[ddp-outcome-current-corpus]{4}`

This distinction matters for the proposed sideboard project. The observed penalty attaches to a
main-deck Wasteland chassis, not to sideboard transformation in general. {inferred: taxonomy
boundary} The public outcome surface cannot answer whether an unchanged turbo game-one deck gains
equity by changing plans after boarding, because it does not isolate that treatment from main-deck
Tutor, Tamiyo, Bilbo, Teferi, Murktide, and color-package changes. `[ddp-outcome-current-corpus]{1}`
`[ddp-outcome-current-corpus]{3}`

## Exact-list and coverage baseline

The post-ban slice contains 12 entries through August 18: 12 distinct exact 75s, 11 pilot names,
and 11 tournament source IDs. HJ_Kaiser is the sole repeated pilot, with two different Wasteland
lists, and the August 15 Challenge is the sole source containing two slice entries.
`[ddp-outcome-current-corpus]{1}`

Six entries are League publications, all labeled 5-0 and all lacking standings or round rows. The
other six have standings-derived records: five deck entries from four 32-player MTGO Challenges
and one entry from a seventeen-player paper event. The Challenge round table contains seven top-eight
matches per event, so only one of the five Challenge Doomsday entrants appears in it; the paper
entrant appears in two recorded rounds. Standings support the non-League records, but the available
round data cannot reconstruct matchups for the outcome sample. `[ddp-outcome-current-corpus]{2}`

Consequently, the slice supports three different statements and no stronger one:

1. Exact lists can be bound to published records without exact-list duplicate inflation.
   `[ddp-outcome-current-corpus]{1}`
2. Non-League records can be separated from selected League 5-0 publications through standings.
   `[ddp-outcome-current-corpus]{2}`
3. The source cannot test whether a tempo juke rescued otherwise bad archetype matchups, because
   League matchups are absent and non-League round coverage is sparse. {inferred: coverage limit}
   `[ddp-outcome-current-corpus]{2}`

## Overlapping category surface

The category totals must not be added together: chassis labels overlap within exact lists.
2plus2isfive is both Personal Tutor and Tamiyo, while three current lists are simultaneously
Tamiyo, Bilbo, and Teferi. `[ddp-outcome-current-corpus]{3}`

| Category | All published | League excluded | What survives the bias control |
|---|---:|---:|---|
| Personal Tutor main | 22-5 | 7-5 | Positive event-only record, but only two lists/pilots. |
| Wasteland main | 7-9 | 7-9 | No League-selection boost; three lists, two pilots. |
| Tamiyo main | 30-13 | 15-13 | Near-even after League removal. |
| Bilbo main | 17-6 | 7-6 | Near-even after League removal. |
| Teferi main | 19-2 | 4-2 | Three of four entries are selected League 5-0s. |
| Main Murktide | four wins, five losses | four wins, five losses | Two lists/pilots; one paper entry recorded two losses. |
| UB color package | 21-11 | 11-11 | Even after League removal. |
| White-only package | 19-2 | 4-2 | Three of four entries are selected League 5-0s. |
| Green-white package | 8-3 | 3-3 | One League 5-0 plus one Challenge 3-3. |

All totals and memberships come from the exact-list extract. `[ddp-outcome-current-corpus]{3}`
{inferred: bias diagnosis} The dramatic published records for Teferi and white-only lists are at
least as selection-sensitive as the Personal Tutor result: each changes from 19-2 to 4-2 when
League publications are removed. Green-white changes from 8-3 to 3-3. The slice therefore does
not support ranking splash colors or calling value-combo superior to UB. `[ddp-outcome-current-corpus]{3}`

The main-Murktide rows are 4-5 and Wasteland rows are 7-9, which is directionally consistent with
the hypothesis that a deeper tempo lean performs worse. `[ddp-outcome-current-corpus]{3}` Yet
{inferred: treatment ambiguity} these are not independent intensity steps: the two main-Murktide
lists are also Wasteland/Tamiyo lists, and the third Wasteland list uses Bilbo. The records cannot
separate threat choice, Wasteland, reduced turbo density, pilot, or event field as the driver.
`[ddp-outcome-current-corpus]{1}`

## Sensitivity and dependence

### Publication-selection sensitivity

The six League entries contribute 30-0 to the 48-16 aggregate published record and provide no
failed-run denominator. Three of those six entries belong to the Personal Tutor category and none
to Wasteland. `[ddp-outcome-current-corpus]{2}` `[ddp-outcome-current-corpus]{4}` A raw 22-5 versus
7-9 comparison therefore mixes a success-conditioned publication channel with standings-backed
ordinary records.

### Event-type sensitivity

Removing Leagues retains a winless two-match paper entry in the Wasteland arm. Restricting to MTGO Challenges removes
that row and narrows the comparison to Tutor 7-5 versus Wasteland 7-7. `[ddp-outcome-current-corpus]{4}`
{inferred: sensitivity conclusion} Because the descriptive difference drops at each restriction,
the evidence favors “selection explains much of the apparent gap” over “the raw gap measures
chassis strength.” It does not show that selection explains all of the directional difference.

### Pilot, list, and source dependence

Exact-list clustering changes nothing because all 12 hashes are unique. Pilot clustering matters:
HJ_Kaiser supplies two of three Wasteland lists and the entirety of its Challenge-only 7-7 record.
Event clustering also matters because two strategically different lists share the August 15 field.
The corpus supplies too few clusters for a stable inferential correction. `[ddp-outcome-current-corpus]{5}`

Historical BUG, Grixis Squelcher, Moonshadow, Cutter, and Chancellor rows should not be pooled into
this estimate. They cross prior card-legality periods and mix League selection, standings-backed
events, repeat pilots/lists, and known duplicate/date defects. They attest that those configurations
were played and achieved particular finishes, but are incommensurable with the current slice as a
single performance rate. `{incommensurable: era and publication mechanism}`
`[ddp-outcome-current-corpus]{6}`

## Decision implication

{inferred: test prioritization} Keep Personal Tutor turbo as a priority arm because its event-only
record remains positive, but do not declare it the winner. Retain one deep Wasteland/tempo arm
because the direction is unresolved rather than disproven. Most importantly, add a sideboard-only
transformation arm sharing the turbo game-one 60. That three-way structure distinguishes:

- concentrated turbo construction;
- a compact post-board juke that preserves game-one density; and
- deep hybridization that pays main-deck slots and mana for a fair plan.

The public records cannot make that distinction because existing labels overlap and matchup
coverage is missing. `[ddp-outcome-current-corpus]{1}` `[ddp-outcome-current-corpus]{2}`
{inferred: experimental discriminator} If the sideboard-only arm improves the targeted hostile
matchups without losing the turbo arm's broader results, the problem is likely hybridization depth,
not transformation itself. If both fair-plan arms underperform within paired matchup blocks, the
“two weaker strategies” hypothesis gains support.

## Disconfirming analysis

- **Against “the raw result proves turbo is better.”** Removing League 5-0 publications cuts the
  rounded Tutor/Wasteland gap from 38 to 15 points; Challenge-only restriction cuts it to 8 points.
  `[ddp-outcome-current-corpus]{4}`
- **Against “the tempo signal disappears entirely under controls.”** Tutor remains numerically
  ahead in both restricted comparisons: 7-5 versus 7-9, then 7-5 versus 7-7.
  `[ddp-outcome-current-corpus]{4}`
- **Against “white or Teferi is clearly best.”** Both 19-2 surfaces become 4-2 after selected
  Leagues are removed. `[ddp-outcome-current-corpus]{3}`
- **Against “the records reveal matchup rescue.”** League rows have no round data; only two of six
  non-League pilots appear in the round table, for three matches total. `[ddp-outcome-current-corpus]{2}`
- **Against duplicate-list inflation as the current explanation.** All 12 exact-list hashes differ.
  The remaining dependencies are publication channel, pilot, and event rather than copied 75s.
  `[ddp-outcome-current-corpus]{1}` `[ddp-outcome-current-corpus]{5}`
- **Against generalizing from Wasteland to every fair juke.** The Wasteland rows alter the main
  chassis and overlap Tamiyo, Murktide, or Bilbo. They do not isolate a sideboard-only pivot.
  `[ddp-outcome-current-corpus]{1}`

## Contradictions

| Relationship | Position A | Position B |
|---|---|---|
| `qualifies` — raw versus controlled surface | Tutor's full published record is 22-5 versus Wasteland's 7-9. `[ddp-outcome-current-corpus]{4}` | The Challenge-only comparison is 7-5 versus 7-7. `[ddp-outcome-current-corpus]{4}` |
| `tension` — persistent direction versus inferential weakness | Tutor remains numerically ahead after both restrictions. `[ddp-outcome-current-corpus]{4}` | The strict comparison has two lists per arm and only one Wasteland pilot, with no matchup reconstruction. `[ddp-outcome-current-corpus]{2}` `[ddp-outcome-current-corpus]{4}` |
| `qualifies` — exact-list independence versus broader dependence | Every post-ban exact 75 is unique. `[ddp-outcome-current-corpus]{1}` | One pilot repeats, two lists share one event, and six rows share a success-conditioned League publication channel. `[ddp-outcome-current-corpus]{2}` `[ddp-outcome-current-corpus]{5}` |
| `incommensurable` — historical finishes versus current rates | Older BUG, Grixis, and alternate configurations have recorded successful finishes. `[ddp-outcome-current-corpus]{6}` | They occupy different legality windows and contain additional publication, pilot, list, and duplicate/date dependencies. `[ddp-outcome-current-corpus]{6}` |

These tensions are retained rather than resolved by averaging all published records.

## Revisit if

- The post-ban slice gains enough standings-backed lists to provide several independent pilots per
  chassis and event type.
- Swiss round coverage can bind exact Doomsday 75s to opponent archetypes, allowing the hostile-
  matchup rescue hypothesis to be tested directly.
- Local paired blocks reach the protocol's minimum sample for turbo, sideboard-only transform, and
  deep-tempo arms.
- A new legality boundary changes the available chassis or invalidates the August 10 regime.

## Revisions

- 2026-08-20 — Removed task-context wording after adversarial review. The outcome population was
  already the exact-archetype August 10–18 cohort and its Tutor/Wasteland sensitivity totals did not
  require recomputation; the source attestation separately corrects two row-level Tamiyo labels.

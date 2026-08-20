---
description: Read when deciding how far a Doomsday build should lean from focused combo into a sideboard juke, value plan, or denial-tempo chassis.
type: brief
kind: research
summary: The selected post-ban surface directionally disfavors deep Wasteland hybrids, but most of the raw gap disappears under event controls; sideboard-only pivots and value-combo require separate tests, including a new matched-main no-juke control.
updated: 2026-08-20
provenance: agent-synthesis
key_findings:
  - The raw Personal Tutor versus Wasteland published-record gap contracts sharply after removing selected League publications and restricting to MTGO Challenges.
  - Pivot location matters more than the broad label fair plan: sideboard-only, maindeck value, and Wasteland-backed denial are different construction treatments.
  - Existing tournament round coverage cannot test whether a pivot rescues hostile matchups.
  - The registered Dimir comparison control already carries a creature juke, so a matched-main no-juke arm is required to test transformation itself.
decisions:
  - Prioritize a four-rung intensity test: no-juke turbo, matched-main sideboard juke, value-combo, and deep denial-tempo.
  - Preserve Personal Tutor turbo as a priority arm and Wasteland/Murktide as a diagnostic arm without declaring either causally superior.
  - Evaluate pivots with matchup-block deltas and explicit break-even scenarios rather than aggregate published records.
---

# Doomsday pivot intensity and performance

## Decision result

The available evidence does **not** support “all-in combo is better than every fair juke.” It does
support a narrower concern: the three post-ban lists making the deepest maindeck denial-tempo
commitment have a weaker-looking published surface than Personal Tutor lists, and that construction
also changes lands, acceleration, access, and threat density together. [ddp-taxonomy-postban]{2}
[ddp-outcome-current-corpus]{4}

The raw comparison is Personal Tutor at 22-5 and Wasteland at 7-9. Removing success-conditioned
League publications narrows it to 7-5 versus 7-9; restricting both arms to MTGO Challenges narrows
it again to 7-5 versus 7-7. The descriptive direction survives, but its magnitude is strongly
sensitive to publication mechanism and event type. [ddp-outcome-current-corpus]{2}
[ddp-outcome-current-corpus]{4}

{inferred: decision} Treat this as a reason to **test hybridization depth**, not a reason to abandon
transformational sideboards. Keep focused Personal Tutor turbo near the front of the program, retain
one Wasteland/Murktide arm to test the suspected cost, and insert a matched-main comparison between
no-juke turbo and a sideboard-only transformation. The present corpus cannot supply that last
contrast because its registered Dimir control already devotes seven sideboard slots to measured
fair cards. [ddp-taxonomy-registry]{1}

## What “leaning tempo” must mean

The campaign's post-ban population contract is exact stored archetype `Doomsday` from August 10
through August 18. It contains twelve exact lists. A broader maindeck-Doomsday construction census
would additionally contain one `Conflict(Doomsday,TES)` row; that row is excluded from both the
outcome and taxonomy comparisons here. [ddp-outcome-current-corpus]{1}
[ddp-taxonomy-postban]{1}

A binary combo/tempo label collapses three different costs. The registered measurements retain land
count, Wasteland, acceleration, selection/access, maindeck value permanents, and sideboard pivot
cards separately. [ddp-taxonomy-registry]{1}

| Construction class | Operational definition | Registered examples | What can be taxed |
|---|---|---|---|
| **A — focused combo** | No measured deep denial, large maindeck value engine, or qualifying sideboard pivot | BUG reconstruction only | Little measured fair-plan density, though its green splash still confounds a clean Dimir control |
| **B — sideboard-led pivot** | Measured main-value count below threshold; at least four fair sideboard cards or a linked alternate package | Current Dimir, Personal Tutor, Grixis Squelcher, Moonshadow, Cutter, Chancellor, alternate combos | The qualifying module is sideboarded, but other maindeck interaction or up to two measured value permanents may remain |
| **C — value-combo overlap** | At least six named maindeck value permanents without the denial threshold | Esper/Bilbo and four-color | Game-one engine slots and setup mana, without Wasteland denial |
| **D — deep denial-tempo** | At least three Wasteland and four maindeck value permanents | Wasteland/Murktide | Lands, acceleration/access, denial sequencing, pressure density, and sideboard plan together |

These rules classify the fourteen registered candidates as A1/B10/C2/D1 and the twelve-list
post-ban slice as A0/B5/C4/D3. Raising the thresholds moves boundary cases but preserves the main
distinction: Wasteland constructions remain deeper commitments, while high-density Esper/Bilbo
remains a value middle. [ddp-taxonomy-registry]{1} [ddp-taxonomy-postban]{1}

This classification also revises a color-based Grixis classification. The registered Squelcher list has
one Squelcher main, no Wasteland, and six measured fair cards sideboarded; it is closer to a compact
protection juke than to the Wasteland denial chassis. [ddp-taxonomy-registry]{4}

## What the published outcomes can and cannot say

The post-ban slice has twelve unique exact 75s, eleven pilots, and eleven tournament source IDs.
Six rows are League publications, all 5-0 and all missing standings and rounds. The other six have
standings-derived records, but only three direct matches for two of those pilots appear in the
round table. [ddp-outcome-current-corpus]{1} [ddp-outcome-current-corpus]{2}

| Comparison | Published surface | Bias-restricted surface | Interpretation |
|---|---:|---:|---|
| Personal Tutor vs Wasteland | 22-5 vs 7-9 | Challenge-only 7-5 vs 7-7 | Direction persists; most raw separation disappears |
| Teferi main | 19-2 | League-excluded 4-2 | Attractive raw record is highly publication-sensitive |
| White-only package | 19-2 | League-excluded 4-2 | Same totals as Teferi, but a different four-list membership |
| Green-white | 8-3 | League-excluded 3-3 | One selected League row drives much of the raw difference |
| Main Murktide | four wins, five losses | same | Two lists and two pilots; overlaps Wasteland/Tamiyo |

Chassis memberships can overlap: Personal Tutor can coexist with Tamiyo, while Bilbo can coexist
with Tamiyo, Teferi, or Wasteland. Each list separately receives one exclusive color-package label.
The table is therefore a sensitivity surface, not a ranking or an adjusted package estimate.
[ddp-outcome-current-corpus]{3} [ddp-outcome-current-corpus]{5}

The direct matchup question remains unanswered. Registered source events provide standings much
more often than complete target-player rounds, and the available rounds do not reconstruct the
opponent-archetype distribution for these lists. [ddp-match-store]{1} Consequently, a deep hybrid
could still improve a narrow hostile matchup while losing elsewhere; the published aggregate cannot
confirm or reject that rescue mechanism.

## Break-even frame for a matchup rescue

{inferred: scenario algebra} Let `s` be the hostile matchup's expected field share, `gain` the
candidate's improvement in that matchup, and `loss` its deterioration over the rest of the field.
Break-even requires:

`s × gain = (1 − s) × loss`

For each one-point loss elsewhere, the required hostile-matchup gain is:

| Hostile field share | Required gain in that matchup |
|---:|---:|
| 10% | 9 points |
| 20% | 4 points |
| 30% | about 2⅓ points |

Double the required gain if the broad-field loss is two points. These are scenarios, not estimates
of Legacy or of any candidate. They provide a decision rule for the paired results: a pivot is worth
its aggregate cost only if the measured hostile-cell improvement, weighted by the expected room,
repays deterioration elsewhere.

## Prioritized test program

### Phase 0 — create the missing experimental contrast

{inferred: experimental design} Register two legal list versions with the **same Dimir maindeck and
mana base**:

1. a no-juke turbo sideboard focused on protection and matchup interaction; and
2. a creature-transform sideboard with an explicit fair-plan boarding map.

This pair is required before interpreting “sideboard juke versus all-in.” The existing control is a
class-B creature juke, while the sole registered class-A list is a green reconstruction and therefore
not a clean Dimir control. [ddp-taxonomy-registry]{1}

### Phase 1 — compare four intensity rungs

| Rung | Candidate | Main question | First blocks |
|---|---|---|---|
| A | New matched-main no-juke Dimir | Baseline combo consistency and post-board interaction | blue permission; fast combo; permanent-based disruption |
| B | Same main with creature-transform sideboard | Does the juke rescue hostile post-board games without harming the shared game-one engine? | blue tempo/removal; attrition; graveyard interaction |
| C | `current-esper-teferi-swords` | Does maindeck value/timing protection plus white removal repay its slot and mana cost? | blue permission; creature/permanent pressure |
| D | `wasteland-murktide-tempo` | Does denial plus pressure improve mana-dependent cells enough to repay broad consistency costs? | nonbasic-heavy mana; blue tempo; permanent disruption |

Personal Tutor turbo should also remain a focused-access benchmark because its bias-restricted
record stays numerically positive; BUG and Grixis follow as targeted protection experiments rather
than replacements for the four-rung construction test. [ddp-outcome-current-corpus]{4}
[ddp-taxonomy-registry]{4}

Use the existing protocol's exact list version/hash, fixed opponent list/version, balanced
play/draw and list order, pre/post-board states, and twenty-completed-match threshold. Report
candidate-level and matchup-block paired deltas alongside keep rate, mulligans, combo turns,
boarding, splash mana, Wasteland exposure, protection relevance, and alternate-plan outcomes.
[ddp-playtest-protocol]{1}

For the matched-main A/B pair, game-one observations should agree up to sampling noise because the
60 is identical; the decision signal is the post-board delta and the documented boarding exchange.
For C and D, game one is itself part of the treatment, so their pre-board results must not be pooled
with the A/B sideboard-only contrast. {inferred: measurement boundary}

## Interpretation of the original hypothesis

The “two weaker strategies” hypothesis splits into three claims:

- **Sideboard dilution:** plausible, but currently unmeasured. Published sideboard-led class-B
  successes prevent
  treating every compact juke as harmful. [ddp-taxonomy-postban]{1}
- **Maindeck value dilution:** plausible but not directionally supported by the selected surface;
  value lists also have successful publications whose magnitude is selection-sensitive.
  [ddp-outcome-current-corpus]{3}
- **Deep denial-tempo dilution:** the live concern. Its construction tax is visible and its selected
  outcomes are weaker-looking, but the strict comparison is two Tutor pilots against one repeated
  Wasteland pilot and has no matchup reconstruction. [ddp-outcome-current-corpus]{4}
  [ddp-taxonomy-postban]{2}

{inferred: strategic conclusion} The evidence-supported current stance is neither “always juke” nor “always
all-in.” Preserve a focused combo engine unless the second plan has a defined matchup target and a
measurable break-even case. Sideboard-only pivots deserve the first test because they can hold the
maindeck constant. Deep tempo deserves a diagnostic test because it is the registered current construction
showing both a broad resource shift and a persistent weak-looking direction under sensitivity cuts.

## Disconfirming analysis

- **Against the raw turbo-superiority claim:** removing League publications reduces the rounded
  Tutor/Wasteland gap from about 38 points to about 15; the Challenge-only gap is about 8.
  [ddp-outcome-current-corpus]{4}
- **Against “the tempo signal vanishes”:** Tutor remains numerically ahead in both restricted
  comparisons, although the strict Wasteland arm is one pilot's two lists.
  [ddp-outcome-current-corpus]{4}
- **Against “all fair pivots lose”:** eleven of twelve post-ban lists have a sideboard-pivot
  signature before precedence, including selected undefeated publications.
  [ddp-taxonomy-postban]{1}
- **Against “Grixis proves deep tempo”:** the registered red list lacks Wasteland and places most
  measured fair density in the sideboard. [ddp-taxonomy-registry]{4}
- **Against matchup-rescue inference from placements:** the source rows lack complete Swiss and
  League matchup coverage. [ddp-match-store]{1}
- **Against treating the current protocol as already sufficient:** its control is itself a
  sideboard juke, so it cannot estimate the effect of adding that juke to the same maindeck.
  [ddp-registered-candidates]{1} [ddp-taxonomy-registry]{1}

## Contradictions

| Relationship | Position A | Position B |
|---|---|---|
| `qualifies` — raw versus controlled outcome | Tutor's published record is 22-5 against Wasteland's 7-9. [ddp-outcome-current-corpus]{4} | Challenge-only records are 7-5 and 7-7, and the Wasteland side is one pilot. [ddp-outcome-current-corpus]{4} |
| `tension` — juke viability versus all-in simplicity | Sideboard-pivot signatures occur across most post-ban lists, including successful publications. [ddp-taxonomy-postban]{1} | No current registered list supplies a clean no-juke Dimir control, so transformation cost remains unidentified. [ddp-taxonomy-registry]{1} |
| `tension` — value density versus denial depth | Esper has more named maindeck value permanents than Wasteland/Murktide. [ddp-taxonomy-registry]{1} | Wasteland/Murktide couples its permanents to three denial lands, nineteen total lands, and reduced acceleration/access. [ddp-taxonomy-registry]{2} |
| `incommensurable` — historical success versus current performance | BUG, Grixis, Moonshadow, Cutter, and Chancellor have published historical finishes. [ddp-outcome-current-corpus]{6} | Their legality windows, publication channels, pilot/list dependence, and duplicate/date defects prevent one pooled current rate. [ddp-outcome-current-corpus]{6} |
| `qualifies` — plausible mechanism versus observed effect | Card records specify what Tutor, Wasteland, Veil, Teferi, Squelcher, and alternate threats can do. [ddp-card-capabilities]{1} | The source rows do not measure those mechanisms' matchup effects. [ddp-match-store]{1} |
| `qualifies` — exact archetype versus broader construction census | The outcome and taxonomy surfaces use twelve exact-archetype rows. [ddp-outcome-current-corpus]{1} [ddp-taxonomy-postban]{1} | A broader maindeck-Doomsday predicate adds one conflict-archetype row and is a separately named population, not a silent substitute. [ddp-taxonomy-postban]{1} |

## Revisit if

- New post-ban standings-backed lists provide several independent pilots in each intensity class.
- Swiss or League match rows bind exact list versions to opponent archetypes.
- The matched-main A/B pair reaches the protocol threshold in the same matchup blocks.
- A new legality boundary or candidate hash changes the tested construction.

## Revisions

- 2026-08-20 — Correction after the single adversarial pass: aligned all post-ban construction
  claims to the exact-archetype August 10–18 population; renamed observed class B to
  “sideboard-led pivot”; separated Teferi and exclusive-white rows with coincident totals; distinguished
  overlapping chassis from exclusive color labels; removed task-context wording; and grounded
  candidate status, reconstruction, legality posture, and mechanism claims in extended current
  attestations. The Tutor/Wasteland sensitivity result and four-rung experimental direction remain.

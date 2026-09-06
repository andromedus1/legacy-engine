---
description: Read when deciding which Doomsday pivot candidates and matchup blocks to test next.
type: brief
kind: research
summary: Audits observable matchup-data coverage for the registered Doomsday candidates, derives break-even scenarios without imputing win rates, and proposes a paired-test matrix that preserves the existing protocol.
updated: 2026-08-20
provenance: agent-synthesis
key_findings:
  - The local store exposes standings and deck registrations more broadly than direct target-player round rows.
  - Break-even improvement depends on hostile-field share and any deterioration elsewhere; no campaign-specific win rates are available from the registered source rows.
  - The existing 20-match paired threshold and game-level diagnostic fields are the appropriate measurement boundary.
---

# Doomsday pivot performance — matchup economics and test design

## Scope and evidence boundary

The registered comparison contains 14 unique experimental 75s and one artifact alias for the duplicate
Battlegrounds Esper/value registration. The alias is a provenance convenience, not a fifteenth
independent treatment. [ddp-registered-candidates]{1}

The local store contains deck registrations, standings, and some round rows, but direct target-player
round coverage is uneven. Battlegrounds, wakame's four-color registration, clan, and the dated BUG
have deck-level League results but no standings or rounds. HJ_Kaiser and nevilshute have standings
and one and two direct target-player round rows respectively; current Dimir and wizardpasta have
standings and event rounds but no direct target-player row. Neither a deck result nor a standing
identifies opponent archetypes or package-level effects. [ddp-match-store]{1}

Therefore this engagement cannot estimate a registered candidate's matchup win rate, aggregate-record
penalty, or hostile-matchup gain from the local source data. Published placements and 5-0 records
remain registration context, not matchup observations. {inferred: preserve the denominator boundary}
The paired log is the prospective source for matchup-specific package effects. [ddp-match-store]{1}[ddp-playtest-protocol]{1}

## Matchup economics

Let `s` be the hostile matchup's share of the tested field, `gain` the candidate improvement in
that matchup, and `loss` the positive deterioration across the remaining field.

The candidate breaks even when:

`s × gain = (1 − s) × loss`, or `gain = ((1 − s) / s) × loss`.

This is a scenario calculator, not an estimate of the Legacy field. For a one-percentage-point
deterioration elsewhere, the hostile matchup would need a nine-point improvement at a one-tenth hostile
share, a four-point improvement at one-fifth, or an approximately two-and-one-third-point improvement at three-tenths. If the deterioration
is two percentage points, double those required improvements. The formula should be recomputed from the
pre-registered field-share scenario rather than filled with an assumed metagame.

The same calculation applies to a candidate with a direct aggregate-record penalty: the penalty is
not evidence of a useful pivot or a failed pivot until its field share and matchup-specific changes
are observed. Keep aggregate match outcomes, hostile-cell outcomes, and diagnostic mechanisms as
separate columns in the analysis. [ddp-playtest-protocol]{1}

## Plausible mechanisms and measurable endpoints

The card dimension supplies mechanisms that can motivate blocks without asserting outcomes.
{inferred: mechanism-to-endpoint test design} The observation columns below are proposed
measurements rather than effects attested by card text:

| Mechanism hypothesis | Registered examples | Primary observations | Diagnostic observations |
| --- | --- | --- | --- |
| Access / combo consistency | Personal Tutor, Tamiyo/Bilbo | keep rate, mulligans, actual combo turn | tutor or value card presented; pile decision; mana spent before Doomsday |
| Mana denial / tempo | Wasteland, Murktide Regent | paired game and match result | nonbasic exposure, Wasteland punishment, combo sequencing, fair-plan deployment |
| One-turn stack protection | Veil of Summer | paired result in blue/black blocks | splash-mana keep/sequencing effect, color failure, protection presented/live/relevant |
| Persistent stack/timing protection | Hexing Squelcher, Teferi | paired result in stack-heavy blocks | resolution, survival, interaction actually presented, mana spent before combo |
| Creature/permanent removal | Swords to Plowshares, Teferi, Witherbloom Charm | paired result in creature/permanent blocks | cards boarded in/out, target/answer relevance, splash color failure |
| Graveyard / alternate combat plan | Moonshadow, Barrowgoyf, Cori-Steel Cutter | post-board paired result | alternate-plan deployment/result, graveyard-dependent growth, red equip mana |
| Alternate library win | Paradigm Shift, Shelldock Isle, Emrakul, Jace | alternate-plan result | line attempted, threshold reached, sideboard slot consumption, primary Oracle line displaced |
| Value threats | Quantum Riddler, Sheoldred | post-board paired result | cards drawn, mana spent before Doomsday, threat closing a game after primary disruption |

The card rows describe rules text and resource conditions, not matchup performance. For example,
Carpet's mana is conditional on an opponent's Islands, Wasteland targets a nonbasic land, and Veil
requires the protected turn's blue/black context; those conditions should be recorded as observed
events rather than converted into prior win-rate assumptions. [ddp-card-capabilities]{1}

## Prioritized paired-test matrix

Each row below is a comparison arm, not a ranking. Every block uses the current Dimir control and
one candidate under the same opponent list/version. The existing protocol randomizes play/draw and
list order, records pre/post-board games, and requires balanced blocks. [ddp-playtest-protocol]{1}

| Priority | Candidate arm | Question | First matchup blocks | Primary endpoint | Key diagnostic |
| ---: | --- | --- | --- | --- | --- |
| 1 | `personal-tutor-turbo` | Does tutor density change keep/mulligan and actual combo turns without sacrificing paired results? | blue stack/tempo; creature removal | paired game/match delta; combo-turn distribution | keep and mulligan denominator; combo turn |
| 2 | `current-esper-teferi-swords` (canonical arm; `tamiyo-bilbo-unearth-value` is its alias) | Do white removal and Teferi change the relevant post-board interaction at their mana cost? | blue stack; creature/permanent removal | pre/post paired delta | splash mana, protection relevance, cards in/out |
| 3 | `wasteland-murktide-tempo` | Does a maindeck tempo/denial exchange produce useful pressure against mana-dependent opponents? | nonbasic-heavy mana; creature/permanent decks | paired pre/post delta | Wasteland exposure/punishment; fair-plan deployment |
| 4 | `bug-veil-carpet-reconstructed` | Does the inferred green shield repay its reconstruction and mana costs in blue/black rooms? | blue/black stack; Island-rich mana | paired post-board delta | color failure, Carpet availability, protection relevance |
| 5 | `grixis-squelcher-refresh` | Does the dated persistent protection package merit a current-room test? | blue stack/permission | paired post-board delta | Squelcher survival/presentation, blast relevance, red mana |
| 6 | alternate transformation arms (`moonshadow-creature-switch`, `cori-steel-cutter-barrowgoyf`) | Can a sideboard transformation win games without changing the primary combo's pre-board consistency? | creature removal; graveyard interaction | post-board paired delta | alternate deployment/result, mana tax, boarded slots |
| 7 | library/value alternate arms (`paradigm-shift-oracle`, `emrakul-shelldock-isle`, `value-threats-jace-riddler-sheoldred`, `chancellor-annex-protection`) | Do alternate/value modules create a measurable post-board line worth their slots? | graveyard interaction; stack; attrition | post-board paired delta | line reached, alternate result, protection/tax relevance |

The first three arms isolate broad construction questions using exact current or post-ban
registrations. The dated and reconstructed arms should follow only after their registered
list-version/hash and legality posture are copied into the log. The alternate arms are module
experiments; their status fields do not make them interchangeable with the control or with one
another. [ddp-registered-candidates]{1}

## Sideboard-only juke versus maindeck tempo hypothesis

The hypothesis is testable but not resolved by the current registry: a sideboard-only transformation
may preserve pre-board combo consistency better than a maindeck tempo package, while gaining less
game-one pressure. The registered artifacts do not form a one-variable contrast—Wasteland/Murktide
changes the maindeck, while Moonshadow/Cutter change the post-board plan and reconstruct a banned
chassis—so an across-arm difference cannot be attributed to the package alone. {inferred: compare}
[ddp-registered-candidates]{1}

Use two stages:

1. Compare pre-board keep/mulligan and combo-turn distributions for the tempo arm and each
   transformation arm against the same opponent list/version.
2. Compare post-board paired results and explicit alternate-plan outcomes, retaining each list's
   deck hash, board changes, and evidence posture.

If the project later emits a matched-main/rotating-sideboard series, repeat the comparison with the
maindeck held constant. That is the design needed to distinguish a sideboard juke from a chassis
effect; the current registry cannot supply it by itself.

## Stopping and interpretation

Use the existing preregistered threshold of 20 completed matches per list, with pre/post-board games
inside balanced paired blocks. Thin or unfinished matches remain in the raw log but are excluded from
the completed-match threshold and are labeled descriptively. [ddp-playtest-protocol]{1}

Report, for every arm and block:

- game and match wins/losses/draws with denominators;
- keep rate and total mulligans with game denominators;
- combo-turn distribution with observed-turn denominator and explicit not-seen count;
- paired candidate-minus-control delta, keyed by block and pair;
- splash-mana, Wasteland, boarding, protection, and alternate-plan diagnostics.

Do not rank arms from a thin sample. A later decision should combine the measured paired deltas with
the explicit break-even scenario for the expected hostile share, not substitute a placement,
standing, or aggregate record for the missing matchup cell.

## Contradictions

- The local store contains many deck registrations and standings, but target-player round coverage is
  sparse and absent for several exact source lists. The registration/standing position is visible in
  the `decks` and `standings` rows; the direct-match position is visible in `rounds`. These are
  different evidence objects, not a blended matchup record. [ddp-match-store]{1}
- The protocol asks for paired matchup-block deltas, while the source corpus supplies mostly
  event-level results. The former is a prospective measurement contract; the latter cannot satisfy
  it retrospectively. [ddp-playtest-protocol]{1}[ddp-match-store]{1}
- The card dimension supplies plausible mechanisms, while no source row here measures those
  mechanisms' matchup effects. Treat the mechanism-to-endpoint mapping as a test design
  extension, not an observed result. {inferred: map}

## Disconfirming analysis

The source-registration tournament IDs were checked for target-player round rows and compared with
the event-level round counts and standings. That check found zero direct rows for Battlegrounds,
wakame's four-color source, clan, and the BUG reconstruction; one direct row for HJ_Kaiser; and two
for nevilshute. It also found current Dimir and wizardpasta standings without direct target-player
round rows. This is disconfirming evidence against using published event records as a matchup
denominator. [ddp-match-store]{1}

The card capability rows were also checked for evidence of a matchup gain. They
contain Oracle text and resource conditions, but no game outcomes, so they disconfirm any causal or
comparative performance claim based only on card text. [ddp-card-capabilities]{1}

## Revisit if

Reopen this facet when the playtest log reaches 20 completed matches per arm; when a candidate's deck
hash changes; when a target opponent block has enough paired pre/post games to expose a stable
diagnostic pattern; or when a matched-main/rotating-sideboard series becomes available. Reopen the
break-even scenarios whenever the expected hostile-field share changes.

## Revisions

- 2026-08-20 — Corrected the standings/deck-result boundary, narrowed the paired-log claim to
  prospective matchup effects, marked the mechanism-to-endpoint map as composed test design,
  grounded candidate status/legality posture in the extended registry attestation, and removed
  task-context narration.

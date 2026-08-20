---
description: Read when choosing which Doomsday configurations, splashes, or transformational modules to build and test in the post-Fantasticar Legacy format.
type: brief
kind: research
summary: A wide-net map of current and recent Doomsday chassis, color packages, protection layers, transformational plans, alternate wins, and unusual threats, with evidence-calibrated build directions.
updated: 2026-08-20
provenance: agent-synthesis
research_method: /research
key_findings:
  - Post-ban published Doomsday is not one Dimir 60; tutor-turbo, Tamiyo/Bilbo value, and Wasteland/Murktide tempo chassis coexist.
  - Esper and green-white/four-color are the observed post-ban splash branches; pure BUG and Grixis Squelcher are developed but currently dated branches.
  - Color labels are insufficient because protection, removal, alternate-win, and fair-threat modules overlap across chassis.
  - Moonshadow, Cori-Steel Cutter, Paradigm Shift/Oracle, Chancellor, Ring/Riddler, and other recurring modules warrant learning tests but have dated, concentrated, or legality-qualified evidence.
  - Published finishes demonstrate viable registrations, not package-controlled matchup superiority.
decisions:
  - Use Dimir creature-transform as the comparison control, then investigate Esper, green in separate BUG and green-white forms, and Grixis as distinct learning arms.
  - Treat shared-maindeck compatibility as a later design optimization rather than a gate on research directions.
---

# Doomsday variation landscape — build directions after The Fantasticar

## Decision result

There is considerably more Doomsday variation than “Dimir, Esper, BUG, or Grixis.” The useful
model has four independent axes: **game-one chassis**, **protection layer**, **interaction layer**,
and **post-board win plan**. Current lists mix those axes rather than selecting one sealed color
archetype. Five of the first 12 post-ban lists use Personal Tutor, eight use Tamiyo, three use
Wasteland, four use Bilbo, and four use Teferi; the selected-card signatures are unique across all
12 lists.[ddv-landscape-current-db]{6}

{inferred: experimental design} The recommended learning sequence is:

1. Keep a **Dimir creature-transform** list as the control arm.
2. Build **Esper Teferi/Swords** as the first current splash comparator.
3. Explore green in two distinct forms: **pure BUG Veil/Carpet/Charm or Decay** and the current
   **green-white/four-color shield**. They answer different questions and should not be collapsed.
4. Build **Grixis Squelcher/blasts** as a deliberate blue-room experiment, recognizing that its
   evidence ends in June.
5. Preserve a second learning track for non-color variants: **tutor-turbo, Bilbo/Tamiyo value,
   Wasteland/Murktide tempo, Paradigm Shift/Oracle, Moonshadow, Cutter, Chancellor, and value
   permanents**.

This is an experiment order, not a matchup ranking. The corpus records published lists and results,
but does not isolate package effects or contain the failed-League denominator.
[ddv-landscape-current-db]{1}[ddv-packages-module-census]{10}

## What is current after the ban

Wizards banned The Fantasticar effective August 10, 2026.[ddv-packages-ban-20260810]{1} The first
post-ban Doomsday slice contains 12 published lists from 11 pilot names and 12 exact 75s through
August 18:

| Published family | Entries | What distinguishes it |
|---|---:|---|
| Blue-black | 6 | Creature-transform and/or tutor, value, or tempo chassis |
| Esper Teferi/Swords | 3 | Teferi main; Swords and Ending side; Tundra and Scrubland |
| White permanent | 1 | Main Voice of Victory; Portable Hole side |
| Green-white hybrid | 2 | White interaction plus Veil, Carpet, and Tropical Island |

No pure BUG or red/Squelcher list appears in that slice.[ddv-landscape-current-db]{1} All six
published League entries are 5-0s, but unpublished failed runs are absent, so the observation shows
that each family produced a publishable run—not a family win rate.[ddv-landscape-current-db]{1}

The surrounding refreshed 386-list field contains substantial blue interaction, creature pressure,
and artifact/big-mana strategies at the same time. Dimir Tempo, Dimir Midrange, Azorius Midrange,
Blue Artifacts, Izzet Delver, and Show and Tell supply blue interaction; Boros Energy and Death &
Taxes keep creature answers relevant; Tron has 31 assigned rows.[ddv-compare-current-corpus]{1}
{inferred: room implication} A splash aimed only at counterspells is therefore a targeted local-room
choice, not an automatic general upgrade.

## Atlas of game-one chassis

{inferred: experimental design} Treat the chassis question before the sideboard question because
current Doomsday does not have one
invariant 60. All 12 current lists share the Doomsday/Force/Brainstorm/Ritual core, but Petal, Daze,
Thoughtseize, Flow State, Oracle, Sea, tutor, creature, and denial counts vary.
[ddv-compare-wide-corpus]{1}

| Chassis | Observed construction | Evidence posture | Strategic hypothesis |
|---|---|---|---|
| **Tutor-dense turbo** | 1–3 Personal Tutor; commonly two Oracle, three Petal, and extra Wraith | 5/12 current lists; 81 stored rows from 35 pilots since April 20 [ddv-compare-wide-corpus]{2} | {inferred: role} Increases direct Doomsday access and enabler density, but is not a measured faster clock. |
| **Tamiyo/Bilbo/Unearth value** | 2–4 Bilbo, 3–4 Tamiyo, Unearth; often Teferi | Four current pilots and four distinct published lists [ddv-compare-wide-corpus]{3} | {inferred: role} Moves the fair/value plan into game one. |
| **Wasteland/Murktide tempo** | Three Wasteland, main Murktide and Tamiyo; some Jace or Bowmasters | Three current lists from two pilots [ddv-compare-wide-corpus]{4} | {inferred: role} Exchanges turbo density for mana denial and combat pressure. |
| **Green pile/utility** | Main Witherbloom Charm with green duals; sometimes Ring | Charm appears main in 37 rows from 14 pilots through July 13 [ddv-compare-wide-corpus]{11} | {inferred: role} Makes green part of piles, draw, and permanent interaction rather than only a sideboard shield. |
| **Value-permanent** | Main The One Ring or Quantum Riddler | Ring and Riddler recur across several pilots but end before the current slice [ddv-compare-wide-corpus]{10}[ddv-compare-wide-corpus]{11} | {inferred: role} Adds non-Doomsday card advantage at a main-slot and mana cost. |

“Turbo” in this atlas describes construction, not a measured turn distribution. Game logs would be
needed to compare actual kill speed.[ddv-compare-wide-corpus]{2}

## Color and protection directions

### Dimir creature-transform

The current sideboard creature module is plural rather than fixed: Dauthi appears in 11 current
sideboards, Barrowgoyf in ten, Murktide in seven, Bowmasters in six, and Tamiyo in two. Ten lists
carry at least two different names from that set.[ddv-packages-module-census]{3} It preserves the
two-color mana base while changing the opponent's post-board threat problem. {inferred: limitation}
It does not itself create an uncounterability window, so stack protection still comes from Forces,
discard, Daze-like interaction, or narrower counter tools.

{inferred: experimental design} Use this as the experimental control because it is current, keeps
the attested two-color mana structure, and is close to the deck already being played—not because
the corpus proves comparative win-rate superiority.

### Esper — current, broad, and still partly transformational

The representative post-ban Esper package uses two Teferi main, three Swords and two Prismatic
Ending side, with Tundra and Scrubland; it retains eight sideboard creatures.
[ddv-packages-list-esper-battlegrounds]{2}[ddv-packages-list-esper-battlegrounds]{3}
Teferi restricts opposing spell timing and can bounce an artifact, creature, or enchantment while
drawing. Swords supplies one-mana creature exile; Ending covers a color-count-bounded nonland
permanent.[ddv-compare-card-affordances]{3}[ddv-compare-card-affordances]{4}

{inferred: test priority} Use this as the first splash comparator because its current registrations combine proactive stack
protection, creature interaction, and a reduced fair transformation. Its costs are visible: Teferi
occupies game-one slots, the white interaction occupies five sideboard slots, and the mana base
adds two nonbasic splash lands. {inferred: testing hypothesis} It is most interesting when the room
asks for both anti-countermagic and creature/permanent answers.

Teferi is not a blanket lock. Triggered abilities still trigger and activated abilities remain
usable with priority.[ddv-packages-rules-202608]{2}[ddv-packages-rules-202608]{4}

### Pure BUG — genuine lineage, current-status gap

Pure BUG is not hypothetical: the store contains 29 green-without-white-or-red source rows from 14
pilot names and 22 exact-list hashes between May 23 and July 13. Packages range from main
Witherbloom Charm with Veil/Carpet to four Veil, three Carpet, and two Abrupt Decay. No pure BUG
list appears after the August 10 ban.[ddv-landscape-current-db]{2}

The attested green cards supply three distinct roles.[ddv-compare-card-affordances]{1}
[ddv-compare-card-affordances]{2}[ddv-compare-card-affordances]{7}

- **Veil of Summer:** a one-turn anti-countering and blue/black hexproof shield, conditionally a
  cantrip.[ddv-compare-card-affordances]{1}
- **Carpet of Flowers:** opponent- and Island-dependent main-phase acceleration.
  [ddv-compare-card-affordances]{2}
- **Witherbloom Charm/Abrupt Decay:** pile-capable draw/life or cheap-permanent interaction, versus
  uncounterable removal for a nonland permanent of mana value three or less.
  [ddv-packages-release-sos]{3}[ddv-compare-card-affordances]{7}

BUG should be rebuilt as a post-ban experiment rather than copied verbatim: the attested clean BUG
75 used four Fantasticars and is now illegal.[ddv-packages-list-bug-wakame-preban]{4}
{inferred: room hypothesis} It is best motivated by a room heavy on blue/black permission and
attrition, especially when Carpet's mana will be live; it is poorly justified merely by the generic
idea that green is flexible.

### Green-white/four-color — the current green answer

The green configurations actually observed post-ban also play white. One light build uses a single
Tropical alongside Tundra/Scrubland, light Veil, three Carpet, and four Swords across the 75. The
full shield uses three Veil and three Teferi main, then three each of Carpet, Swords, and Ending
side, with two Tropical, Tundra, and Scrubland.[ddv-packages-list-green-white-wizardpasta]{2}
[ddv-packages-list-green-white-wizardpasta]{3}[ddv-packages-list-four-color-wakame]{2}
[ddv-packages-list-four-color-wakame]{3}

This evidenced direction combines Veil, Carpet, Teferi, Swords, and Ending and is the current
“other version” beyond Esper. Its breadth is also its tax: the full build must schedule green for Veil, white-blue for
Teferi, triple black for Doomsday, and double blue for Oracle across a highly nonbasic mana base.
[ddv-packages-list-four-color-wakame]{4}[ddv-packages-card-oracle-local]{5}
{inferred: learning value} Treat the light and full forms as separate tests; otherwise it will be
unclear whether green, white, or their combination created the observed experience.

### Grixis Squelcher — developed, coherent, and dated

Grixis Squelcher appears nine times from May 24 through June 27, representing six pilot names and
five exact lists. The recurring build uses Badlands, Volcanic Island, one Squelcher main, two side,
and two Pyroblast; results include published undefeated Leagues and placed Challenge/paper runs.
No Squelcher entry occurs after June 27.[ddv-landscape-current-db]{3}

Squelcher itself cannot be countered and makes its controller's spells uncounterable while it
remains; it and the other creatures gain ward—pay 2 life. The representative build complements it
with Pyroblast and Molten Collapse while retaining four Barrowgoyf in the sideboard.
[ddv-packages-release-ecl]{1}[ddv-packages-list-grixis-nevilshute]{2}
[ddv-packages-list-grixis-nevilshute]{5}

This is a real build direction, not a novelty singleton. {inferred: test priority} Place it behind
Esper and the two green tests for a generic mixed field because its adoption is dated and its
blasts are narrow. It moves
forward when the expected room is unusually blue or when the learning goal is persistent
anti-countermagic rather than one-turn protection.

### Protection cards are not interchangeable

Veil and Squelcher prevent countering; Teferi prevents opponents from casting spells outside
sorcery timing. Mindbreak Trap exiles targeted spells rather than countering them, so Veil and
Squelcher do not answer its resolved exile effect. A resolved Teferi instead prevents Trap from
being cast during the Doomsday player's turn.[ddv-compare-card-affordances]{1}
[ddv-compare-card-affordances]{3}[ddv-compare-card-affordances]{5}
[ddv-compare-card-affordances]{9}

Their sequencing costs also differ: Veil needs green on the protected turn; Squelcher costs two and
must survive; Teferi costs three and must resolve first; Carpet requires an opposing Island and
produces mana only through its main-phase trigger.[ddv-compare-card-affordances]{1}
[ddv-compare-card-affordances]{2}[ddv-compare-card-affordances]{3}
[ddv-compare-card-affordances]{5}

## Wide-net module catalog

These modules deserve visibility without being promoted into unsupported archetype names.

| Module | Evidence status | What it changes |
|---|---|---|
| **Paradigm Shift + extra Oracles** | Five early-May rows from three pilots; two 5-0s and placed event finishes [ddv-compare-wide-corpus]{9} | Paradigm exiles the library, then rebuilds it from the graveyard; Oracle remains the empty-library payoff. [ddv-compare-wide-cards]{6}[ddv-packages-card-oracle-local]{6} |
| **Emrakul + Shelldock Isle** | Seven rows from at least six pilots [ddv-packages-module-census]{7} | Shelldock hides and later plays a card once a library has 20 or fewer cards; Emrakul supplies the large-creature payoff. [ddv-packages-card-oracle-local]{17} |
| **Moonshadow** | Seven late-June rows from six pilots; all on Fantasticar/Bauble mains [ddv-landscape-current-db]{7} | Four-copy mono-black combat transformation whose threat grows as permanent cards enter the graveyard. [ddv-compare-wide-cards]{7} |
| **Cori-Steel Cutter + Barrowgoyf** | Six July rows from four pilots; all use red duals and Fantasticar [ddv-landscape-current-db]{7} | Cutter makes and equips a Monk on the second spell; Barrowgoyf adds a black threat. [ddv-compare-wide-cards]{7}[ddv-compare-card-affordances]{8} |
| **Chancellor of the Annex** | Ten rows from two pilots; several placed finishes [ddv-compare-wide-corpus]{10} | Taxes the first opposing spell from the opening hand and every opposing spell while in play. [ddv-compare-wide-cards]{4} |
| **Jace, Wielder of Mysteries** | Main and sideboard use across many pilots [ddv-packages-module-census]{2}[ddv-packages-module-census]{6} | Alternate empty-library win and draw/mill engine. [ddv-compare-wide-cards]{6} |
| **Ring / Quantum Riddler** | Recurring but heterogeneous and dated [ddv-compare-wide-corpus]{10}[ddv-compare-wide-corpus]{11} | Protection/draw or warp/draw value permanents. [ddv-compare-wide-cards]{8} |
| **Sheoldred / Kaito / Arena** | Recurring sideboard value threats across mixed shells [ddv-packages-module-census]{7} | Draw-step pressure, surveil/draw, or upkeep draw/life engines. [ddv-packages-card-oracle-local]{14}[ddv-packages-card-oracle-local]{18} |
| **Misdirection / Commandeer / Pact / Flusterstorm / Pierce / Chant** | Recur across differing pilot breadth and board locations [ddv-packages-module-census]{11} | Distinct retargeting, control-taking, countering, taxing, or cast-prevention tools. [ddv-packages-card-oracle-local]{19}[ddv-packages-card-oracle-local]{21} |
| **Dauthi / Surgical / Spellbomb / Leyline / Crypt / Cage / Faerie / Cling** | Broad-to-narrow recurring graveyard choices [ddv-packages-module-census]{12} | Replacement exile, graveyard exile, named-card extraction, entry/casting restriction, discard, or reusable spot exile. [ddv-packages-card-oracle-local]{15}[ddv-packages-card-oracle-local]{22} |

Moonshadow and Cutter are meaningful historical lineages, but every observed implementation used
the now-banned Fantasticar core.[ddv-landscape-current-db]{7}
{inferred: legality qualification} Their threats remain legal hypotheses; their exact 75s are not
current templates. Chancellor is similarly real but concentrated mostly in one pilot, while
Riddler, Sheoldred, Arena, Voice, Vision Charm, and Cling recur as modules across unrelated
chassis—not as separate archetypes.[ddv-landscape-current-db]{7}
[ddv-landscape-current-db]{8}

The Yorion/Thundertrap/Temporal Mastery list, Reanimate packages, and Dark Confidant/Skeletal
Scrying remain one-off or duplicate-amplified experiments rather than lineages.
[ddv-landscape-current-db]{9}

## Practical build program

{inferred: experimental design} A learning-oriented build program should compare questions, not
merely colors:

1. **Chassis question:** tutor-turbo versus Tamiyo/Bilbo value versus Wasteland/Murktide tempo.
2. **Protection question:** one-turn Veil versus persistent Teferi versus persistent Squelcher
   versus ordinary Dimir stack/discard tools.
3. **Post-board identity:** creature transform versus removal/control overlay versus alternate
   Oracle combo versus unusual combat threat.
4. **Breadth question:** focused pure BUG or Grixis packages versus the green-white/four-color
   shield.

{inferred: experimental design} Start with complete evidenced registrations for Dimir, Esper, and
the two current green-white builds. Reconstruct a legal post-ban BUG candidate from its banned-core
precedent. Test the dated attested Grixis registration only after refreshing
its metagame assumptions and mana schedule. Treat Paradigm Shift, Moonshadow, Cutter, and Chancellor
as learning prototypes rather than current recommendations.

{inferred: measurement design} For each test, record opening-hand keep rate, actual combo turn,
whether splash mana changed a keep
or sequencing decision, exposure to Wasteland, cards boarded in and out, whether the protection
spell matched the interaction actually presented, and whether the alternate plan won or merely
consumed slots. Keep League publication, event placement, and
matchup win rate as different outcome types.

{inferred: project sequencing} The later interchangeable-sideboard project should begin only after
this program identifies which
axes are worth preserving. Shared-main compatibility is an optimization target, not a filter on
this landscape. Some historical sideboard-only Esper and green switches show that convergence is
possible, but current lists legitimately change maindeck spells and nonfetch lands.
[ddv-compare-wide-corpus]{7}[ddv-compare-wide-corpus]{8}

## Contradictions

- **Current green vs pure BUG — `tension`:** the current slice contains two green-white builds,
  while pure BUG has repeated pilots and successful registrations only through July.
  [ddv-landscape-current-db]{1}[ddv-landscape-current-db]{2}
- **Grixis coherence vs currency — `tension`:** Squelcher/blasts form a repeatable package with
  credible finishes, but no entry appears after June 27.[ddv-landscape-current-db]{3}
- **Published success vs causal quality — `qualifies`:** current and historical branches have 5-0s
  and placed finishes, but the corpus has no failed-League denominator or controlled package
  comparison.[ddv-landscape-current-db]{1}[ddv-packages-module-census]{10}
- **Historical lineage vs legal template — `qualifies`:** the representative BUG 75 and every
  observed Moonshadow/Cutter implementation used The Fantasticar; the card is now banned.
  [ddv-packages-list-bug-wakame-preban]{4}[ddv-landscape-current-db]{7}
  [ddv-packages-ban-20260810]{1}
- **Recurring card vs archetype — `qualifies`:** several value and utility cards recur across
  unrelated chassis or concentrated pilots, supporting module status but not new archetype names.
  [ddv-landscape-current-db]{8}

These positions are not resolved by averaging pre-ban and post-ban results.

## Disconfirming analysis

The wide corpus search disconfirmed a pure-BUG or Grixis claim for the current post-ban slice while
also disconfirming that either branch was merely theoretical: BUG spans many pilots and hashes,
[ddv-landscape-current-db]{2} and Grixis forms a repeated six-pilot package.
[ddv-landscape-current-db]{3} Neither appears in the current slice.
[ddv-landscape-current-db]{1}

The same scan disconfirmed both “Dimir is one stock 60” and “every recurring card is a variant.”
Current lists divide across tutor, value, and tempo chassis, while Riddler, Sheoldred, Arena, Voice,
Vision Charm, and Cling cross shells or concentrate among a small number of pilots.
[ddv-landscape-current-db]{6}[ddv-landscape-current-db]{8}

Rules review disconfirmed blanket-protection readings of Veil, Squelcher, and Teferi. Trap exile
bypasses uncounterability, and Teferi does not stop activated or triggered abilities.
[ddv-compare-card-affordances]{9}[ddv-packages-rules-202608]{2}
[ddv-packages-rules-202608]{4}

## Revisit if

- At least two more weeks of post-ban Challenge, League, and paper results enter the corpus.
- Pure BUG or Grixis publishes a post-ban finish, especially from a new pilot.
- A B&R announcement or card release changes Doomsday's core or interaction environment.
- Match-level evidence becomes bindable to exact 75s.
- The expected local room is specified; testing priority can then be remapped to actual opponents.

## Revisions

- 2026-08-20 — Correction after adversarial review: reconciled Grixis to six pilots and the current
  published League total to six; repaired Witherbloom, module-mechanics, and Fantasticar citation
  loci; restored epistemic markers on experimental recommendations; and distinguished the banned-
  core BUG precedent from the dated Grixis registration. The campaign's taxonomy and temporal
  conclusions are unchanged.

---
provenance: agent-synthesis
updated: 2026-08-20
---

# Comparative decision surface for Doomsday splash packages

## Decision frame

The refreshed evidence does not support treating Dimir creature-transform, Esper, BUG, and Grixis
as four mutually exclusive archetypes. In the 12-list current window, three of the five white lists
also use the sideboard creature package, and both green lists are green-white hybrids rather than
pure BUG. {inferred: overlap} The useful decision unit is therefore the **package** placed on a
Doomsday core: alternate threats, white interaction, green anti-stack/mana, or red
anti-countermagic. [ddv-compare-current-corpus]{2} [ddv-compare-current-corpus]{3}

No source in this facet provides package-controlled matchup win rates. Current placements establish
that configurations were registered and sometimes finished well; they do not measure which package
caused an outcome. [ddv-compare-current-corpus]{7}

## What the current room asks of the sideboard

The refreshed 386-list slice is split across blue interaction, creature decks, and artifact or
big-mana strategies. Dimir Tempo (28), Dimir Midrange (25), Azorius Midrange (18), Blue Artifacts
(18), Izzet Delver (12), and Show and Tell (12) make blue stack interaction materially present,
while Boros Energy (25), Death & Taxes (23), and the Dimir decks keep creature removal relevant;
Tron has 31 assigned rows. These are prevalence observations, not a matchup-weighted
forecast. [ddv-compare-current-corpus]{1}

{inferred: room-mapping} That mixed field argues against choosing a splash solely because it beats
counterspells in theory. A useful candidate must also state what it gives up against creatures,
graveyards, artifacts, and nonblue combo.

## Wide-net strategic taxonomy

The taxonomy below separates **observed structure and results** from **inferred strategic role**.
“Tutor-dense” or “turbo” describes deck construction, not a measured combo-turn distribution. The
database has no game-level clock comparison among these configurations. [ddv-compare-wide-corpus]{1}
[ddv-compare-wide-corpus]{2}

For the future shared-base series, compatibility means that the game-one maindeck can remain fixed
apart from fetchland identity. `Observed sideboard-compatible` means the relevant spells and any
enabling nonfetch lands have appeared entirely in the sideboard. `Base-defining` means observed
lists change nonfetch lands or spells in the game-one maindeck. `Split` means both forms exist. This
is a compatibility classification only; it does not construct or allocate a sideboard.

| Strategic variation | What actually changes | Observed prevalence/results | Inferred role | Shared-base compatibility |
|---|---|---|---|---|
| Tutor-dense structural turbo | One to three Personal Tutor, usually with two Oracle, three Petal, and extra Street Wraith; current lists still vary Daze, Thoughtseize, Flow State, and Sea counts. [ddv-compare-wide-corpus]{1} [ddv-compare-wide-corpus]{2} Personal Tutor puts a sorcery on top of the library. [ddv-compare-wide-cards]{1} | Five of 12 current lists; three League 5-0s and Challenge 10th/17th. Personal Tutor occurs in 81 post-April rows from 35 pilots. [ddv-compare-wide-corpus]{2} | {inferred: structure-to-role} Raises direct Doomsday access and pile-enabler density while spending maindeck slots and a draw step/card-draw action on the top-deck tutor. It is not evidence of a faster measured kill. | **Base-defining.** Personal Tutor, Oracle, Wraith, and interaction counts vary beyond fetchlands. |
| Bilbo/Tamiyo/Unearth value core | Adds two to four Bilbo, three or four Tamiyo, and Unearth to the main deck, often with Teferi. [ddv-compare-wide-corpus]{3} Bilbo casts selected spells from the graveyard after attacking; Unearth recovers a low-mana creature. [ddv-compare-wide-cards]{2} | Four current lists from four pilots: two League 5-0s, Challenge 14th, and Challenge 32nd. [ddv-compare-wide-corpus]{3} | {inferred: structure-to-role} Integrates a fair/value engine into game one instead of reserving the alternate axis for post-board games. | **Base-defining.** Multiple nonfetch maindeck cards change. |
| Wasteland/Murktide tempo core | Three Wasteland, two main Murktide, main Tamiyo, two Petal, and one Oracle; some lists add Jace, others Bowmasters/Unearth. [ddv-compare-wide-corpus]{4} | Three current lists from two pilots: Challenge 7th, paper 16th, Challenge 32nd. [ddv-compare-wide-corpus]{4} | {inferred: structure-to-role} Trades some turbo density for mana denial and a game-one combat plan. | **Base-defining.** Wasteland and main threats are not fetchland substitutions. |
| Instant-speed stack reinforcement | Force of Negation is universal current-sideboard support; Duress, Misdirection, Veil, Commandeer, and blasts are narrower branches. [ddv-compare-wide-corpus]{5} [ddv-compare-current-corpus]{8} Misdirection retargets a single-target spell, while Commandeer takes a noncreature spell. [ddv-compare-wide-cards]{4} | Force of Negation is in all 12 current sideboards. One current League 5-0 has Misdirection side and another has it main; Grixis blasts belong to the dated May–June cluster. [ddv-compare-wide-corpus]{5} [ddv-compare-wide-corpus]{10} [ddv-compare-current-corpus]{8} | {inferred: role} Adds stack exchanges without necessarily changing the win condition; individual tools answer different interaction and cannot be treated as fungible “protection.” | **Split.** Dimir sideboard tools are compatible; main Misdirection and splash cards are base-defining unless their mana moves into the sideboard. |
| Persistent anti-stack permanents | Teferi and Voice restrict when opponents cast spells; Squelcher makes spells uncounterable while present; Chancellor can tax the first opposing spell from the opening hand. [ddv-compare-wide-cards]{3} [ddv-compare-wide-cards]{4} | Current: four main Teferi, one main Voice, one side Voice, zero Squelcher. Dated: Squelcher ends June 27; Chancellor appears in ten rows from two pilots, including Challenge 1st. [ddv-compare-wide-corpus]{6} [ddv-compare-wide-corpus]{10} | {inferred: role} Establishes protection before the combo turn and asks the opponent to answer a permanent or tax. The cards differ against exile-based stack interaction. | **Split.** Sideboard-only Esper switches and Chancellor are observed-compatible; current main Teferi/Voice and observed Squelcher mana are base-defining. |
| Fair-creature transformation | Boards into combinations of Barrowgoyf, Murktide, Tamiyo, Dauthi, and Bowmasters without abandoning the combo core. Their Dimir casting costs need no third color. [ddv-compare-card-affordances]{8} [ddv-compare-wide-cards]{9} | Ten current sideboards contain Barrowgoyf; seven Murktide; eleven Dauthi; six Bowmasters. [ddv-compare-wide-corpus]{5} | {inferred: role} Changes the post-board threat axis and gives the deck a combat route; the corpus does not reveal whether opponents removed creature answers. | **Observed sideboard-compatible** for the Dimir threats. Main Murktide/Tamiyo versions are instead base-defining. |
| Removal/control overlay | Black removal, Consign, bounce/phasing, white Swords/Ending, and green Decay/Charm cover different permanent classes. Consign counters triggered abilities or colorless spells; Hide temporarily exiles artifacts/creatures; Witherbloom Charm can destroy a low-mana nonland permanent. [ddv-compare-wide-cards]{5} | Current sideboards: six Consign, five Long Goodbye, five Ending, five Swords, four Push, plus one-list utility. [ddv-compare-wide-corpus]{5} Sideboard-only white and green mana modules are historically observed. [ddv-compare-wide-corpus]{7} [ddv-compare-wide-corpus]{8} | {inferred: role} Exchanges speed or threat slots for answers to creatures, colorless spells/abilities, or cheap permanents. | **Split.** Dimir control is compatible; sideboard-only Esper and green modules are observed-compatible through sideboard lands; main white/green interaction is base-defining. |
| Graveyard/containment overlay | Dauthi plus smaller Spellbomb, Surgical, Crypt, and Priest branches add graveyard or put-into-play containment. [ddv-compare-wide-corpus]{5} | Dauthi occurs in 11 of 12 current sideboards; the other cards are one-list current inclusions or dated minority tools. [ddv-compare-wide-corpus]{5} | {inferred: role} Covers graveyard engines and alternate deployment while retaining Dimir mana for the dominant piece. | **Observed sideboard-compatible** for the Dimir/colorless tools; white Priest requires white access. |
| Alternate Oracle combo | Four Paradigm Shift plus three additional Oracle in the sideboard; Paradigm Shift exiles the library then shuffles the graveyard back, and Jace separately wins on an empty-library draw. [ddv-compare-wide-corpus]{9} [ddv-compare-wide-cards]{6} | Five rows from three pilots in early May: two League 5-0s, Challenge 3rd/22nd, and a second-place finish. [ddv-compare-wide-corpus]{9} | {inferred: role} Changes the combo mechanism while preserving an empty-library win, potentially altering which hate cards line up; no current adoption is observed. | **Observed sideboard-compatible.** The repeated package is entirely blue and sideboarded; main-deck Jace versions are base-defining. |
| Green pile/utility core | Main Witherbloom Charm adds a black-green draw-two sacrifice mode and low-mana permanent removal; pure BUG also adds Veil/Carpet/Decay. [ddv-compare-wide-cards]{5} [ddv-compare-card-affordances]{1} [ddv-compare-card-affordances]{2} [ddv-compare-card-affordances]{7} | Witherbloom Charm appears main in 37 rows from 14 pilots through July 13; pure BUG also ends before the current slice. [ddv-compare-wide-corpus]{11} [ddv-compare-current-corpus]{10} | {inferred: role} Alters both pile resources and interaction rather than merely adding sideboard protection. | **Base-defining** for main Charm/green duals. A narrower sideboard-only Carpet/Veil/Decay module is observed-compatible through a sideboard Tropical Island. |
| Value-permanent core | Main The One Ring or Quantum Riddler adds protection/card draw or a warp/value creature. [ddv-compare-wide-cards]{8} | Ring: 30 rows, nine pilots, ending July 11. Riddler: 20 main rows from ten pilots and five side rows from five pilots, ending August 8. [ddv-compare-wide-corpus]{10} [ddv-compare-wide-corpus]{11} | {inferred: role} Adds card advantage and non-Doomsday play at the cost of main or side slots; results are heterogeneous. | **Split.** Main Ring/Riddler is base-defining; sideboard Riddler is compatible with Dimir mana. |
| Red token/fair hybrid | Four Cori-Steel Cutter plus four Barrowgoyf side, enabled by main Badlands and Volcanic Island. Cutter produces prowess tokens after a second spell. [ddv-compare-wide-corpus]{12} [ddv-compare-wide-cards]{7} | Six rows from four pilots in July, including two League 5-0s and mixed event finishes. [ddv-compare-wide-corpus]{12} | {inferred: role} Uses the spell-dense core to create a token combat plan alongside black threats. | **Base-defining as observed.** No post-April red package keeps both red spells and red nonfetch lands entirely sideboarded. |
| Black unusual-threat switch | Four sideboard Moonshadow; its body grows as permanent cards enter the graveyard. [ddv-compare-wide-cards]{7} | Seven rows from six pilots across June 24–29, including first-place and League 5-0 results. [ddv-compare-wide-corpus]{10} | {inferred: role} A compact monocolor-black combat transformation distinct from Barrowgoyf/Murktide. | **Observed sideboard-compatible.** No third color or main change is required by the package. |
| One-off current experiments | Main Voice, main or side Misdirection, and singleton bounce, phasing, graveyard, or containment cards. [ddv-compare-wide-corpus]{13} | Each named current experiment is represented by one current list unless counted elsewhere. [ddv-compare-wide-corpus]{13} | {inferred: role} Hypothesis generators, not adoption signals. | **Card-specific.** Sideboard Dimir/colorless tools are compatible; main Voice/Misdirection is not compatible with an otherwise invariant base. |

### Shared-base compatibility implication

{inferred: experimental-design} A future series can compare genuinely sideboard-only branches
without changing the chosen game-one 60: Dimir creature/control/graveyard packages, the observed
sideboard Esper switch, the observed sideboard Tropical/Carpet branch, Paradigm Shift/Oracle,
Chancellor, Moonshadow, sideboard Riddler/Jace, and singleton Dimir stack tools. The current
Bilbo/Tamiyo, tutor-dense, Wasteland/Murktide, four-color, main-Charm, Ring, Squelcher-Grixis, and
Cutter configurations instead define different base maindecks under the fetchland-only rule.
[ddv-compare-wide-corpus]{2} [ddv-compare-wide-corpus]{3} [ddv-compare-wide-corpus]{4}
[ddv-compare-wide-corpus]{7} [ddv-compare-wide-corpus]{8} [ddv-compare-wide-corpus]{9}
[ddv-compare-wide-corpus]{10} [ddv-compare-wide-corpus]{11} [ddv-compare-wide-corpus]{12}

That implication does not choose the shared base or emit a sideboard series. The observed current
60s already vary on nonfetch spells and lands, so base selection must be an explicit later decision
rather than an assumption that “current Dimir” is one list. [ddv-compare-wide-corpus]{1}

## Package comparison

| Package | Direct affordance | Current evidence | Opportunity cost and exposure | Room that justifies a test |
|---|---|---|---|---|
| Dimir creature-transform | Barrowgoyf is a lifelinking/deathtouch body. [ddv-compare-card-affordances]{8} Murktide is a flying delve threat. [ddv-compare-card-affordances]{8} Tamiyo is an early flying value permanent. [ddv-compare-card-affordances]{8} | Ten of 12 current lists use at least one of the three in the sideboard; the representative Dimir list devotes seven sideboard slots to Barrowgoyf, Murktide, and Dauthi while retaining removal and Force of Negation. [ddv-compare-current-corpus]{2} [ddv-compare-current-corpus]{4} | {inferred: mana-and-slot-cost} It keeps the black-blue fetch/dual structure and spends sideboard space changing threats rather than adding a third-color answer class. It still needs several removal slots to support a fair game. | {inferred: testing-hypothesis} Unknown or Wasteland-heavy rooms; mixed fields where a stable two-color core matters; grindy blue rooms where changing the threat axis may punish an opponent's post-board configuration. The last clause is a hypothesis to test, not an attested boarding fact. |
| Esper Teferi/Swords | Teferi limits opposing spell timing and can bounce an artifact, creature, or enchantment while drawing; Swords exiles a creature; Ending exiles a mana-value-bounded nonland permanent. [ddv-compare-card-affordances]{3} [ddv-compare-card-affordances]{4} | Five of 12 current lists use Teferi or Swords. Battlegrounds' 5-0 has two Teferi main and five white interaction cards side, yet also keeps four sideboard fair threats. [ddv-compare-current-corpus]{3} [ddv-compare-current-corpus]{5} | {inferred: mana-and-slot-cost} Teferi asks for three mana including white and blue before it protects the combo. The representative list cuts from four to three Underground Sea and adds Tundra plus Scrubland; its white interaction consumes five sideboard slots and Teferi two main slots. | {inferred: room-mapping} Creature-dense blue rooms or rooms where low-cost permanents and countermagic must both be addressed. It is less specifically aimed at nonblue spell-combo than a discard/Force-heavy Dimir allocation. |
| Pure BUG Veil/Carpet/Decay | Veil gives anti-countering plus blue/black hexproof during the turn it resolves and conditionally replaces itself; Carpet converts opposing Islands into main-phase mana; Decay is uncounterable removal for a nonland permanent of mana value three or less. [ddv-compare-card-affordances]{1} [ddv-compare-card-affordances]{2} [ddv-compare-card-affordances]{7} | Pure BUG is evidenced through July, including Dominic Rode's 8th-place list with 4 Veil/3 Carpet/2 Decay, a League 5-0 with 2 Veil/3 Carpet, and a Challenge 6th with 2 Veil/3 Carpet/2 Decay. No pure BUG list appears in the 12-list current window. [ddv-compare-current-corpus]{10} | {inferred: mana-and-slot-cost} Bayou plus Tropical Island preserve access to black and blue while adding green, but both are Wasteland targets and the package can occupy five to nine sideboard slots in the observed examples. Carpet is conditional on opposing Islands; Veil's protection is limited to the turn and to blue/black targeting. | {inferred: room-mapping} Rooms dominated by blue/black permission and attrition, especially when extra mana is valuable. Do not select it for a field led by non-Island decks or colorless permanent hate merely because “green is flexible.” |
| Grixis Squelcher/blasts | Squelcher cannot be countered and makes its controller's spells uncounterable while it remains; Pyroblast/REB counter blue spells or destroy blue permanents. [ddv-compare-card-affordances]{5} [ddv-compare-card-affordances]{6} | Nine lists from six pilots form a coherent May–June cluster, with League 5-0s and Challenge 3rd among mixed results. The package disappears after 2026-06-27 and is absent from the current 12. The representative configuration has one Squelcher main, two Squelcher and two Pyroblast side, plus Badlands and Volcanic Island. [ddv-compare-current-corpus]{8} [ddv-compare-current-corpus]{9} | {inferred: mana-and-slot-cost} The representative build pays one main and four side slots for red protection, plus two splash dual slots. Squelcher is a permanent that must remain in play; its ward asks for life rather than mana and does not make it immune to removal. Blasts are narrow outside blue cards. | {inferred: room-mapping} A concentrated blue permission room where a persistent uncounterability effect and live blasts justify red. Its dated adoption makes it a targeted experiment, not a current-default inference. |
| Green-white protective hybrid | Combines Veil/Carpet's anti-blue and mana role with Teferi, Swords, and Ending's timing/removal role. [ddv-compare-card-affordances]{1} [ddv-compare-card-affordances]{2} [ddv-compare-card-affordances]{3} [ddv-compare-card-affordances]{4} | This is the green configuration actually present in the current slice: wakame's League 5-0 and wizardpasta's Challenge 17th, both with Veil/Carpet/Swords packages. [ddv-compare-current-corpus]{3} [ddv-compare-current-corpus]{6} | {inferred: mana-and-slot-cost} wakame uses Underground Sea, Tropical Island, Tundra, and Scrubland and commits six main slots to Teferi/Veil plus nine side slots to Carpet/Ending/Swords. This buys broad interaction but leaves a highly nonbasic, four-color casting surface and little room for a creature transformation. [ddv-compare-current-corpus]{6} | {inferred: room-mapping} A room simultaneously heavy on blue/black permission and creatures or cheap permanents, when breadth is worth testing despite mana and slot compression. It is the current evidence-backed “other version.” |

## Protection is not interchangeable

Veil and Squelcher stop countering, while Teferi prevents opponents from casting spells at
non-sorcery timing. Mindbreak Trap exiles spells rather than countering them. {inferred:
rules-consequence} Veil and Squelcher therefore do not answer a resolved Trap ability through their
“can't be countered” text, whereas a resolved Teferi prevents an opponent from casting Trap during
the Doomsday player's turn. [ddv-compare-card-affordances]{1} [ddv-compare-card-affordances]{3}
[ddv-compare-card-affordances]{5} [ddv-compare-card-affordances]{9}

{inferred: sequencing} Veil asks for one green on the protected turn and only lasts for that turn;
Squelcher costs two and must stay on the battlefield; Teferi costs three and must resolve
before it constrains the opponent. Carpet is acceleration conditioned on Islands, not protection
by itself. [ddv-compare-card-affordances]{1} [ddv-compare-card-affordances]{2}
[ddv-compare-card-affordances]{3} [ddv-compare-card-affordances]{5}

## Testing recommendation

1. **Keep Dimir creature-transform as the control arm.** It is the current adoption baseline and
   retains the observed two-color mana structure. [ddv-compare-current-corpus]{2}
   [ddv-compare-current-corpus]{4}
2. **Test Esper as the first splash comparator when the expected room contains both blue
   interaction and creature decks.** It has four current main-deck-Teferi registrations, and its
   white removal can coexist with a smaller creature plan. {inferred: test-priority}
   [ddv-compare-current-corpus]{3} [ddv-compare-current-corpus]{5}
3. **Test green in two separate forms, not under one “BUG” label:** a compact pure BUG package
   (Bayou/Tropical with Veil/Carpet and optional Decay) to isolate green's effect, and the current
   green-white hybrid as a high-breadth stress case. {inferred: experimental-design} Mixing both in
   one arm would confound whether Veil/Carpet or Teferi/Swords drove the result. Pure BUG has dated
   evidence; the hybrid has current evidence. [ddv-compare-current-corpus]{6}
   [ddv-compare-current-corpus]{10}
4. **Place Grixis behind those tests unless the expected room is unusually blue.** Its package is
   coherent and successful finishes exist, but adoption ends in June while the refreshed field has
   moved to other packages. {inferred: test-priority} [ddv-compare-current-corpus]{8}
   [ddv-compare-current-corpus]{8}

Record game-one speed, post-board combo-turn distribution, mulligans attributable to splash mana,
Wasteland-induced color failures, and whether each protection card was live against the actual
interaction presented. {inferred: measurement-design} Do not collapse League 5-0 publication,
Challenge placement, and matchup win rate into one outcome variable.

## Disconfirming analysis

- **Against “BUG is current.”** The source search included all 12 Doomsday lists from 2026-08-10
  onward and all green-signature rows since 2026-04-20. Pure BUG recurs through 2026-07-13 but is
  absent from the current slice; both current green lists also use white. [ddv-compare-current-corpus]{3}
  [ddv-compare-current-corpus]{10}
- **Against “Grixis is just one novelty list.”** The corpus search found nine Squelcher rows, six
  pilots, a stable Badlands/Volcanic package, and several strong finishes. [ddv-compare-current-corpus]{8}
- **Against “Grixis is a current recommendation.”** The same search found no Squelcher after June
  27 and none in the current window. [ddv-compare-current-corpus]{8}
- **Against “Esper replaces the fair transformation.”** Three of the five current white lists also
  carry the sideboard creature package; the observed packages overlap. [ddv-compare-current-corpus]{3}
- **Against “one protection card covers all stack interaction.”** Oracle-text comparison finds that
  Mindbreak Trap exiles rather than counters, while Veil and Squelcher are written around
  countering; Teferi operates through casting-time restriction instead. [ddv-compare-card-affordances]{9}
- **Against performance attribution.** The current sample contains heterogeneous League, Challenge,
  and paper outcomes and lacks a controlled package comparison. No matchup win-rate claim survives
  that check. [ddv-compare-current-corpus]{7}
- **Against “turbo” as a measured speed claim.** Tutor-dense current lists have a recognizable
  Personal Tutor/Oracle/Wraith structure, but the corpus does not contain game-level combo-turn
  distributions. The taxonomy therefore marks structure, not clock. [ddv-compare-wide-corpus]{2}
- **Against one canonical current maindeck.** Even the 12-list current slice varies Petal, Daze,
  Thoughtseize, Flow State, Oracle, Wraith, Underground Sea, tutor, threat, and denial counts.
  [ddv-compare-wide-corpus]{1}
- **Against “splashes necessarily alter game one.”** Three Esper 5-0s keep the full white package
  and its two duals sideboarded, while 13 dated rows keep green cards and Tropical Island entirely
  sideboarded. [ddv-compare-wide-corpus]{7} [ddv-compare-wide-corpus]{8}
- **Against treating unusual threats as noise.** Paradigm Shift/Oracle, Chancellor, Moonshadow,
  Riddler, Ring, and Cutter each recur across multiple rows or pilots; their evidence is dated and
  heterogeneous, but it is not a single recalled-list claim. [ddv-compare-wide-corpus]{9}
  [ddv-compare-wide-corpus]{10} [ddv-compare-wide-corpus]{11}
  [ddv-compare-wide-corpus]{12}

## Contradictions

| Relationship | Position A | Position B |
|---|---|---|
| `tension` — current vs dated green evidence | The current slice contains green only in two green-white configurations. [ddv-compare-current-corpus]{3} | Pure BUG has repeated registrations and finishes through July. [ddv-compare-current-corpus]{10} |
| `tension` — coherent Grixis package vs current adoption | The nine-row corpus cluster shows a repeatable Squelcher/blast build. [ddv-compare-current-corpus]{8} [ddv-compare-current-corpus]{9} | The last observed Squelcher list is June 27, with zero in the current slice. [ddv-compare-current-corpus]{8} |
| `qualifies` — placements vs package quality | Current Esper and hybrid lists include League 5-0s and Challenge finishes. [ddv-compare-current-corpus]{7} | The store does not isolate package effect or provide controlled matchup rates. [ddv-compare-current-corpus]{7} |
| `tension` — shared-base requirement vs current practice | A future comparison requires one game-one maindeck with only fetchland variation. | Current lists vary many nonfetch spells and nonfetch lands. [ddv-compare-wide-corpus]{1} |
| `qualifies` — splash mana vs invariant game one | Current white/green hybrids place splash duals and spells in the main deck. [ddv-compare-current-corpus]{6} | Dated Esper and green configurations demonstrate sideboard-only splash spells plus sideboard duals. [ddv-compare-wide-corpus]{7} [ddv-compare-wide-corpus]{8} |
| `tension` — red strategic evidence vs shared-base compatibility | Grixis Squelcher and Cutter packages recur with recorded finishes. [ddv-compare-current-corpus]{8} [ddv-compare-wide-corpus]{12} | Every post-April red configuration found uses a red-producing nonfetch land in the main deck; no red sideboard-only mana module was found. [ddv-compare-wide-corpus]{12} |

## Revisit if

- A new B&R boundary or set release changes Doomsday's core or the available protection cards.
- The post-2026-08-10 Doomsday slice grows enough to populate pure BUG or Grixis independently.
- Match-level data can bind exact 75s to opponents without repeated-list or repeated-pilot leakage.
- The expected local room is known and materially different from the refreshed public corpus.
- A shared base maindeck is selected; compatibility must then be re-evaluated against that exact 60,
  not against the abstract Dimir shell.

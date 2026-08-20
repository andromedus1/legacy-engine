---
title: Doomsday splash packages and rules interactions
description: Card-role, mana, pile, module-landscape, and fixed-main compatibility analysis for Doomsday.
type: research
summary: Current modules span tutor, recursion, tempo, protection, creature, hate, and hybrid-color axes; splash rotation requires preloaded nonfetch sources.
updated: 2026-08-20
provenance: agent-synthesis
temporal_contract: ttl-bounded
valid_through: 2026-09-10
---

# Doomsday splash packages and rules interactions

## Scope and evidence boundary

This brief compares what each color package *does*, what mana it asks of a Doomsday shell, and how
its cards can interact with a five-card pile. It does not infer matchup superiority from card text.
The representative post-ban lists are registrations, not matchup records: clan supplies the Dimir
baseline; Battlegrounds supplies Esper; wizardpasta and wakame supply two different green-plus-white
packages. The clean BUG and Grixis examples are older registrations. [ddv-packages-list-dimir-clan]{1}
[ddv-packages-list-esper-battlegrounds]{1} [ddv-packages-list-green-white-wizardpasta]{1}
[ddv-packages-list-four-color-wakame]{1} [ddv-packages-list-bug-wakame-preban]{1}
[ddv-packages-list-grixis-nevilshute]{1}

The pre-ban BUG list cannot be copied as a legal 75: it registered four The Fantasticar, and
Wizards banned that card in Legacy effective August 10, 2026. [ddv-packages-list-bug-wakame-preban]{4}
[ddv-packages-ban-20260810]{1} [ddv-packages-ban-20260810]{2}

## Shared combo constraints

Doomsday itself costs `{B}{B}{B}` and retains five chosen cards in the library; Thassa's
Oracle costs `{U}{U}` and wins through an enters-the-battlefield trigger. Every splash therefore
competes with a shell already asking for triple black before the pile and double blue at the kill,
while a splash card placed in the pile consumes one of only five positions. [ddv-packages-card-oracle-local]{5}
[ddv-packages-card-oracle-local]{6}

{inferred: consequence} The cleanest use of Teferi, Hexing Squelcher, and Carpet is usually as
pre-pile infrastructure: resolve the permanent, then cast Doomsday. Veil and Witherbloom Charm can
instead function during pile execution because they are instants, but each adds a colored-mana and
card-position requirement. This is a structural implication of the cards and Doomsday's five-card
limit, not evidence that one pile family wins more often. [ddv-packages-release-rvr]{1}
[ddv-packages-release-ecl]{1} [ddv-packages-card-oracle-local]{1}
[ddv-packages-release-sos]{1} [ddv-packages-release-sos]{3}
[ddv-packages-card-oracle-local]{5}

## Full module inventory from the refreshed corpus

The color splashes sit on top of several independent build axes. The current 12-list slice has a
stable ritual/cantrip/Oracle core, but it divides between Personal Tutor, Tamiyo, Bilbo/Unearth,
and Wasteland/creature-tempo choices. Five lists use Personal Tutor, eight use Tamiyo, four use
Bilbo, five use Unearth, and three contain Tamiyo, Bilbo, and Unearth together. Three lists use
Wasteland, and two use main-deck Murktide Regent. [ddv-packages-module-census]{1}
[ddv-packages-module-census]{2}

### Tutor, acceleration, and card-flow modules

- **Personal Tutor turbo:** Personal Tutor puts Doomsday or another sorcery on top for `{U}`. It is
  present in five current registrations and is a main-deck construction choice rather than a
  sideboard pivot. [ddv-packages-card-oracle-local]{8} [ddv-packages-module-census]{1}
- **Tamiyo/Bilbo/Unearth recursion:** Bilbo discounts spells cast outside the hand and can recast an
  artifact, instant, or sorcery from the graveyard on attack; Unearth returns a small creature or
  cycles. The three-card cluster occurs together in three current lists, while its components occur
  more broadly. [ddv-packages-card-oracle-local]{9} [ddv-packages-module-census]{1}
- **Wasteland tempo:** three current rows use three Wasteland, two of them also registering
  main-deck Murktide. Wasteland trades itself for a target nonbasic, so this axis changes both the
  mana base and the deck's resource plan. [ddv-packages-module-census]{2}
  [ddv-packages-card-oracle-local]{10}
- **Historical ritual/tutor acceleration:** Cabal Ritual appears under 36 pilot names in 2026 and
  Spoils of the Vault under nine. Cabal Ritual adds black mana; Spoils finds a named card while
  exiling cards and losing life. Their occurrence establishes tested alternatives, not a current
  shared package. [ddv-packages-module-census]{6} [ddv-packages-card-oracle-local]{12}
- **Historical draw engines:** the refreshed store records Quantum Riddler, Deep Analysis, The One
  Ring, Night's Whisper, Lórien Revealed, Predict, and Ideas Unbound across multiple pilot names.
  They span warp/creature draw, flashback, sustained artifact draw, compact draw-two, landcycling,
  named-card milling, and a draw-three with delayed discard. [ddv-packages-module-census]{6}
  [ddv-packages-card-oracle-local]{13} [ddv-packages-card-oracle-local]{14}

### Protection and permission modules beyond the color headlines

Force of Negation is the universal current sideboard layer: all 12 lists carry it. Consign to
Memory appears in six, Duress across six main/side registrations, and Misdirection in two lists.
Misdirection is not a counterspell; it changes the target of a single-target spell and may pitch a
blue card for its cost. [ddv-packages-module-census]{4} [ddv-packages-card-oracle-local]{19}

Voice of Victory supplies a white creature version of the “opponents cannot cast during the combo
turn” role. It appears in one current main and another current sideboard. Unlike Teferi, its text is
limited to the controller's turn and supplies no bounce/draw mode. [ddv-packages-module-census]{4}
[ddv-packages-card-oracle-local]{16} [ddv-packages-release-rvr]{1}

The historical corpus also contains opening-hand Chancellor of the Annex, blue Mana Maze, flash
Opposition Agent, and Containment Priest modules. They tax a first spell or all opposing spells,
constrain consecutive same-color casting, take over library searches, or exile uncast creatures;
their pilot breadth varies from one for Mana Maze to eight for Containment Priest.
[ddv-packages-module-census]{8} [ddv-packages-card-oracle-local]{16}

Other repeated protection choices cover different timing windows: Flusterstorm and Spell Pierce
tax spells on the stack; Pact defers its mana cost; Consign targets triggers or colorless spells;
Commandeer takes a noncreature spell; Orim's Chant precludes a target player casting for the turn;
and Inquisition, Therapy, and Unmask attack the hand. Their pilot breadth ranges from two for Unmask
to 76 for Flusterstorm, without establishing that the cards belong in one combined package.
[ddv-packages-module-census]{11} [ddv-packages-card-oracle-local]{21}

### Transformational creatures and unusual threats

The current creature pivot is modular rather than monolithic: Dauthi Voidwalker appears in 11
sideboards, Barrowgoyf in ten, Murktide in seven, Bowmasters in six, and Tamiyo in two. Multiple
names appear together in several Esper and Dimir boards, allowing a pressure package to carry
graveyard denial, large flying threats, draw punishment, and cheap card flow at once.
[ddv-packages-module-census]{3}

Jace is both an alternate empty-library win and a mill/draw engine. It appears main in two rows from
one pilot and sideboard in three lists from three other pilots, so it can be either baked into the
core or held as a post-board alternate win. [ddv-packages-module-census]{2}
[ddv-packages-card-oracle-local]{11}

The historical threat inventory includes four-Cori-Steel-Cutter red boards, four-Moonshadow black
boards, Sheoldred, and Kaito. Cutter creates and equips Monk tokens on second spells; Moonshadow
grows as permanent cards enter the graveyard; Sheoldred pressures draw steps; Kaito is a
surveil/draw planeswalker that can enter through ninjutsu. [ddv-packages-module-census]{7}
[ddv-packages-card-oracle-local]{18}

### Alternate wins, graveyard hate, prison, and control

The Emrakul/Shelldock module occurs together across seven source rows from at least six pilot names:
Shelldock hides a card and can play it once a library has twenty or fewer cards. Four sideboard
Paradigm Shift appears across five rows from three names and converts the library to the graveyard
contents. These are distinct alternate-win modules; neither is evidence of current post-ban
adoption. [ddv-packages-module-census]{7} [ddv-packages-card-oracle-local]{17}

Current graveyard coverage is mostly Dauthi; the noncreature options are singleton-list choices of
Nihil Spellbomb, Surgical Extraction, or Tormod's Crypt. Historically, Leyline of the Void and
Grafdigger's Cage recur across 15 and 12 pilot names, respectively; Surgical, Nihil, Crypt, Faerie
Macabre, and Cling to Dust also recur across multiple names. These options differ between
replacement exile, whole-graveyard exile, named-card extraction, discard-to-exile, and a reusable
single-card exile spell. [ddv-packages-module-census]{5}
[ddv-packages-module-census]{8} [ddv-packages-module-census]{12}
[ddv-packages-card-oracle-local]{15} [ddv-packages-card-oracle-local]{22}

Current control packages recur through Fatal Push, Long Goodbye, Bitter Triumph, white exile,
Portable Hole, Consign, blasts, bounce, and Engineered Explosives. Engineered Explosives scales its
destructive mana value with colors spent, making it a control card whose reach is itself sensitive
to the shared mana base. [ddv-packages-module-census]{4} [ddv-packages-module-census]{5}
[ddv-packages-card-oracle-local]{20}

The Fantasticar/Mishra's Bauble engine is intentionally outside the compatibility set. Both cards
were widespread before August 10, but The Fantasticar is now banned in Legacy.
[ddv-packages-module-census]{9} [ddv-packages-ban-20260810]{1}

## Package comparison

### Dimir creature-transform baseline

The current clan registration keeps every land blue/black: four Underground Sea, Undercity
Sewers, Island, Swamp, and eight fetchlands. Its sideboard transformation is not a single threat
package: it distributes pressure across Murktide Regent, Barrowgoyf, Dauthi Voidwalker, Orcish
Bowmasters, and Tamiyo, with Unearth and stack/removal support. [ddv-packages-list-dimir-clan]{2}
[ddv-packages-list-dimir-clan]{4} [ddv-packages-list-dimir-clan]{5}

Role: preserve stable access to `{B}{B}{B}` and `{U}{U}`, then make opposing post-board cards
that are narrow against creatures less reliable. {inferred: limitation} The package does not create
a blanket “spells cannot be countered” window; its stack protection remains Force/Daze-style cards
and discard in the registered main deck. [ddv-packages-list-dimir-clan]{3}

Pile implication: no third-color source or splash spell needs to be found. Its transformational
creatures are normally independent threats, although the registered Tamiyo, Unearth, and Oracle
remain cards that can participate in draw/recursion or win lines depending on game state.
[ddv-packages-list-dimir-clan]{4}

### White: Teferi, Swords, and Prismatic Ending

Teferi is a three-mana proactive shield: while it remains in play, the opponent may cast spells
only at sorcery timing. Its −3 can bounce an artifact, creature, or enchantment and draw, while the
+1 can give the controller's sorceries flash. A permission granting flash does not override
Teferi's restriction. [ddv-packages-release-rvr]{1} [ddv-packages-release-rvr]{2}

Teferi does not silence the whole game. Triggered abilities can trigger when casting is prohibited,
and activated abilities remain usable whenever their controller has priority. {inferred: rules
application} An opposing triggered or activated ability can therefore still interact with an Oracle
line if its own text and targets allow it. [ddv-packages-rules-202608]{2}
[ddv-packages-rules-202608]{4}

Swords is one-mana instant-speed creature exile; Prismatic Ending is sorcery-speed nonland exile
whose ceiling depends on the number of mana colors spent. The life from Swords uses the creature's
last battlefield power. [ddv-packages-release-blb]{1} [ddv-packages-release-blb]{2}
[ddv-packages-card-oracle-local]{4}

The post-ban Esper 5-0 package is two Teferi main plus three Swords and two Ending side. Its mana is
three Underground Sea, Tundra, Scrubland, Undercity Sewers, Island, Swamp, eight fetchlands, and two
Petals; it retains eight sideboard creatures. [ddv-packages-list-esper-battlegrounds]{2}
[ddv-packages-list-esper-battlegrounds]{3} [ddv-packages-list-esper-battlegrounds]{4}

{inferred: mana consequence} This package asks for white once for Swords/Ending and white-blue
together for Teferi, but no double-white spell appears in the cited package. Fetching Tundra or
Scrubland exposes the added color to nonbasic-land disruption, while the retained Island and Swamp
still allow a basic-led line. [ddv-packages-list-esper-battlegrounds]{2}
[ddv-packages-list-esper-battlegrounds]{4}

Pile implication: Teferi normally protects a later Doomsday/Oracle sequence from opposing spell
casts after it resolves; it is slow and card-intensive if first drawn from the five-card pile.
Swords and Ending are answers rather than pile accelerants. Teferi's +1 technically permits a
sorcery such as Doomsday at instant timing, but no result evidence here establishes that as a
routine plan. [ddv-packages-release-rvr]{1} [ddv-packages-card-oracle-local]{5}

### Green: Veil, Carpet, and BUG removal/draw

Veil is the compact reactive shield. After it resolves, the controller's spells cannot be
countered for the turn and the controller and their permanents gain hexproof from blue and black;
it draws only if an opponent cast a blue or black spell that turn. It can itself be countered and
does nothing before resolving. [ddv-packages-release-sos]{1} [ddv-packages-release-sos]{2}

{inferred: rules application} Veil can answer a black or blue targeted discard/removal spell by
making its targets illegal and can create an uncounterability window for the combo, but it does not
grant hexproof from other colors and does not stop non-countering stack removal. Mindbreak Trap is
the explicit counterexample: it exiles spells rather than countering them and therefore works on
uncounterable spells. [ddv-packages-release-sos]{1} [ddv-packages-release-otj]{2}
[ddv-packages-release-otj]{3}

Carpet is a repeatable but opponent-dependent mana engine. It targets an opponent, counts that
opponent's Islands, makes mana of one color at a main-phase trigger, and can add mana only once per
turn through that ability. Unspent mana empties at the end of the phase. {inferred: pile
consequence} Carpet can pay a large colored requirement within the same main phase, but a pile
cannot assume a fixed output without an opposing Island, and precombat Carpet mana cannot be banked
through combat. [ddv-packages-card-oracle-local]{1} [ddv-packages-rules-202608]{5}

Witherbloom Charm is the green package's unusual pile-capable card: for `{B}{G}` it can sacrifice a
permanent to draw two, gain five life, or destroy a nonland permanent of mana value two or less.
Abrupt Decay costs the same colors, cannot be countered, and destroys a nonland permanent of mana
value three or less. Decay's uncounterability also defeats ward's countering action, although it
still needs a legal target. [ddv-packages-release-sos]{3} [ddv-packages-release-otj]{1}

There are two materially different current green packages:

- wizardpasta uses one Tropical Island with Tundra and Scrubland, one Veil main and one side, three
  Carpets side, and a four-Swords 75. This is green plus white, not pure BUG.
  [ddv-packages-list-green-white-wizardpasta]{2}
  [ddv-packages-list-green-white-wizardpasta]{3}
  [ddv-packages-list-green-white-wizardpasta]{4}
- wakame uses two Tropical Islands, two Underground Seas, Tundra, and Scrubland; three Veils and
  three Teferis main; and three each of Carpet, Swords, and Ending side. It has neither Bayou nor a
  basic Swamp. [ddv-packages-list-four-color-wakame]{2}
  [ddv-packages-list-four-color-wakame]{3}
  [ddv-packages-list-four-color-wakame]{4}

{inferred: mana consequence} The wakame package has the broadest pre-combo color schedule in this
facet: `{G}` for Veil and `{W}{U}` for Teferi alongside `{B}{B}{B}` and `{U}{U}`. Four Lotus Petals
help bridge that schedule, but the registered permanent mana base sacrifices both Bayou and basic
Swamp. [ddv-packages-list-four-color-wakame]{2}
[ddv-packages-list-four-color-wakame]{4} [ddv-packages-card-oracle-local]{5}
[ddv-packages-card-oracle-local]{6}

The clean BUG precedent uses Tropical Island plus Bayou, three Underground Sea, one Witherbloom
Charm main, and three Carpet/two Veil/two more Charm side. It demonstrates a coherent BUG mana and
card module, but its four Fantasticars make the 75 a historical starting point rather than a legal
post-ban list. [ddv-packages-list-bug-wakame-preban]{2}
[ddv-packages-list-bug-wakame-preban]{3} [ddv-packages-list-bug-wakame-preban]{4}
[ddv-packages-ban-20260810]{1}

### Red: Hexing Squelcher, Pyroblast, and Molten Collapse

Hexing Squelcher is a two-mana creature whose own spell cannot be countered. Once it resolves,
spells its controller controls cannot be countered; it has ward—pay 2 life and grants that ward to
other creatures. Ward is a triggered ability that counters the targeting spell or ability unless
the cost is paid. [ddv-packages-release-ecl]{1} [ddv-packages-rules-202608]{7}

{inferred: rules application} Squelcher therefore supplies a persistent anti-counter shield and
taxes targeted interaction with the creature plan, but it does not prevent discard, sacrifice,
non-targeted removal, spell exile, or a paid ward interaction. Mindbreak Trap again bypasses the
uncounterability clause. [ddv-packages-release-ecl]{1} [ddv-packages-release-otj]{2}
[ddv-packages-release-otj]{3}

Pyroblast is one-mana conditional interaction with blue spells or blue permanents. Molten Collapse
is a `{B}{R}` sorcery that kills a creature or planeswalker and, after descend, may also remove a
noncreature nonland permanent of mana value one or less. [ddv-packages-card-oracle-local]{2}
[ddv-packages-card-oracle-local]{3}

The representative Grixis list ran one Squelcher main, two Squelcher/two Pyroblast/one Molten
Collapse side, and a mana base with three Underground Sea, Volcanic Island, Badlands, two basics,
Undercity Sewers, eight fetchlands, and three Petals. Its sideboard also had four Barrowgoyf, so the
red protection module coexisted with a creature transformation rather than replacing it.
[ddv-packages-list-grixis-nevilshute]{2} [ddv-packages-list-grixis-nevilshute]{3}
[ddv-packages-list-grixis-nevilshute]{5}

{inferred: pile consequence} Squelcher is usually cast before Doomsday; drawing and casting a
`{1}{R}` creature from the pile consumes both a pile card and mana before the combo can use its
shield. Pyroblast can be a pile interaction card only against a blue object, while Molten Collapse
is sorcery-speed board interaction. [ddv-packages-release-ecl]{1}
[ddv-packages-card-oracle-local]{2} [ddv-packages-card-oracle-local]{3}
[ddv-packages-card-oracle-local]{5}

### Cavern is not universal splash fixing

Every representative registration includes one Cavern of Souls, but Cavern chooses one creature
type and its colored mana can cast only that type. {inferred: deckbuilding consequence} Its colored
mana can support Oracle or Squelcher only when the corresponding creature type was chosen; a single
Cavern does not simultaneously fix creatures of different types and cannot pay for Veil, Teferi,
Swords, Pyroblast, or Doomsday. [ddv-packages-card-oracle-local]{7}
[ddv-packages-list-dimir-clan]{2} [ddv-packages-list-esper-battlegrounds]{4}
[ddv-packages-list-green-white-wizardpasta]{4} [ddv-packages-list-four-color-wakame]{4}
[ddv-packages-list-grixis-nevilshute]{3}

## Coherent modules for testing

These are evidenced modules, not matchup-ranked recommendations:

| Module | Evi­denced cards | Mana registration | Evidence status |
|---|---|---|---|
| Dimir transform | Murktide, Barrowgoyf, Dauthi, Bowmasters, Tamiyo, Unearth | 4 Sea, Sewers, Island, Swamp, 8 fetch | Post-ban 5-0 [ddv-packages-list-dimir-clan]{1} [ddv-packages-list-dimir-clan]{2} [ddv-packages-list-dimir-clan]{4} |
| Esper hybrid | 2 Teferi main; 3 Swords + 2 Ending side; eight sideboard creatures | 3 Sea, Tundra, Scrubland, Sewers, two basics, 8 fetch | Post-ban 5-0 [ddv-packages-list-esper-battlegrounds]{1} [ddv-packages-list-esper-battlegrounds]{2} [ddv-packages-list-esper-battlegrounds]{3} |
| Light green/white | 1+1 Veil, 3 Carpet, four-Swords 75 | 3 Sea, Tropical, Tundra, Scrubland, Sewers, Island, 8 fetch | Post-ban 17th [ddv-packages-list-green-white-wizardpasta]{1} [ddv-packages-list-green-white-wizardpasta]{2} [ddv-packages-list-green-white-wizardpasta]{4} |
| Full green/white shield | 3 Veil + 3 Teferi main; 3 Carpet + 3 Swords + 3 Ending side | 2 Sea, 2 Tropical, Tundra, Scrubland, Sewers, Island, 8 fetch | Post-ban 5-0 [ddv-packages-list-four-color-wakame]{1} [ddv-packages-list-four-color-wakame]{2} [ddv-packages-list-four-color-wakame]{3} |
| BUG interaction | 1 Charm main; 3 Carpet, 2 Veil, 2 Charm side | 3 Sea, Tropical, Bayou, Sewers, Island, 8 fetch | Pre-ban 5-0; source 75 now illegal [ddv-packages-list-bug-wakame-preban]{1} [ddv-packages-list-bug-wakame-preban]{2} [ddv-packages-ban-20260810]{1} |
| Grixis Squelcher | 1 Squelcher main; 2 Squelcher, 2 Pyroblast, 1 Collapse side; 4 Barrowgoyf | 3 Sea, Volcanic, Badlands, Sewers, two basics, 8 fetch | Pre-ban third place [ddv-packages-list-grixis-nevilshute]{1} [ddv-packages-list-grixis-nevilshute]{2} [ddv-packages-list-grixis-nevilshute]{3} |

{inferred: testing priority from package evidence} The Esper hybrid and the two green/white modules
can be tested as registered because their exact post-ban configurations are attested. A pure BUG or
Grixis post-ban 75 requires extending from an older shell; that extension
should be labeled as a brew until current results attest the replacements and mana schedule.

## Compatibility with a shared fixed main

For this classification, “shared fixed main” means nonland main-deck cards and nonfetch lands stay
unchanged between configurations; only fetchland identities may change. This is a compatibility
audit, not a sideboard construction proposal.

| Class | Meaning under the constraint |
|---|---|
| **Native sideboard module** | Can rotate entirely through the sideboard and is castable from a UB main mana base already evidenced here. |
| **Color-preload required** | Can rotate through the sideboard only if the fixed main already carries a nonfetch source for the added color; changing fetch names alone cannot create that color. |
| **Bake into shared main** | Changes nonland main slots but not necessarily nonfetch lands; compatible only if every configuration accepts it in the one shared main. |
| **Nonfetch-base change** | Adds, removes, or repurposes a nonfetch main land and therefore cannot rotate under an only-fetchlands-may-change rule. |
| **Historical/legality excluded** | Not a current legal module or lacks a post-ban registered replacement. |

### Classification

- **Native sideboard modules:** Dimir creatures (Barrowgoyf, Dauthi, Murktide, Bowmasters, Tamiyo),
  Force of Negation/Consign/Duress/Misdirection, UB removal, colorless graveyard artifacts,
  Leyline, Cage, Moonshadow, Paradigm Shift, Mana Maze, Jace, Kaito, Sheoldred, and Phyrexian Arena
  when sideboarded, plus Engineered Explosives at the colors the fixed base can already spend. Their
  card texts and recorded colors do not require a new nonfetch source.
  [ddv-packages-module-census]{2}
  [ddv-packages-module-census]{3} [ddv-packages-module-census]{4}
  [ddv-packages-module-census]{5} [ddv-packages-module-census]{7}
  [ddv-packages-module-census]{8} [ddv-packages-module-census]{11}
  [ddv-packages-module-census]{12} [ddv-packages-card-oracle-local]{14}
  [ddv-packages-card-oracle-local]{18} [ddv-packages-card-oracle-local]{21}
  [ddv-packages-card-oracle-local]{22}
- **Color-preload required:** Swords/Ending/Portable Hole/Voice/Containment Priest/Orim's Chant
  require white;
  Veil/Carpet and BUG Charms/Decay require green; Squelcher/Pyroblast/Molten Collapse/Cutter require
  red. The attested lists meet those requirements with Tundra/Scrubland, Tropical/Bayou, or
  Volcanic/Badlands in the main. {inferred: compatibility} A fetchland substitution can select among
  duals already present but cannot make a missing white, green, or red-producing nonfetch land
  appear. [ddv-packages-list-esper-battlegrounds]{4}
  [ddv-packages-list-bug-wakame-preban]{3} [ddv-packages-list-grixis-nevilshute]{3}
  [ddv-packages-module-census]{7}
- **Bake into shared main:** Personal Tutor turbo, Tamiyo/Bilbo/Unearth recursion, Cabal
  Ritual/Spoils acceleration, the alternate draw engines, main-deck Jace, Teferi, Veil, Squelcher,
  Swords, The One Ring, and main-deck fair threats all change nonland main slots. They are
  compatible only as decisions accepted by every configuration, not as rotating modules.
  [ddv-packages-module-census]{1} [ddv-packages-module-census]{2}
  [ddv-packages-module-census]{6} [ddv-packages-list-four-color-wakame]{2}
  [ddv-packages-list-grixis-nevilshute]{2}
- **Nonfetch-base change:** the Wasteland tempo axis changes nonfetch lands; the cited green, white,
  red, and four-color registered mains also change their nonfetch dual suite. Those exact 60s cannot
  be rotated from a Dimir fixed main by changing fetchland names alone. [ddv-packages-module-census]{2}
  [ddv-packages-list-dimir-clan]{2} [ddv-packages-list-esper-battlegrounds]{4}
  [ddv-packages-list-four-color-wakame]{4} [ddv-packages-list-grixis-nevilshute]{3}
- **Sideboard-land caveat:** Emrakul/Shelldock is compatible with a fixed *main* only when Shelldock
  remains a sideboard land; moving Shelldock into the main would be a nonfetch-base change. The
  corpus contains both sideboard Shelldock registrations and one main-deck occurrence.
  [ddv-packages-module-census]{7} [ddv-packages-card-oracle-local]{17}
- **Conditional opening-hand module:** Chancellor of the Annex needs no colored source for its
  opening-hand reveal, but a UB fixed main cannot normally cast its `{4}{W}{W}{W}` body. It is
  mechanically compatible as an opening-hand effect and mana-incompatible as a conventional
  threat. [ddv-packages-card-oracle-local]{16} [ddv-packages-module-census]{8}
- **Historical/legality excluded:** Fantasticar/Bauble cannot enter a current rotation because
  The Fantasticar is banned. Pure BUG and Grixis packages remain historically evidenced, but their
  exact post-ban replacements are not attested. [ddv-packages-module-census]{9}
  [ddv-packages-ban-20260810]{1} [ddv-packages-list-bug-wakame-preban]{4}

{inferred: constraint consequence} The shared-main rule does not collapse the field to Dimir, but
it changes what “rotate a package” means. UB creature, permission, graveyard, and control modules
can rotate natively. A white, green, or red module is available only when its colored nonfetch
sources are preloaded into the one shared main, and any evidenced package with splash cards already
in the main must itself be baked into that shared main.

## Disconfirming analysis

- **“Green splash” is not synonymous with BUG.** The two attested post-ban green registrations also
  use white; the clean BUG registration is pre-ban and contains four now-banned Fantasticars.
  [ddv-packages-list-green-white-wizardpasta]{3}
  [ddv-packages-list-four-color-wakame]{2}
  [ddv-packages-list-bug-wakame-preban]{4} [ddv-packages-ban-20260810]{1}
- **“Cannot be countered” is not complete stack protection.** Wizards' Mindbreak Trap notes say
  exile works on uncounterable spells; both Veil and Squelcher therefore leave a documented bypass.
  [ddv-packages-release-otj]{2} [ddv-packages-release-otj]{3}
- **Teferi is not a blanket ability lock.** Rules allow triggered abilities to trigger even when
  spells cannot be cast and allow activated abilities with priority. [ddv-packages-rules-202608]{2}
  [ddv-packages-rules-202608]{4}
- **Carpet is not unconditional acceleration.** It needs a targeted opponent with Islands, triggers
  in a main phase, and its mana does not survive the phase. [ddv-packages-card-oracle-local]{1}
  [ddv-packages-rules-202608]{5}
- **The Grixis example is not a pure protection board.** Four Barrowgoyfs remain in the sideboard,
  so Squelcher/Pyroblast coexist with the fair-creature pivot. [ddv-packages-list-grixis-nevilshute]{5}
- **The current shell is not one tutor configuration.** Only five of 12 current lists use Personal
  Tutor, while eight use Tamiyo and several combine Bilbo with Unearth. A later shared main must pick
  or deliberately combine these axes rather than assuming they are invariant.
  [ddv-packages-module-census]{1}
- **Historical breadth does not imply present adoption.** Cabal Ritual, Spoils, One Ring,
  Emrakul/Shelldock, Paradigm Shift, Cutter, Moonshadow, Chancellor, and prison cards appear in the
  2026 store, but the current-window census does not place them in a post-ban family.
  [ddv-packages-module-census]{6} [ddv-packages-module-census]{7}
  [ddv-packages-module-census]{8} [ddv-packages-module-census]{10}

## Contradictions

| Sources | Relationship | Positions kept distinct |
|---|---|---|
| `ddv-packages-list-bug-wakame-preban`; `ddv-packages-ban-20260810` | qualifies | The registration attests a coherent BUG module and result; the later ban makes that exact 75 illegal. [ddv-packages-list-bug-wakame-preban]{1} [ddv-packages-list-bug-wakame-preban]{4} [ddv-packages-ban-20260810]{1} |
| `ddv-packages-release-ecl`; `ddv-packages-release-otj` | qualifies | Squelcher says controlled spells cannot be countered; Mindbreak Trap removes spells by exile rather than countering. [ddv-packages-release-ecl]{1} [ddv-packages-release-otj]{2} [ddv-packages-release-otj]{3} |
| `ddv-packages-release-rvr`; `ddv-packages-rules-202608` | qualifies | Teferi restricts opponent spell casting; the rules separately allow triggered abilities to trigger and activated abilities to be used with priority. [ddv-packages-release-rvr]{1} [ddv-packages-rules-202608]{2} [ddv-packages-rules-202608]{4} |

No attested sources make incompatible matchup-performance claims. Their results and dates are not
commensurable as matchup rates, so this brief does not average them into one.

## Revisit if

- A post-August-10 result registers a pure BUG or Grixis Squelcher 75 without The Fantasticar.
- The October 12, 2026 B&R announcement changes Legacy legality.
- Match-level records become available for the exact registrations, allowing card-role analysis to
  be separated from pilot and opponent-field effects.
- A rules or Oracle update changes Carpet's trigger, Teferi's casting restriction, ward, or the
  wording of Veil/Squelcher.
- The operator chooses the exact shared nonfetch mana base. Color-preload compatibility can then be
  converted from requirements to a yes/no result for each module.

## Attestation index

- `[ddv-packages-list-dimir-clan]` → `.research/attestation/ddv-packages-list-dimir-clan.md`
- `[ddv-packages-list-green-white-wizardpasta]` → `.research/attestation/ddv-packages-list-green-white-wizardpasta.md`
- `[ddv-packages-list-four-color-wakame]` → `.research/attestation/ddv-packages-list-four-color-wakame.md`
- `[ddv-packages-list-esper-battlegrounds]` → `.research/attestation/ddv-packages-list-esper-battlegrounds.md`
- `[ddv-packages-list-grixis-nevilshute]` → `.research/attestation/ddv-packages-list-grixis-nevilshute.md`
- `[ddv-packages-list-bug-wakame-preban]` → `.research/attestation/ddv-packages-list-bug-wakame-preban.md`
- `[ddv-packages-rules-202608]` → `.research/attestation/ddv-packages-rules-202608.md`
- `[ddv-packages-release-sos]` → `.research/attestation/ddv-packages-release-sos.md`
- `[ddv-packages-release-ecl]` → `.research/attestation/ddv-packages-release-ecl.md`
- `[ddv-packages-release-rvr]` → `.research/attestation/ddv-packages-release-rvr.md`
- `[ddv-packages-release-otj]` → `.research/attestation/ddv-packages-release-otj.md`
- `[ddv-packages-release-blb]` → `.research/attestation/ddv-packages-release-blb.md`
- `[ddv-packages-card-oracle-local]` → `.research/attestation/ddv-packages-card-oracle-local.md`
- `[ddv-packages-ban-20260810]` → `.research/attestation/ddv-packages-ban-20260810.md`
- `[ddv-packages-module-census]` → `.research/attestation/ddv-packages-module-census.md`

## Revisions

- 2026-08-20 — **Refresh:** Checkpoint-B scope expansion added the full evidenced module census and
  shared-fixed-main compatibility classification. The prior color-package findings remain in place.

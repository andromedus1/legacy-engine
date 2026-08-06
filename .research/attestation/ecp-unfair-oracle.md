---
source_handle: ecp-unfair-oracle
fetched: 2026-08-03
source_path: data/scryfall/oracle_cards.json
provenance: source-direct
---

# Oracle mechanics for unfair-matchup pressure points

## Source structure

The local Scryfall Oracle bulk file records current rules text, card types, and faces. The passages
below preserve only mechanics that determine how the exact Energy sideboard interacts with the
representative strategies.

## Key passages

1. **Artifact and ability constraints.** Null Rod prevents activated abilities of artifacts.
   Clarion Conqueror prevents activated abilities of artifacts, creatures, and planeswalkers. The
   One Ring's card draw is an activated tap ability; Karn's two loyalty abilities are activated;
   Emry's artifact-recast ability is activated; Mystic Forge's top-card exile is activated; LED's
   mana ability and Grindstone's milling ability are activated. Painter's continuous color-setting
   ability, Mystic Forge's top-card casting permission, and Glaring Fleshraker's two abilities are
   not activated abilities.

2. **Graveyard and alternative-entry constraints.** Leyline of the Void replaces cards entering an
   opponent's graveyard with exile. Surgical Extraction needs a nonbasic card in a graveyard as a
   target. Containment Priest replaces a nontoken creature entering without having been cast with
   exile. Reanimate and Animate Dead put a creature onto the battlefield from a graveyard; Dread
   Return does the same and can be flashed back by sacrificing three creatures. Show and Tell puts
   a qualifying permanent onto the battlefield rather than casting it.

3. **Spell-count constraint.** Deafening Silence prevents each player from casting more than one
   noncreature spell per turn. This constrains ritual/tutor chains and cantrip-then-combo turns, but
   does not prevent a creature spell after a noncreature spell.

4. **Land engines.** Planar Nexus has every nonbasic land type, including Mine, Power-Plant, Tower,
   and Urza's. Life from the Loam returns up to three lands and has dredge 3. Thespian's Stage can
   become a copy of a target land; Dark Depths makes Marit Lage after it has no ice counters.

5. **Deterministic creature kills.** Doomsday reduces the library to a chosen five-card stack;
   Thassa's Oracle wins when its devotion threshold meets the remaining-library size. Aluren lets
   either player cast creatures of mana value three or less for free and at instant speed;
   Acererak returns to its owner's hand and ventures when its entry condition applies. Balustrade
   Spy mills until a land is revealed, which mills an entire ordinary-land-free Oops library.

6. **Graveyard creature engines.** Hogaak may be cast from the graveyard using convoke and delve.
   Bridge from Below creates Zombies when its controller's nontoken creatures die while Bridge is
   in the graveyard, but exiles itself when a creature is put into an opponent's graveyard from
   the battlefield.


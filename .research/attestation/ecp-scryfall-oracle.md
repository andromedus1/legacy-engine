---
source_handle: ecp-scryfall-oracle
fetched: 2026-08-03
source_path: data/scryfall/oracle_cards.json
provenance: source-direct
---

# Oracle-card bulk data for the exact 75

## Summary

The local Scryfall Oracle bulk file (filesystem date 2026-07-03) records the rules text, mana costs,
types, and faces of every card in the exact list. The passages below group the details that govern
the deck's engines, sequencing, and sideboard effects.

## Key passages

### Creature and token engine

- Guide of Souls triggers whenever another creature enters under its controller, gaining one life
  and one energy. On attack, three energy puts two +1/+1 counters and a flying counter on a target
  attacker, which also becomes an Angel.
- Ocelot Pride has first strike and lifelink. At end step, if its controller gained life that turn,
  it creates a Cat token; with the city's blessing it additionally copies each token that entered
  that turn. Ascend requires ten permanents.
- Ajani, Nacatl Pariah creates a 2/1 Cat Warrior token on entry. When one or more other Cats die, it
  may exile and return transformed. Ajani, Nacatl Avenger can grow Cats, create another Cat, or—with
  another red permanent—deal damage equal to creature count when that token is created.
- Voice of Victory has mobilize 2: attacking creates two tapped-and-attacking Warriors that are
  sacrificed at the beginning of the next end step. Opponents cannot cast spells during its
  controller's turn.
- Goblin Bombardment sacrifices a creature to deal one damage to any target.

### Interaction and protection

- Cabal Therapy chooses a nonland card name; the target player reveals their hand and discards all
  cards with that name. Its flashback cost is sacrificing a creature.
- Thoughtseize reveals the target player's hand, discards a chosen nonland card, and costs its
  caster two life as part of the effect. Swords to Plowshares exiles a target creature and grants
  its controller life equal to its power.
- Hexing Squelcher cannot be countered, makes its controller's spells uncounterable, has ward—pay 2
  life, and grants that same ward ability to the controller's other creatures.
- Orcish Bowmasters has flash and triggers on entry and each opponent draw beyond the first draw in
  that opponent's draw step, dealing one damage and amassing Orcs 1.
- Wasteland sacrifices to destroy a target nonbasic land. Karakas can return a target legendary
  creature to its owner's hand. The two surveil duals enter tapped and surveil one.

### Amped Raptor

- Amped Raptor has first strike. On entry it gives two energy, then, only if cast from hand, exiles
  cards until a nonland appears and permits that card to be cast by paying energy equal to mana
  value instead of mana. Because all nonlands in this exact main deck cost one or two, its own two
  energy is enough to cast every legal hit, subject to targets and other casting restrictions.

### Sideboard text

- Leyline of the Void may begin on the battlefield from the opening hand and exiles cards that
  would enter an opponent's graveyard.
- Surgical Extraction can cost either one black mana or two life. It targets a nonbasic card in a
  graveyard, then searches that card's owner’s graveyard, hand, and library for any number of cards
  with the same name and exiles those found.
- Deafening Silence limits each player to one noncreature spell per turn.
- Containment Priest has flash and exiles a nontoken creature that would enter without being cast.
- Null Rod prevents activated abilities of artifacts from being activated.
- Clarion Conqueror prevents activated abilities of artifacts, creatures, and planeswalkers from
  being activated.


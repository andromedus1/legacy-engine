---
source_handle: ddp-card-capabilities
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Registered card capability rows

The local `cards` table provides card names, type lines, and Oracle text for the registered mechanisms.

## Key passages

- `Personal Tutor` searches for a sorcery and places it on top of its controller's library.
- `Bilbo, Thief in the Night` reduces the cost of spells cast from outside its controller's hand
  and can cast an artifact, instant, or sorcery from that controller's graveyard when it attacks.
- `Tamiyo, Inquisitive Student` investigates on attack and transforms after its third-card draw condition.
- `Murktide Regent` uses delve and receives counters as instants and sorceries leave the graveyard.
- `Wasteland` sacrifices to destroy a nonbasic land.
- `Veil of Summer` can draw against blue/black spells and makes the controller's spells uncounterable for the turn.
- `Carpet of Flowers` produces main-phase mana based on an opponent's Islands.
- `Hexing Squelcher` cannot be countered and makes the controller's spells uncounterable while it remains.
- `Teferi, Time Raveler` restricts opposing spell timing and can return an artifact, creature, or
  enchantment while drawing.
- `Swords to Plowshares` exiles a target creature and gives its controller life equal to its power.
- `Witherbloom Charm` can trade a sacrificed permanent for two cards, gain five life, or destroy a
  nonland permanent with mana value two or less.
- `Barrowgoyf` has deathtouch and lifelink, sizes itself from card types in all graveyards, and can
  mill cards and recover a creature after dealing combat damage to a player.
- `Cori-Steel Cutter` creates and equips a prowess Monk on a second spell and requires red to equip.
- `Moonshadow` removes a -1/-1 counter when permanent cards enter its graveyard.
- `Chancellor of the Annex` can tax the opponent's first spell from the opening hand and taxes later opposing spells.
- `Paradigm Shift` exiles a library and shuffles the graveyard back.
- `Shelldock Isle` can play its hidden card when a library has twenty or fewer cards.
- `Emrakul, the Aeons Torn` cannot be countered and grants an extra turn when cast.
- `Quantum Riddler` draws on entry and can draw an additional card with one or fewer cards in hand.
- `Jace, Wielder of Mysteries` wins on a draw with an empty library.
- `Sheoldred, the Apocalypse` gains life on its controller's draws and drains opponents' draws.

## Revisions

- 2026-08-20 — Corrected Teferi's bounce qualifier and added the directly queried Bilbo, Swords,
  Witherbloom Charm, and Barrowgoyf rows required by the mechanism table.

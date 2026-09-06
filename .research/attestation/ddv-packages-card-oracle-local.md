---
source_handle: ddv-packages-card-oracle-local
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Local card Oracle snapshot — remaining splash cards

## Summary

The `cards` table in the refreshed project database provides mana costs, types, colors, and Oracle
text for the remaining splash cards not quoted from a fetched Wizards release-note page.

## Key passages

- `Carpet of Flowers` is a `{G}` enchantment. At the beginning of each of its controller's main
  phases, if that controller has not added mana with the ability that turn, they may add X mana of
  one color, where X is the number of Islands the targeted opponent controls.
- `Pyroblast` is a `{R}` instant with two modes: counter a target spell if it is blue, or destroy a
  target permanent if it is blue.
- `Molten Collapse` is a `{B}{R}` sorcery. It chooses one mode, or both if its caster descended that
  turn: destroy a target creature or planeswalker; and/or destroy a target noncreature nonland
  permanent with mana value one or less.
- `Prismatic Ending` is an `{X}{W}` sorcery whose converge effect exiles a target nonland permanent
  whose mana value does not exceed the number of mana colors spent to cast it.
- `Doomsday` costs `{B}{B}{B}` and searches its controller's library and graveyard for five cards,
  exiles the rest, orders the chosen cards on top of the library, and makes its controller lose half
  their life rounded up.
- `Thassa's Oracle` costs `{U}{U}`. Its enters-the-battlefield ability wins when its controller's
  devotion to blue is at least the number of cards remaining in that player's library.
- `Cavern of Souls` chooses one creature type as it enters. Its colored mana can be spent only on a
  creature spell of that type, and a spell using that mana cannot be countered.
- `Personal Tutor` costs `{U}` and puts a revealed sorcery from its controller's library on top of
  that library after shuffling.
- `Bilbo, Thief in the Night` reduces by `{1}` spells its controller casts from outside their hand
  and may cast an artifact, instant, or sorcery from the graveyard when Bilbo attacks. `Unearth`
  returns a creature of mana value three or less from the graveyard or cycles for `{2}`.
- `Wasteland` makes colorless mana or sacrifices to destroy a target nonbasic land.
- `Jace, Wielder of Mysteries` costs `{1}{U}{U}{U}` and replaces a draw from an empty library with a
  win. Its +1 mills a target player for two and draws a card.
- `Cabal Ritual` costs `{1}{B}` and adds three black, or five black at threshold. `Spoils of the
  Vault` costs `{B}`, reveals to a named card, puts it in hand, exiles the other revealed cards, and
  loses one life per card exiled this way.
- `Deep Analysis` draws two and has a flashback cost of `{1}{U}` plus three life. `Night's Whisper`
  draws two and loses two life. `Quantum Riddler` is a warpable creature that draws on entry and
  adds an extra card to draws while its controller has one or fewer cards. `Predict` mills a named
  card to draw two on a correct name or one otherwise. `Ideas Unbound` draws three and creates an
  end-step discard of three. `Lórien Revealed` draws three or islandcycles for `{1}`.
- `The One Ring` grants protection from everything until its controller's next turn when cast,
  then uses burden counters to draw increasing numbers of cards and lose life. `Phyrexian Arena`
  draws one additional card and loses one life at each controller upkeep.
- `Leyline of the Void` can begin on the battlefield from an opening hand and exiles cards that
  would enter an opponent's graveyard. `Grafdigger's Cage` stops creature cards entering from
  graveyards/libraries and stops spells being cast from those zones.
- `Chancellor of the Annex` can be revealed from an opening hand to tax the opponent's first spell
  and taxes opposing spells while in play. `Voice of Victory` stops opponents casting spells during
  its controller's turn. `Opposition Agent` controls opposing library searches. `Containment
  Priest` exiles nontoken creatures that enter without being cast. `Mana Maze` stops a player from
  casting a spell that shares a color with the most recently cast spell that turn.
- `Emrakul, the Aeons Torn` is an uncounterable fifteen-mana creature with a cast trigger for an
  extra turn. `Shelldock Isle` hides one of four cards and may play it without its mana cost while a
  library has twenty or fewer cards. `Paradigm Shift` exiles its controller's library and shuffles
  that player's graveyard into the library.
- `Cori-Steel Cutter` makes a Monk token on the controller's second spell each turn and equips it;
  `Moonshadow` grows from a one-mana 1/1 toward 7/7 as permanent cards enter its controller's
  graveyard; `Sheoldred, the Apocalypse` gains life on controller draws and drains opponents on
  theirs; `Kaito, Bane of Nightmares` is a surveil/draw planeswalker that can ninjutsu from hand.
- `Misdirection` may exile a blue card instead of paying `{3}{U}{U}` and changes the target of a
  single-target spell.
- `Engineered Explosives` uses the colors spent on X to determine its charge counters, then costs
  two and sacrifices to destroy each nonland permanent with that mana value.
- `Flusterstorm` is a `{U}` storm counter for an instant or sorcery unless `{1}` is paid per copy;
  `Spell Pierce` taxes a noncreature spell by `{2}`; `Pact of Negation` costs zero immediately but
  requires `{3}{U}{U}` at the next upkeep; and `Consign to Memory` replicates to counter triggered
  abilities or colorless spells. `Commandeer` may pitch two blue cards to take a noncreature spell.
  `Orim's Chant` costs `{W}` to stop one target player casting spells for the turn. `Inquisition of
  Kozilek`, Cabal Therapy, and Unmask are black hand-disruption spells with different selection and
  alternate/flashback costs.
- `Dauthi Voidwalker` replaces cards entering an opponent's graveyard with void-counter exile and
  can sacrifice to play one such card. `Nihil Spellbomb` and `Tormod's Crypt` sacrifice to exile a
  graveyard. `Surgical Extraction` exiles copies of one named nonbasic card after targeting one in a
  graveyard and may be paid with life. `Faerie Macabre` discards to exile up to two graveyard cards.
  `Cling to Dust` exiles one graveyard card for life or a draw and has escape.

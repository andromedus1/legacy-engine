---
source_handle: ddv-compare-wide-cards
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Wide-net Doomsday card affordances

## Source structure

The `cards` table was queried read-only by exact card name. The passages paraphrase mana cost,
type, and Oracle text. They describe card capabilities only and carry no prevalence or outcome
claim.

## Key passages

1. **Tutor and selection.** Personal Tutor costs one blue and puts a revealed sorcery from the
   library on top. Flow State costs one and a blue, looks at three cards, and normally keeps one;
   with both an instant and sorcery in the graveyard it keeps two.

2. **Bilbo/Unearth value engine.** Bilbo costs one and a blue, reduces by one the cost of spells
   cast from outside the hand, and may cast an artifact, instant, or sorcery from the graveyard when
   attacking. Unearth costs one black and returns a creature of mana value three or less from the
   graveyard, with cycling for two generic mana.

3. **Persistent casting restrictions.** Voice of Victory costs one and a white and prevents
   opponents from casting spells during its controller's turn. Teferi's restriction instead limits
   opponents to sorcery timing. Hexing Squelcher makes its controller's spells uncounterable while
   it remains on the battlefield.

4. **Free or alternate-cost stack tools.** Misdirection may exile a blue card rather than pay five
   mana and changes the target of a spell with one target. Commandeer may exile two blue cards
   instead of paying seven mana and takes control of a noncreature spell. Chancellor of the Annex
   may be revealed from the opening hand to tax the opponent's first spell by one mana; on the
   battlefield it taxes every opposing spell the same way.

5. **Colorless and permanent interaction.** Consign to Memory costs one blue, has replicate for one
   generic, and counters a triggered ability or colorless spell. Hide on the Ceiling costs X and a
   blue and temporarily exiles X artifacts and/or creatures until the next end step. Witherbloom
   Charm costs black-green and chooses among sacrificing a permanent to draw two, gaining five
   life, or destroying a nonland permanent of mana value two or less.

6. **Alternate wins.** Paradigm Shift costs one and a blue, exiles the controller's library, then
   shuffles their graveyard into their library. Jace, Wielder of Mysteries costs one and three blue
   and replaces a draw from an empty library with winning the game.

7. **Unusual fair threats.** Moonshadow costs one black, has menace, enters with six negative
   counters, and removes one when permanent cards enter its controller's graveyard. Cori-Steel
   Cutter costs one and a red and creates a prowess Monk after its controller's second spell each
   turn, then may equip it; the equipped creature gets power/toughness, trample, and haste.

8. **Value permanents.** The One Ring costs four generic, is indestructible, grants protection from
   everything until the controller's next turn when cast, and draws increasing cards for burden
   counters while causing upkeep life loss. Quantum Riddler is a five-mana flying creature with a
   two-mana warp cost; it draws on entry and increases draws while its controller has at most one
   card in hand.

9. **Transformational blue and black threats.** Barrowgoyf, Murktide Regent, and Tamiyo provide
   black lifelink/deathtouch, a blue flying delve threat, and a one-mana flying value creature,
   respectively. Their text does not require adding a third color to a Dimir shell.


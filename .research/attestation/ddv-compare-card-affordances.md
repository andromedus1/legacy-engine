---
source_handle: ddv-compare-card-affordances
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Splash-card Oracle-text affordances

## Source structure

The `cards` table was queried read-only by exact card name. It contains mana cost, type line, and
Oracle text. These passages describe card capabilities only; they contain no matchup or performance
measurement.

## Key passages

1. **Veil of Summer (`{G}`, instant).** If an opponent cast a blue or black spell this turn, Veil
   draws a card. For the turn it makes the controller's spells unable to be countered and gives the
   controller and their permanents hexproof from blue and black.

2. **Carpet of Flowers (`{G}`, enchantment).** At the beginning of each of its controller's main
   phases, once per turn, Carpet may add mana of one color equal to the number of Islands controlled
   by a targeted opponent.

3. **Teferi, Time Raveler (`{1}{W}{U}`, planeswalker).** Teferi restricts each opponent to casting
   spells only when they could cast a sorcery. Its minus-three returns an artifact, creature, or
   enchantment to its owner's hand and draws a card.

4. **Swords to Plowshares (`{W}`, instant) and Prismatic Ending (`{X}{W}`, sorcery).** Swords exiles
   a creature and gives its controller life equal to its power. Ending exiles a nonland permanent
   whose mana value is no greater than the number of mana colors spent on it.

5. **Hexing Squelcher (`{1}{R}`, creature).** The Squelcher spell itself cannot be countered. While
   it remains on the battlefield, its controller's spells cannot be countered. It has ward requiring
   payment of 2 life, and grants the same ward to other creatures.

6. **Pyroblast and Red Elemental Blast (`{R}`, instants).** Each can counter a blue spell or destroy
   a blue permanent. The two cards differ in targeting syntax, but the stored operational modes are
   the same at this comparison's level.

7. **Abrupt Decay (`{B}{G}`, instant).** Decay cannot be countered and destroys a nonland permanent
   with mana value three or less. **Force of Vigor (`{2}{G}{G}`, instant)** can exile a green card
   instead of paying its mana cost when it is not the controller's turn and destroys up to two
   artifacts and/or enchantments.

8. **Transformational creatures.** Barrowgoyf costs `{2}{B}`, has deathtouch and lifelink, scales
   from card types in all graveyards, and may mill then recover a creature after combat damage.
   Murktide Regent costs `{5}{U}{U}`, has delve and flying, enters larger for exiled instants and
   sorceries, and grows when one leaves the graveyard. Tamiyo costs `{U}`, flies, makes a Clue when
   attacking, and transforms when its controller draws a third card in a turn.

9. **Exile is not countering.** Mindbreak Trap (`{2}{U}{U}`, instant) may cost zero after an opponent
   casts three spells in a turn and exiles targeted spells. Its Oracle text does not use the word
   “counter.” Force of Negation, by contrast, says to counter a noncreature spell and then exile it
   if countered this way.

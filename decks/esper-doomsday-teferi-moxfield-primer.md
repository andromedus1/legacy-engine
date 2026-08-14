# Esper Doomsday — Teferi sideboard

List: [`decks/esper-doomsday-teferi-moxfield.txt`](esper-doomsday-teferi-moxfield.txt)

This is a current, legal composite built from two proven shells:

- The maindeck is SmokyboyJFF's **August 10, 2026 5-0**, the first post-ban Doomsday result in the
  local corpus. It is preserved card for card.
- The sideboard is thescuba96's **July 28, 2026 5-0** Esper package, preserved card for card: two
  white duals, three Teferi, three Swords, two Prismatic Ending, three Force of Negation, and two
  Consign to Memory.

The splice is deliberate. **The Fantasticar was banned in Legacy on August 10**, so the successful
pre-ban Esper lists cannot be registered unchanged. The post-ban maindeck replaces the Fantasticar
plan with Personal Tutor, a second Oracle, extra cyclers, and Unearth; the Teferi board remains
legal and mechanically compatible. No post-ban result has yet validated this exact combined 75, so
treat the maindeck as proven, the sideboard as proven in the prior shell, and their combination as
an evidence-backed first draft rather than a solved list.

Sources: [post-ban 5-0 maindeck](https://www.mtgo.com/decklist/legacy-league-2026-08-1010831) and
[Esper Teferi 5-0 shell](https://www.mtgo.com/decklist/legacy-league-2026-07-2810831). Local corpus
current through 2026-08-10.

## The plan

Game one is streamlined UB Doomsday. Cantrips and three Personal Tutors find Doomsday; discard,
Daze, and Force of Will clear the stack; Ritual, Petal, and LED compress the setup turn; Oracle
wins after Doomsday leaves five cards in the library.

Post-board, Tundra and Scrubland enter with the white interaction. Teferi forces opposing blue
decks to fight on your main phase, then shuts off their counters and removal during the combo turn.
Swords and Ending clear hate creatures, clocks, Chalice, and other cheap lock pieces. Consign and
Force of Negation reinforce the stack against combo and colorless decks.

This is still a combo deck. The white package makes the combo turn safer and clears specific
obstacles; it does not turn the deck into Esper Control.

## Core card roles

**Personal Tutor.** Usually finds Doomsday, but it can find Flow State when the missing resource is
cards rather than the payoff. Because the card goes on top, pair Tutor with a cantrip or plan to
draw it next turn. Tutor exposes your plan and is poor into Bowmasters pressure, so sequence it with
purpose rather than firing it automatically.

**Two Thassa's Oracle.** The second copy gives resilience to discard, exile effects, and sideboard
games where the first Oracle is answered. It also changes pile construction: do not assume piles
from one-Oracle Fantasticar lists transfer unchanged.

**Flow State.** With an instant and a sorcery in the graveyard, it puts two of the top three cards
into hand. It does not say “draw,” so it does not trigger Orcish Bowmasters. In a pile it can move
multiple cards while leaving the library small enough for Oracle.

**LED, Street Wraith, Edge of Autumn.** These are pile resources. LED is usually pile mana; Street
Wraith cycles for two life; Edge cycles by sacrificing a land. They let a pile advance without
ordinary mana, but every one has a real resource condition. Recount life, lands, and colors before
locking the five.

**Unearth.** Rebuys a discarded or countered Oracle and can cycle when dead. It makes graveyard
hate somewhat more relevant than it was in Fantasticar builds, but the primary Doomsday/Oracle plan
still does not depend on the graveyard.

**Cavern of Souls.** Name **Merfolk** for Thassa's Oracle. It protects the spell from counters, not
the Oracle triggered ability; Consign to Memory can still counter that trigger.

**Teferi, Time Raveler.** His static is the reason for the splash: after he resolves, the opponent
cannot cast counters or removal during your turn. His -3 returns an artifact, creature, or
enchantment and draws a card, so it can unlock Chalice, Sphere, Thalia, Collector Ouphe, or a clock.
It cannot bounce lands or planeswalkers, and it does not stop triggered abilities already on the
battlefield.

## Mulligans

Keep hands that answer three questions:

1. Can the hand produce black mana, preferably BBB on schedule?
2. Does it contain Doomsday or a credible route to it?
3. Does it protect the attempt or survive the opponent's first push?

Good blind keeps include two lands, a cantrip/Tutor, disruption, and a payoff; or a fast Doomsday
hand with Ritual/Petal and protection. A Tutor hand needs either a draw effect or enough time to
wait a turn. Ship no-black-source hands, acceleration with no action, and fragile one-land hands
that need multiple perfect draws. Do not count LED as ordinary turn-one mana.

Against fair blue, prioritize discard plus velocity and accept a slower hand. Against faster combo,
keep interaction plus a clock; disruption without a route to Doomsday gives them too many redraws.
Against creature decks, prize speed and avoid speculative Thoughtseize/Street Wraith life payments.

## Building and executing piles

This primer intentionally does not prescribe one “universal” five. Piles depend on the cards in
hand, available mana, land count, life total, cards already exiled, and the answer being played
around. Use this checklist every time:

1. After Doomsday, the library has five cards. Oracle wins only if blue devotion is at least the
   cards remaining when its trigger resolves.
2. Count available draws: cantrips, two Street Wraith, two Edge of Autumn, Flow State, and the normal
   draw step.
3. Count mana by color after paying BBB. Reserve UU for Oracle unless LED or Cavern changes the line.
4. Decide which interaction matters: spell counter, Oracle-trigger counter, removal, Bowmasters,
   Wasteland, or a tax permanent.
5. Put a redundant Oracle or Unearth into the pile only when it answers the actual failure mode.

Against Bowmasters, prefer a same-turn line with the fewest true draws. Against soft counters, make
them fight over Doomsday while discard/Daze still matters. Against permission, Cavern protects the
Oracle spell and Teferi broadly closes the casting window, but neither stops Consign on the Oracle
trigger.

## Sideboard cards

- **3 Teferi:** fair blue, the mirror, and matchups where a bounceable permanent blocks the combo.
- **3 Force of Negation:** Show and Tell, Reanimator, storm, the mirror, and noncreature lock pieces.
- **2 Consign to Memory:** Oracle and other triggered abilities; colorless spells from Eldrazi,
  Mystic Forge, Blue Artifacts, and Tron. Replicate when one target is not enough.
- **3 Swords to Plowshares:** fast creatures and hatebears. Efficient, but the life can matter when
  trying to win with damage is not the plan anyway.
- **2 Prismatic Ending:** Chalice, Vial, cheap hate creatures, and other nonland permanents. With
  Underground Sea plus Tundra or Scrubland it can spend white, blue, and black and reach converge
  three.
- **Tundra and Scrubland:** bring both with any meaningful white package. They preserve blue and
  black access while adding white, but cost actual sideboard slots and increase Wasteland exposure.

## Sideboarding discipline

Oracle, LED, Street Wraith, Edge of Autumn, and the mana engine determine which piles exist. Avoid
boarding them out unless you have practiced the resulting configuration. The normal cuts are:

- Daze on the draw, against Ancient Tomb, or in long games where opponents easily pay.
- Duress and Thoughtseize against creature-heavy decks.
- One Personal Tutor when the opponent punishes topdeck tutors or the game becomes attritional.
- One Flow State or one acceleration piece when slowing down for Teferi—but do not hollow out the
  combo merely to use every sideboard card.

The plans below are starting points. The post-August 10 matchup window is only one ingested result,
so mechanics carry more weight than rates right now.

## Matchup guide

### Dimir Tempo / Dimir Midrange

**In:** 3 Teferi, 1 Tundra, 1 Scrubland; consider 2 Swords if you saw must-kill Goyfs or Bowmasters.

**Out:** 3 Daze on the draw, 1 Personal Tutor, 1 Lotus Petal; for Swords, trim Duress and a second
Tutor. Keep Thoughtseize to clear Teferi, and remember that Teferi itself must survive their board.
On the play, retain one or two Daze and trim another Tutor/velocity card instead.

### Izzet Delver

**In:** 3 Swords, 1 Tundra, 1 Scrubland; optionally 2 Teferi on the play if their configuration is
counter-heavy and slow.

**Out:** Duress, 3 Thoughtseize, then Daze on the draw. Do not overload on three-mana Teferis while
behind to a one-drop. Remove the clock, preserve life, and force one protected combo turn.

### Azorius/Jeskai and slower permission decks

**In:** 3 Teferi, 1 Tundra, 1 Scrubland, 2 Force of Negation; add Ending when Chalice or a cheap
permanent lock appears.

**Out:** 3 Daze on the draw, 1 Lotus Petal, 1 Personal Tutor, 1 Flow State, 1 Edge of Autumn. Keep
discard: resolving Teferi usually demands the same opening as resolving Doomsday.

### Blue Artifacts / Mystic Forge / Eldrazi / Tron

**In:** 2 Consign, 2 Prismatic Ending, 3 Force of Negation, both white lands; add Teferi if their
locks are bounceable and the matchup is slow enough.

**Out:** 3 Daze against Ancient Tomb mana, Duress, 2-3 Thoughtseize, 1 Personal Tutor, and small
amounts of velocity/acceleration to match the number brought in. Consign counters colorless spells
and their triggers; Ending handles resolved Chalice at zero or one. Do not bring all twelve spells
in just because they have text—preserve the kill.

### Show and Tell / Aluren

**In:** 3 Force of Negation and 2 Consign.

**Out:** 1 Unearth, 1 Personal Tutor, 1 Flow State, 1 Edge of Autumn, 1 Lotus Petal. Keep Daze and
discard on the play. Consign does not counter Show and Tell itself, but it can answer important
colorless or triggered follow-ups; Force the enabler whenever possible.

### Reanimator

**In:** 3 Force of Negation, 3 Swords, 1 Tundra, 1 Scrubland.

**Out:** 1 Unearth, 1 Personal Tutor, 1 Flow State, 1 Edge of Autumn, 1 Lotus Petal, 2 Street Wraith,
1 Duress. Keep Thoughtseize, Daze, and Force of Will. This board has no Containment Priest or graveyard
lock, so it fights on the stack and removes the creature after it lands; that is functional, not a
hard lock.

### Energy / Death & Taxes

**In:** 3 Swords, 2 Prismatic Ending, 1 Tundra, 1 Scrubland; add Teferi only if multiple Chalice,
Thalia, or other bounceable locks make it worthwhile.

**Out:** Duress, 3 Thoughtseize, and up to 3 Force of Will in the least explosive creature matchup.
Kill Thalia, Guide of Souls, or Collector Ouphe immediately. Ending exiles Vial and cheap lock
pieces; Teferi is an unlock button, not the primary plan.

### Lands

**In:** 3 Force of Negation; add 2 Consign if colorless lock pieces are prominent.

**Out:** 3 Daze, then 1 Personal Tutor and 1 Flow State. Stay fast. White removal and Teferi are
usually poor into Wasteland, Maze of Ith, and Marit Lage; Teferi is reasonable only when a Sphere
effect is the card that matters.

### Doomsday mirror / spell combo

**In:** 3 Force of Negation, 2 Consign; against the mirror also bring 3 Teferi plus both white lands.

**Out:** Daze on the draw, Unearth against non-discard combo, one Personal Tutor, one Flow State,
and the slowest cycling/acceleration pieces needed to finish the swap. Consign on an opposing Oracle
trigger wins even through Cavern. Against faster storm, leave Teferi and the white lands out unless
their post-board plan is unusually permission-heavy.

## Practice plan

1. Goldfish ten hands with the post-ban 60 and state the intended pile before casting Doomsday.
2. Practice with each cycler unavailable, then with LED unavailable.
3. Rehearse double-Oracle and Unearth recovery lines.
4. Play post-board hands that must develop BBB and then WU through Wasteland.
5. Practice Teferi -3 on Chalice/Thalia followed by a same-turn combo, including the mana count.

The deck rewards resource accounting more than memorizing a single pile. Slow down, recount the
library and mana, and choose the line that gives the opponent the fewest live answers.

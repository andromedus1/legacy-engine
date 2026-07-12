# Dimir Tempo — Barrowgoyf

The grind-forward build of Dimir Tempo, and the one winning the build war: since the May bans,
Barrowgoyf lists outnumber the old Nethergoyf configuration roughly five to one, and they've
posted the strongest results of any Dimir configuration in the young Fantasticar-era data
(around 59% over the first weeks, small sample).

## This deck's plan

Classic Dimir tempo-attrition: tax spells with Daze and Force of Will, strip hands with a full
four Thoughtseize, kill everything cheaply, and win with undercosted threats. Every removal
exchange feeds the payoff — this deck is happy to trade one-for-one all day because its threats
are better than yours.

The threat suite is built to close from the top of an empty board. **Barrowgoyf** ({2}{B}) is a
deathtouch, lifelink Lhurgoyf whose power equals the number of card types across *all* graveyards
(toughness one higher) — after a few exchanges it's a 4/5-plus that blocks anything, races anything,
and refills your hand when it connects. **Murktide Regent** delves the graveyard the attrition war
fills. **Kaito, Bane of Nightmares** is a planeswalker that becomes a hexproof 3/4 on your turn and
draws you cards whenever an opponent lost life — nearly impossible to kill on the swing back.
**Tamiyo, Inquisitive Student** is a one-mana flyer that flips into a card-advantage engine.
**Orcish Bowmasters** flashes in to snipe a mana dork or an X/1, and punishes every extra card the
opponent draws — Brainstorm, a second Ponder, The One Ring, Faithless Looting, Echo of Eons all
feed it a ping plus an Orc.

**Flow State** ({1}{U}, sorcery) is the newest addition and now a consensus four-of: "Look at the
top three cards... put one into your hand. If there is an instant card and a sorcery card in your
graveyard, instead put two of them into your hand." It replaced the old Stifle and Mishra's Bauble
velocity package. Play it like a sorcery-speed engine, not a trick: a fetch plus any cantrip turns
it on by turn two, and every Flow State already in the graveyard upgrades the next one.

**Snuff Out** rounds out the removal — with a Swamp in play it's free ("pay 4 life rather than pay
this spell's mana cost; destroy target nonblack creature"), which matters when you're tapping out
for Kaito or Murktide. The catch lives in its text: **nonblack**. It can't touch a black creature,
so it whiffs on the mirror's Barrowgoyfs and Dauthi Voidwalkers, on Hogaak, and on a Marit Lage
token (which is also indestructible). Point it at Murktide, Tamiyo, mana dorks, and white/red
beaters.

The build's identity in one line: it trades equity against Energy, Lands, and Death & Taxes for
the best Izzet and Eldrazi numbers of any Dimir configuration. Those three creature decks are
genuinely bad matchups — the plans below don't pretend otherwise, they just give you the best
fighting chance.

Two metagame notes worth tracking. First, the June 29 Candelabra ban gutted Tron, and its old prey
— Reanimator, Blue Artifacts, Energy — should pick up share; two of those three are bad news, so
respect the drift. Second, the Flow State build of Izzet Delver plays closer to even against this
deck than classic Delver does — check for Flow State in game one before assuming the usual edge.

## Mulligan keep guide

This is a cantrip-dense deck — twelve one-mana card-selection spells (Brainstorm, Ponder, Flow
State) plus fetchlands mean you dig hard, so you can keep hands that a clunkier deck couldn't. But
digging is not a plan by itself. A keep needs a castable mana base (you're a two-color deck leaning
on duals and fetches — one land plus a fetch that finds the second color is fine; a hand that can't
produce black *and* blue by turn two is shaky) and it needs to answer the question "what is this
hand actually doing?" Match that answer to what you're facing.

**Against fair blue** (Izzet Delver, the mirror, Azorius/Jeskai midrange): you want cantrip density
plus one or two pieces of interaction and enough land to operate. The tempo war is won by trading
efficiently and landing a sticky threat, not by durdling. A hand of three threats and no interaction
gets run over; a hand of all counters and no clock durdles into their card advantage. *Keep:* two
lands, Ponder, Thoughtseize, Fatal Push, a threat. *Ship:* four lands, Murktide, Kaito, no cheap
interaction — nothing happens before turn four.

**Against combo** (Show and Tell, Doomsday, storm/TES/Necro, Reanimator, Oops, Cephalid): the keep
must contain disruption that bites — Force of Will, Daze, or Thoughtseize — *and* a clock. Removal
alone is close to blank against a deck that wins without attacking. Thoughtseize plus a counter plus
any threat is a snap keep even on six. A hand with two removal spells and no disruption is a
mulligan no matter how many lands it has.

**Against creature decks** (Energy, Death & Taxes, Eldrazi, Cradle Control, Red Stompy): you want to
be removal-heavy — Fatal Push, Snuff Out, Orcish Bowmasters, and the lands to cast them. Counter-
heavy hands drown here, because their threats resolve faster than you can hold them and they rebuild
through your one-for-ones. Keep removal and a way to stabilize; ship the hand that's three
counterspells and a Murktide.

**Wasteland-aggression hands:** on the play, a hand of Wasteland plus Daze plus a one-drop threat
plus a disruption spell is a premium keep against any greedy mana base — Tron, Lands, Eldrazi,
Cradle Control. You're not durdling; you're denying their second or third color and racing before
they set up. Lean into these keeps on the play and be greedier about them the slower the opponent is.

## Matchups & sideboard

The fifteen sideboard cards, and their jobs: **2 Consign to Memory** (colorless spells + triggered
abilities — Eldrazi, artifact combo), **2 Force of Negation** (free counter vs noncreature combo),
**2 Hydroblast** (counter or destroy anything red), **2 Sheoldred's Edict** (sacrifice — ignores
ward, hexproof, indestructible), **1 Damping Sphere** (anti-ramp, anti-storm), **1 Dauthi
Voidwalker** (graveyard exile + unblockable clock), **1 Grafdigger's Cage** (reanimation and
library-to-battlefield hate), **1 Mystical Dispute** (cheap counter vs blue), **1 Null Rod**
(shuts off artifact mana and artifact combos), **1 Surgical Extraction** (targeted graveyard hate),
**1 Toxic Deluge** (scalable sweeper). Every plan below keeps IN and OUT equal.

Each header carries the deck's colors, its share of the field, and our win rate where the data
supports one.

#### 1. Tron (C) — 9.3% of the meta · ~52% for us (raw 54, n=13)

Stale number — this was the format's top deck before the June 29 Candelabra ban, and post-ban lists
are still shaking out, so treat share and record as soft. **Their plan:** Karn, the Great Creator,
The One Ring, Ugin, Kozilek's Command, and Grim Monolith into an early, oppressive artifact engine;
Emrakul as the top end. **How to spot it:** unmistakable — the Urza's Mine/Tower/Power Plant land
trio (all 100%) plus Planar Nexus, backed by Ancient Tomb and Urza's Saga (both 88%). Turn-one Grim
Monolith, Voltaic/Manifold Key, or Kozilek's Command seals the read. **Our plan:** Consign to Memory
is excellent — The One Ring, Karn, Ugin, Grim Monolith, and Kozilek's Command are all colorless
spells you counter for one mana. Damping Sphere neuters their big mana (a land tapped for two or more
produces only colorless), and Null Rod turns off Grim Monolith, the keys, and The One Ring's draw.
Thoughtseize the engine piece before they're online. **In:** 1 Damping Sphere, 1 Null Rod, 2 Consign
to Memory. **Out:** 3 Fatal Push, 1 Snuff Out (almost no creatures to kill). Counts: 4 / 4.

#### 2. Izzet Delver (UR) — 7.7% of the meta · ~61% for us (raw 63, n=86)

**Their plan:** the format's premier tempo deck — Dragon's Rage Channeler and Murktide behind Daze,
Force of Will, Lightning Bolt, and Cori-Steel Cutter, now almost always with Flow State. **How to
spot it:** Volcanic Island plus Wasteland (both ~100%) over Izzet fetches (Scalding Tarn, Polluted
Delta), and a turn-one Channeler or Ponder. Nearly every list now runs Flow State (98%) — the tell
that matters for us is *how* they use it: a list leaning on Flow State as a graveyard engine (and
often more Murktide) plays closer to even than a classic burn-and-Daze tempo draw, so track their
graveyard and adjust your race math. **Our plan:** Hydroblast is the swing card — it counters Bolt
and Unholy Heat *and* destroys a resolved Cori-Steel Cutter or a Channeler (both red permanents).
Kill the Channeler before delirium and the Murktide before it delves huge; those are the two threats
that actually run you over. Bowmasters trades up on their one-toughness board and taxes their
cantrips. Against Flow State builds the extra Surgical is well spent — their graveyard fuels both
Flow State upgrades and Murktide. **In:** 2 Hydroblast, 1 Mystical Dispute (add 1 Surgical Extraction
vs Flow State builds). **Out:** 2 Thoughtseize, 1 Kaito (add 1 more Thoughtseize vs Flow State).
Counts: 3 / 3 (4 / 4 vs Flow State).

#### 3. Show and Tell (UR) — 6.9% of the meta · ~59% for us (raw 60, n=102)

**Their plan:** Show and Tell into Emrakul, Omniscience, or Atraxa on turn one or two; a Sneak Attack
package in some builds; Force of Will and Flusterstorm to protect it. **How to spot it:** Ancient Tomb
(100%) alongside Island and blue duals is the giveaway — a fast-mana land in an otherwise blue deck
means the turn-one Show and Tell draw, often off Lotus Petal (94%). Distinguish the two flavors early:
if you see Sneak Attack (a red enchantment), it's Sneak & Show — you can't answer the enchantment, so
race and counter; if it's Omniscience-heavy with no red, it's Omni-Tell and the game becomes a counter
war. **Our plan:** Thoughtseize the enabler, then hold up counters for the Show and Tell or the
Omniscience. Two traps: Grafdigger's Cage does nothing here (their fatties enter from hand), and
nothing in the fifteen answers Sneak Attack itself — removal can't profitably touch what they cheat
in. Keep Snuff Out for the creatures they hard-cast. **In:** 2 Force of Negation, 1 Mystical Dispute
(Dispute costs {2} less targeting their blue Show and Tell or Omniscience). **Out:** 2 Fatal Push, 1
Barrowgoyf. Counts: 3 / 3.

#### 4. Energy (WR) — 5.5% of the meta · ~36% for us (raw 33, n=55)

The punt column. **Their plan:** a fast, wide white aggro engine — Ocelot Pride and Guide of Souls
generating tokens and life, Ajani, Amped Raptor, Goblin Bombardment as a sacrifice outlet, and
Hexing Squelcher, which makes their team uncounterable and gives everything ward. **How to spot it:**
Plains plus Karakas (96%) and white fetches (Marsh Flats, Arid Mesa) into a turn-one Guide of Souls or
Ocelot Pride. Plateau (93%) marks the red splash for Goblin Bombardment and Amped Raptor. **Our plan:**
Hexing Squelcher is why Daze and Force of Will get worse after board — pivot to removal. Toxic Deluge
at two or three clears a Guide/Ocelot board; Sheoldred's Edict answers a warded Squelcher and dodges
their sacrifice-fodder tricks because it makes *them* choose. This is a real uphill fight. **In:** 1
Toxic Deluge, 2 Sheoldred's Edict. **Out:** 2 Daze, 1 Brazen Borrower. Counts: 3 / 3.

#### 5. Grixis Reanimator (UBR) — 5.1% of the meta · ~52% for us (raw 53, n=17)

**Their plan:** Reanimate, Animate Dead, or Shallow Grave onto Griselbrand, Atraxa, or Archon of
Cruelty, enabled by Dark Ritual, Faithless Looting, and Unmask, with Cabal Therapy for protection.
**How to spot it:** Badlands and Raucous Theater (both 100%) next to Underground Sea — the red source
is what marks this as the Grixis flavor, and the turn-one tell is Dark Ritual or Faithless Looting into
a Reanimate/Animate Dead/Shallow Grave. If there's no red and it's grindier, you're likely facing Dimir
Midrange's reanimation splash instead. **Our plan:** this is the matchup Grafdigger's Cage is actually
for — a reanimation spell can't put its target onto the battlefield while the Cage is out. Dauthi
Voidwalker exiles the fatties they loot or discard before they can be reanimated, and Surgical removes
the one that slips through. Thoughtseize the reanimation spell or the payoff. **In:** 1 Dauthi
Voidwalker, 1 Surgical Extraction, 1 Grafdigger's Cage. **Out:** 2 Daze, 1 Kaito. Counts: 3 / 3.

#### 6. Blue Artifacts (U) — 4.6% of the meta · ~43% for us (raw 40, n=47)

**Their plan:** explosive artifact starts off Mox Opal and Lotus Petal, with Emry recurring cheap
artifacts and Pinnacle Emissary as a payoff. **How to spot it:** Urza's Saga (97%) plus Seat of the
Synod (61%) is the signature — an artifact-land package no fair deck plays — with a turn-one Lotus
Petal or Mox Opal. Ancient Tomb (40%) shows up in the faster builds. **Our plan:** Null Rod is the
hoser — it shuts off Mox Opal, Lotus Petal, and any activated artifact engine, collapsing their mana.
Damping Sphere slows the explosive draws, and Consign to Memory counters their colorless artifact
spells. Kill Emry to stop the recursion. An underdog spot. **In:** 1 Null Rod, 1 Damping Sphere, 2
Consign to Memory. **Out:** 2 Daze, 1 Snuff Out, 1 Brazen Borrower. Counts: 4 / 4.

#### 7. Doomsday (UBG) — 4.4% of the meta · ~56% for us (raw 58, n=48)

**Their plan:** assemble the pile and win with Thassa's Oracle off Doomsday, powered by Lion's Eye
Diamond and Dark Ritual, protected by Force of Will and Daze, dug to with cantrips. **How to spot it:**
looks like a blue deck (Underground Sea, Polluted Delta, Island) until Cavern of Souls (99%) gives it
away — that's there to force Thassa's Oracle through countermagic. Turn-one Lion's Eye Diamond or Dark
Ritual and heavy cantripping confirm it. **Our plan:** Thoughtseize on the turn they'd pile; Bowmasters
punishes every cantrip and cycle with a ping plus an Orc. Hold Force of Negation and Dispute for the
Doomsday or the Oracle. Grafdigger's Cage does nothing — Thassa's Oracle is cast from hand. **In:** 2
Force of Negation, 1 Mystical Dispute. **Out:** 2 Fatal Push, 1 Snuff Out. Counts: 3 / 3.

#### 8. Lands (G) — 4.2% of the meta · ~35% for us (raw 30, n=40)

The punt column, and a structural underdog. **Their plan:** Exploration and Life from the Loam grind
lands into a lock — Wasteland loops, utility lands, Sphere of Resistance — while Dark Depths plus
Thespian's Stage makes a 20/20 Marit Lage token. **How to spot it:** the land base *is* the deck —
Dark Depths, Maze of Ith, Boseiju, Karakas, and Urza's Saga (all 100%) — plus turn-one Exploration,
Mox Diamond, or Life from the Loam. **Our plan:** race with Murktide and Kaito while Wasteland fights
their utility lands, and Surgical the Loam to stop the recursion engine. The key insight: Marit Lage
is a black, indestructible token, so Fatal Push and Snuff Out are both dead to it — but Sheoldred's
Edict makes them *sacrifice* it, ignoring both. Null Rod hits Mox Diamond and their Expedition Map.
Expect to lose more than you win, and win on the play with a fast draw. **In:** 1 Null Rod, 2
Sheoldred's Edict, 1 Surgical Extraction. **Out:** 3 Fatal Push, 1 Snuff Out (all dead against a deck
with no killable creatures). Counts: 4 / 4.

#### 9. Dimir Tempo (UB) — 4.1% of the meta · ~50% for us (raw 50, n=172, parent baseline)

The mirror — roughly a coin flip that comes down to configuration and sequencing. This build's
Barrowgoyf beats the Nethergoyf and Mishra's-Bauble configurations in the grind: deathtouch and
lifelink mean it blocks and races everything, and it grows off *both* graveyards. **Their plan:** the
same shell — Thoughtseize, Force of Will, Daze, Bowmasters, Tamiyo, Kaito, Murktide. **How to spot it:**
your own mana base staring back — Underground Sea, Wasteland, Undercity Sewers, Polluted Delta (all
100%) with a turn-one Thoughtseize or Ponder. Which goyf they're on shows late, not early: a turn-one
Mishra's Bauble points to the Bauble-velocity build, while the goyf that lands tells you Barrowgoyf
(deathtouch/lifelink, grows off both yards) versus Nethergoyf (smaller, self-mill). Read it and play
the long game accordingly. **Our plan:** Bowmasters is the single most important card — flash it on
their cantrip for value and a body. Snuff Out only kills their Murktide and Tamiyo (their Barrowgoyf,
Dauthi, and Orc tokens are black), so lean on Fatal Push and the sacrifice plan for Kaito. Mystical
Dispute counters everything that matters, and Sheoldred's Edict answers Kaito the planeswalker and
their creatures alike. Daze gets worse as the game grinds long. **In:** 2 Sheoldred's Edict, 1 Mystical
Dispute, 1 Surgical Extraction (their Flow State / Murktide fuel). **Out:** 3 Daze, 1 Brazen Borrower.
Counts: 4 / 4.

#### 10. Death & Taxes (W) — 3.5% of the meta · ~38% for us (raw 32, n=37)

The punt column. **Their plan:** Aether Vial and a low white curve — Solitude, Recruiter, Skyclave
Apparition, Stoneforge into Batterskull or Meteor Sword, Phelia, and Swords — with Wasteland/Karakas
disruption. **How to spot it:** Karakas (100%) and Wasteland (99%) over Plains, with a turn-one Aether
Vial or Thalia (61%). The black splash (Shadowy Backstreet) marks the current WB build. **Our plan:**
their curve is built to play around Daze, so cut it; Toxic Deluge sweeps the board and Sheoldred's
Edict answers a Vialed-in threat. Keep every Wasteland for the mana-denial war. **In:** 1 Toxic
Deluge, 2 Sheoldred's Edict. **Out:** 3 Daze. Counts: 3 / 3.

#### 11. Dimir Midrange (UB) — 2.9% of the meta · ~52% for us (raw 53, n=15)

**Their plan:** a slower, splashy cousin of the mirror — Thoughtseize, Force of Will, Flow State, and
Tamiyo, most lists adding Reanimate for a fatty. **How to spot it:** the same Dimir shell (Underground
Sea, Undercity Sewers, Polluted Delta) but slower and greedier, and the Reanimate (53%) plus a light
white or green splash is the tell that separates it from the tempo mirror. **Our plan:** out-grind them
with Barrowgoyf and Kaito, Bowmasters on every cantrip, and removal on their threats; watch for the
reanimation package and bring Surgical for it. **In:** 2 Sheoldred's Edict, 1 Surgical Extraction, 1
Mystical Dispute. **Out:** 3 Daze, 1 Snuff Out. Counts: 4 / 4.

#### 12. Azorius Midrange (WU) — 2.7% of the meta · ~57% for us (raw 63, n=19)

A Phelia/Quantum Riddler tempo-midrange deck. **Their plan:** Force of Will, Swords, Tamiyo, Murktide,
and Phelia behind Teferi, Time Raveler and Force of Negation. **How to spot it:** Tundra (100%) and
Meticulous Archive (96%) with Plains and Island, a Wasteland, and a turn-one Swords or Ponder. Phelia
and Flow State (both ~51%) mark the tempo lean over pure control. **Our plan:** Teferi is the problem
card — its static line turns off your counters and flash, so Thoughtseize it and cut Daze after board.
Remove Phelia, Quantum Riddler, and Murktide; Sheoldred's Edict answers Teferi (planeswalker mode) and
their creatures. **In:** 1 Mystical Dispute, 2 Sheoldred's Edict. **Out:** 3 Daze. Counts: 3 / 3.

#### 13. Jeskai Midrange (WU) — 2.6% of the meta · ~63% for us (raw 74, n=19)

**Their plan:** a controlling midrange deck — Swords, Prismatic Ending, Force of Will, Force of
Negation, Tamiyo, Murktide, with Forth Eorlingas!, Wrath of the Skies as a sweeper, and Dress Down.
**How to spot it:** Volcanic Island plus Tundra (both 100%) — the three-color WUR mana base is
distinctive — with Swords or Prismatic Ending early. Forth Eorlingas! (60%) and Wrath of the Skies
(56%) confirm the controlling build. **Our plan:** play around Wrath of the Skies and Dress Down (which
turns off Barrowgoyf, Tamiyo, and Kaito's abilities) by not overcommitting; grind through their answers
with Bowmasters and a resilient threat. Sheoldred's Edict is a clean answer to a Forth Eorlingas! board
or their planeswalkers, and Dispute counters their blue. Daze is weak into a counter-heavy deck. **In:**
1 Mystical Dispute, 2 Sheoldred's Edict. **Out:** 3 Daze. Counts: 3 / 3.

#### 14. Eldrazi (C) — 2.3% of the meta · ~58% for us (raw 60, n=50)

**Their plan:** fast, big colorless creatures under Chalice of the Void — Thought-Knot Seer, Reality
Smasher, Eldrazi Linebreaker, and It That Heralds the End, off Lotus Petal and Kozilek's Command.
**How to spot it:** Eldrazi Temple, Eye of Ugin, and Cavern of Souls (all ~100%) plus Ancient Tomb —
the fast colorless mana base — with a turn-one Chalice of the Void or Lotus Petal into a threat.
**Our plan:** Consign to Memory is a house — *every* Eldrazi threat is a colorless spell (Reality
Smasher, Thought-Knot, and the devoid Linebreaker all counter for one mana, replicate to catch two).
Kill Thought-Knot before it strips your hand and Reality Smasher before it connects; Toxic Deluge
sweeps the board. The one caution: a Chalice on one counters your cantrips *and* Consign — Thoughtseize
or Force the Chalice, and don't over-rely on one-mana answers into it. **In:** 2 Consign to Memory, 1
Toxic Deluge. **Out:** 2 Daze, 1 Snuff Out. Counts: 3 / 3.

#### 15. TES (UBRG) — 2.2% of the meta · ~58% for us (raw 63, n=27)

The Epic Storm — a ritual-storm combo deck. **Their plan:** Dark Ritual, Lion's Eye Diamond, and the
Moxen into Beseech the Mirror or Burning Wish for Tendrils of Agony, with Echo of Eons and Gaea's Will
to refill. **How to spot it:** a sparse land base (Badlands, Bloodstained Mire, Underground Sea) that
leans on rituals — turn-one Lotus Petal, Chrome Mox, Dark Ritual, or Lion's Eye Diamond into a tutor
(Burning Wish, Gamble) is the unmistakable storm open. **Our plan:** Damping Sphere is the premier hoser
— each spell costs {1} more per other spell they've cast that turn, which wrecks a storm chain — and
Null Rod turns off their Mox and LED mana. Thoughtseize the ritual or payoff, and Bowmasters punishes an
Echo of Eons brutally (they each draw seven — that's a ping per card). Force of Negation catches the
noncreature combo pieces for free. **In:** 1 Damping Sphere, 1 Null Rod, 2 Force of Negation. **Out:**
3 Fatal Push, 1 Snuff Out (no creatures to kill). Counts: 4 / 4.

#### 16. White Beanstalk (WUG) — 1.6% of the meta · ~54% for us (raw 55, n=51)

**Their plan:** a white-green value-control deck — Up the Beanstalk and Uro drawing cards, Swords,
Leyline Binding, Force of Will and Force of Negation, Quantum Riddler. **How to spot it:** Tropical
Island and Savannah (98%) alongside Tundra and blue fetches — a three-color Bant mana base — with a
turn-one Ponder or an early Up the Beanstalk (100%), the card the deck is named for. **Our plan:** grind
with the graveyard threats; Bowmasters punishes the card draw from Up the Beanstalk and Uro. Surgical
the escaped Uro to keep it dead, and Sheoldred's Edict answers Uro and Quantum Riddler. **In:** 2
Sheoldred's Edict, 1 Surgical Extraction. **Out:** 2 Daze, 1 Snuff Out. Counts: 3 / 3.

#### 17. Cradle Control (WUBG) — 1.5% of the meta · ~54% for us (raw 56, n=36)

**Their plan:** green ramp-combo — Ignoble Hierarch and Birds into Green Sun's Zenith and Natural
Order, Grist and Collector Ouphe for value, Gaea's Cradle mana, and Craterhoof or Atraxa as the kill.
**How to spot it:** Gaea's Cradle (100%) and Dryad Arbor with Bayou and Forest, plus a turn-one mana
dork (Birds, Ignoble Hierarch) or Green Sun's Zenith. **Our plan:** Bowmasters snipes their mana dorks
on the way in, Toxic Deluge sweeps a dork-heavy board or a Craterhoof alpha strike, and Sheoldred's
Edict answers the fatty they tutor up. Thoughtseize or counter Natural Order — that's the spell that
ends the game. **In:** 1 Toxic Deluge, 2 Sheoldred's Edict. **Out:** 2 Daze, 1 Snuff Out. Counts: 3 / 3.

#### 18. Dredge (UBRG) — 1.4% of the meta · ~50% for us (raw 50, n=14)

**Their plan:** dredge Golgari Grave-Troll and Stinkweed Imp to flood the graveyard, then Dread Return
and Bridge from Below tokens with Narcomoeba and Ox of Agonas for gas. **How to spot it:** Cephalid
Coliseum (95%) and a five-color splash of duals with a turn-one Faithless Looting, Careful Study, or
Golgari Thug — the enablers that get the dredge engine rolling. **Our plan:** graveyard hate wins this
— Grafdigger's Cage stops Narcomoeba entering from the library and shuts off Dread Return, Dauthi
Voidwalker exiles everything they mill or dredge into the yard, and Surgical rips Bridge from Below.
Toxic Deluge sweeps the board they do build. Cut Thoughtseize (they're happy to discard) and cut
counters that have few targets. **In:** 1 Grafdigger's Cage, 1 Dauthi Voidwalker, 1 Surgical Extraction,
1 Toxic Deluge. **Out:** 2 Thoughtseize, 2 Daze. Counts: 4 / 4.

#### 19. Izzet Midrange (UR) — 1.3% of the meta · no reliable data — mechanical read

**Their plan:** a grindier Izzet deck than Delver — Cori-Steel Cutter, Dragon's Rage Channeler, and
Murktide behind Bolt, Daze, Force of Will, and Flow State. **How to spot it:** the same UR base as
Izzet Delver (Volcanic Island, Wasteland, Izzet fetches) but Cori-Steel Cutter (100%) and Flow State
(100%) as centerpieces over a pure Delver curve — it grinds rather than races. **Our plan:** the Izzet
Delver plan applies — Hydroblast counters Bolt and destroys Cori-Steel Cutter or the Channeler, and you
trade into their threats while landing a sticky one. Kill the Channeler and Murktide first. **In:** 2
Hydroblast, 1 Mystical Dispute. **Out:** 2 Thoughtseize, 1 Kaito. Counts: 3 / 3.

#### 20. Aluren (WUBG) — 1.2% of the meta · ~57% for us (raw 67, n=12, small)

**Their plan:** Aluren (free creature spells, mana value three or less, at flash speed) plus Acererak
the Archlich for a token/venture loop, backed by Show and Tell into fatties and Veil of Summer to
protect the combo. **How to spot it:** Tropical Island and Hedge Maze (97%) with Ancient Tomb (97%) —
a Bant-ish base with fast mana — and heavy cantripping (Ponder, Brainstorm) with a Veil of Summer (92%)
held up. **Our plan:** Thoughtseize or counter the Aluren itself (a noncreature enchantment — Force of
Negation catches it for free), and watch for Veil of Summer blanking your black disruption and blue
counters. Removal is weak against the combo, so trim it; race and disrupt. **In:** 2 Force of Negation,
1 Mystical Dispute. **Out:** 2 Fatal Push, 1 Snuff Out. Counts: 3 / 3.

#### 21. Painter (R) — 1.2% of the meta · ~47% for us (raw 46, n=24)

**Their plan:** Painter's Servant plus Grindstone to mill you out, defended by Ensnaring Bridge and
Pyroblast, with Goblin Engineer/Welder to assemble it. **How to spot it:** Ancient Tomb and Urza's Saga
(both 100%) plus Great Furnace and Mountain, with a turn-one Grindstone, Painter's Servant, or Mox Opal.
Pyroblast (89%) in the early spells warns you their anti-blue is maindeck. **Our plan:** Null Rod is the
key card — it turns off Grindstone's activated ability (and their Mox mana), disabling the combo
outright. Consign to Memory counters Painter's Servant, Grindstone, and their colorless artifacts on the
stack. Kill Painter's Servant to break the loop, and respect Pyroblast blowing out your counters. **In:**
1 Null Rod, 2 Consign to Memory. **Out:** 2 Daze, 1 Snuff Out. Counts: 3 / 3.

#### 22. Mystic Forge Combo (C) — 1.2% of the meta · ~57% for us (raw 62, n=21)

**Their plan:** artifact ramp into a Mystic Forge / untap engine — Grim Monolith, Manifold and Voltaic
Key, Mox Opal, The One Ring, Kozilek's Command, Ugin as a payoff. **How to spot it:** Ancient Tomb (100%)
and Urza's Saga (92%) with Urza's Workshop and City of Traitors — pure artifact-ramp lands — and a
turn-one Grim Monolith, Mox Opal, or a key. **Our plan:** Null Rod is devastating — it shuts off Grim
Monolith, both keys, Mox Opal, The One Ring's draw, and Mystic Forge's own ability all at once. Consign
to Memory counters the colorless spells (The One Ring, Grim Monolith, Kozilek's Command, Ugin), and
Damping Sphere throttles their mana. Thoughtseize the engine piece. **In:** 1 Null Rod, 2 Consign to
Memory, 1 Damping Sphere. **Out:** 3 Fatal Push, 1 Snuff Out. Counts: 4 / 4.

#### 23. Golgari Landfall (BG) — 1.1% of the meta · ~42% for us (raw 20, n=5, thin — parent baseline)

Thin data — lean on the mechanical read. **Their plan:** a Golgari graveyard-landfall deck — Wight of
the Reliquary, Elvish Reclaimer, Stitcher's Supplier, Hogaak, and Moonshadow, with Bowmasters,
Thoughtseize, and Fatal Push of their own. **How to spot it:** Bayou and Wasteland with Bojuka Bog,
Dryad Arbor, and Talon Gates of Madara (all 100%), plus a turn-one Stitcher's Supplier, Elvish Reclaimer,
or Thoughtseize. **Our plan:** Grafdigger's Cage stops Hogaak being cast from the graveyard, and
Sheoldred's Edict makes them sacrifice it if it lands (Hogaak is black, so Snuff Out and Push are dead
to it). Toxic Deluge sweeps their creature base; Surgical hits their recursion. **In:** 1 Grafdigger's
Cage, 1 Toxic Deluge, 2 Sheoldred's Edict. **Out:** 2 Daze, 1 Snuff Out, 1 Brazen Borrower. Counts: 4 / 4.

#### 24. Oops! All Spells (UB) — 1.1% of the meta · ~65% for us (raw 70, n=50)

**Their plan:** mill their own library on turn one or two with Balustrade Spy, then Dread Return plus
Thassa's Oracle to win, with Narcomoeba and Cabal Therapy along the way. **How to spot it:** almost no
real lands — Agadeem's Awakening and Boggart Trawler (both 100%) that double as spells — and a turn-one
Lotus Petal, Dark Ritual, or Chrome Mox into a self-mill. If it's fizzling their own library early,
it's Oops. **Our plan:** Grafdigger's Cage stops Narcomoeba entering from the library and shuts off
Dread Return — though Thassa's Oracle is cast from hand, so counter or Thoughtseize the Oracle as the
backup. Dauthi Voidwalker and Surgical gut the graveyard they depend on; Force of Will the Balustrade
Spy. **In:** 1 Grafdigger's Cage, 1 Dauthi Voidwalker, 1 Surgical Extraction. **Out:** 3 Fatal Push (few
targets). Counts: 3 / 3.

#### 25. Smallpox (B) — 1.0% of the meta · ~53% for us (raw 55, n=20)

**Their plan:** a black disruptive attrition deck — Smallpox, Thoughtseize, and Bowmasters stripping
your hand and lands, Life from the Loam grinding back, Hogaak as a threat. **How to spot it:** Swamp
(100%) with Wasteland and Urza's Saga (77%), a turn-one Thoughtseize or Bowmasters, and the namesake
Smallpox (100%) coming down to strip a land and a card. **Our plan:** out-grind them with better threats
and card quality; Grafdigger's Cage stops a graveyard-cast Hogaak and Surgical rips the Loam engine.
Their creatures are mostly black, so removal is picky — save it for what matters. **In:** 1 Grafdigger's
Cage, 1 Surgical Extraction. **Out:** 2 Daze. Counts: 2 / 2.

#### 26. Dimir Delver (UB) — 0.9% of the meta · ~46% for us (raw 38, n=8, thin)

Thin sample. **Their plan:** a lower-to-the-ground Delver cousin of our deck — Bowmasters, Thoughtseize,
Fatal Push, Snuff Out, Daze, Murktide, Tamiyo, and Barrowgoyf on a tempo curve. **How to spot it:** the
same UB base as the mirror (Undercity Sewers, Underground Sea, Wasteland, Polluted Delta) but faster and
lower — expect a turn-one threat and Daze (96%) rather than the mirror's grindy value curve. **Our plan:**
treat it like the mirror against a faster, less grindy opponent — trade efficiently, land Barrowgoyf or
Kaito, and out-card them late. Bowmasters and removal carry it. **In:** 2 Sheoldred's Edict, 1 Mystical
Dispute. **Out:** 2 Daze, 1 Snuff Out. Counts: 3 / 3.

#### 27. Red Stompy (R) — 0.7% of the meta · ~50% for us (raw 50, n=30)

**Their plan:** a red prison-aggro deck — Chrome Mox and Simian Spirit Guide into Chalice of the Void,
Blood Moon or Magus of the Moon, and fast threats (Fable, Broadside Bombardiers, Fury, Pyrogoyf). **How
to spot it:** mono-red with Ancient Tomb and City of Traitors (both ~95%) plus Mountain, and a turn-one
Chrome Mox into Chalice of the Void. **Our plan:** Blood Moon is the scariest card — you run only two
basics (Island, Swamp), so fetch a basic early and hold it. Hydroblast is gold: it *destroys* a resolved
Blood Moon (a red enchantment) and Magus, and counters or kills their red threats. Consign to Memory
counters Chalice and The One Ring (both colorless). **In:** 2 Hydroblast, 2 Consign to Memory. **Out:**
2 Daze (their Chalice and Moon undercut your mana anyway), 1 Brazen Borrower, 1 Snuff Out. Counts: 4 / 4.

#### 28. Cephalid Breakfast (WUB) — 0.7% of the meta · ~50% for us (raw 50, n=18)

**Their plan:** Cephalid Illusionist plus Nomads en-Kor to mill themselves, then Dread Return into
Thassa's Oracle; Force of Will and Daze protect it, Narcomoeba and Cabal Therapy support. **How to spot
it:** an Azorius-looking base (Tundra, Island, Flooded Strand) with a black splash (Undercity Sewers,
Underground Sea) and — the dead giveaway — Cephalid Illusionist plus Nomads en-Kor (both 100%), the
mill combo. **Our plan:** the cleanest answer is killing the combo creature — Fatal Push or Snuff Out
on Cephalid Illusionist (or Nomads en-Kor) in response to the mill fizzles the whole turn (both are
nonblack, so Snuff works). Grafdigger's Cage stops Narcomoeba and Dread Return; Dauthi Voidwalker and
Surgical attack the graveyard they need. **In:** 1 Grafdigger's Cage, 1 Surgical Extraction, 1 Dauthi
Voidwalker. **Out:** 3 Daze. Counts: 3 / 3.

#### 29. Azorius Stoneblade (WU) — 0.7% of the meta · ~49% for us (raw 48, n=25)

**Their plan:** a white-blue tempo-control deck — Stoneforge Mystic into Batterskull, Meteor Sword,
Phelia, Quantum Riddler, and Swords behind Force of Will and Daze. **How to spot it:** Tundra (100%)
with Plains, Island, Wasteland, and Meticulous Archive, a turn-one Stoneforge Mystic or Swords, and
Stifle (80%) is a tell that separates it from Azorius Midrange. **Our plan:** remove Stoneforge, Phelia,
and Quantum Riddler; Batterskull is best answered by Sheoldred's Edict (they sacrifice the germ token)
since Null Rod only stops its return ability, not the attack. Mystical Dispute counters their blue. Cut
Daze into their counter-heavy game. **In:** 1 Mystical Dispute, 2 Sheoldred's Edict. **Out:** 3 Daze.
Counts: 3 / 3.

#### 30. Necro Storm (UB) — 0.5% of the meta · ~52% for us (raw 60, n=5, thin — parent baseline)

Thin data. **Their plan:** Necrodominance as a draw engine feeding a ritual-storm kill — Dark and Cabal
Ritual, the Spirit Guides, Beseech the Mirror, Tendrils, with Pact of Negation to protect it. **How to
spot it:** a barely-there land base (Vault of Whispers, Valakut Awakening, Gemstone Mine) leaning on
turn-one Lotus Petal, Chrome Mox, Dark or Cabal Ritual, and Manamorphose — a storm open pointed at
Necrodominance rather than a Doomsday pile. **Our plan:** Damping Sphere throttles the storm chain and
Null Rod cuts their fast mana; Thoughtseize the Necrodominance or the payoff, and Force of Negation
catches the noncreature pieces for free. Bowmasters punishes the Necrodominance draws hard (those aren't
draw-step draws, so every one triggers it). **In:** 1 Damping Sphere, 1 Null Rod, 2 Force of Negation.
**Out:** 3 Fatal Push, 1 Snuff Out. Counts: 4 / 4.

#### 31. Grixis Midrange (UB) — 0.5% of the meta · ~60% for us (raw 73, n=11, thin)

Thin sample. **Their plan:** a Grixis grind deck splashing red — Thoughtseize, Force of Will, Flow
State, Barrowgoyf, Sheoldred's Edict, Bowmasters, Tamiyo, Kaito, with Kolaghan's Command and Baleful
Strix. **How to spot it:** the Dimir base plus a red source (Volcanic Island, Scalding Tarn) — the
splash is the tell — with a turn-one Thoughtseize or Ponder and Baleful Strix (56%) coming down.
**Our plan:** a bigger mirror — win the long game with Barrowgoyf, Kaito, and Bowmasters, and lean on
Edict for their planeswalkers and creatures. Surgical their Flow State / graveyard fuel and Dispute
their blue. **In:** 2 Sheoldred's Edict, 1 Mystical Dispute, 1 Surgical Extraction. **Out:** 3 Daze, 1
Snuff Out. Counts: 4 / 4.

#### 32. Blue Painter (UR) — 0.4% of the meta · ~52% for us (raw 52, n=44, parent baseline)

**Their plan:** the Painter combo shell with a blue tempo top-end — Grindstone plus Painter's Servant to
mill, Emry and Kappa Cannoneer as threats, Force of Will and Metallic Rebuke to protect it. **How to
spot it:** Seat of the Synod and Sink into Stupor (both 100%) with Ancient Tomb, Island, and Urza's Saga
— a blue artifact base — and a turn-one Mox Opal, Grindstone, or Painter's Servant. The blue counters
separate it from mono-color Painter. **Our plan:** Null Rod turns off Grindstone (and their Mox mana),
breaking the combo, and Consign counters the colorless combo pieces. Kappa Cannoneer has Ward 4, so hard
removal is awkward — Sheoldred's Edict makes them sacrifice it (and answers Emry and Painter's Servant)
around the ward. **In:** 1 Null Rod, 1 Consign to Memory, 2 Sheoldred's Edict. **Out:** 2 Daze, 1 Snuff
Out, 1 Brazen Borrower. Counts: 4 / 4.

---

**A note on the numbers.** The consensus list draws on a moderate sample (about sixty lists this regime),
and the matchup percentages on a longer window; the post-ban metagame is only weeks old, and several of
the fringe archetypes above rest on a dozen games or fewer — those are flagged in-line, as are the few
where we fall back to the broader Dimir Tempo parent baseline rather than a Barrowgoyf-specific cell.
Solid leans, not gospel — adjust as the format settles.

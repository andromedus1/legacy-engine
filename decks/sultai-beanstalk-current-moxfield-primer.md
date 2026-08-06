# Sultai Beanstalk — current build, Moxfield paste

Source: cluster-scoped consensus over the `Sultai Beanstalk` era window since **2025-08-04**
(trigger: unattributed disturbance — possible unregistered B&R change), pool n=87 **[evolving]**.
Corpus through 2026-08-05. Built from the **non-Rakshasa's Bargain camp** (n=45 in-window), which
is where 2 of the 3 current-regime decks sit.

⚠ **Read the honesty block before you sleeve this.** This archetype is very nearly absent from
the current format. Everything below is honest about which parts are evidence and which are the
2025 shell still standing in for a deck nobody is currently playing.

<!-- PASTE BELOW -->

:::notes:::
sultai beanstalk, non-rakshasa's camp. UB(g) up-the-beanstalk value tempo.
era window since 2025-08-04, pool n=87 evolving. corpus thru 2026-08-05.

⚠ THIS IS A FRINGE DECK RIGHT NOW — SAY IT OUT LOUD.
* **3 decks in the entire current ban regime** (since the 2026-06-29 Candelabra ban), out of a
  2,218-deck field = **0.14% share**. two of those three are MTGO league 5-0 dumps, not results.
* the camps' median list dates are **May 2025**. the list below is a 2025-era shell with three
  2026 sightings — it is not a deck the current format has tested.
* the engine's era detector calls its boundary an **unattributed disturbance** ("possible
  unregistered B&R change"), i.e. it does not know why this deck changed. that is a soft window.

what IS measured (the deck has real history, just not recent history):
* 16 of 77 field cells measured, **48.6% coverage**. adjusted field WR **46.3%** — under water.
* agency **27.8%** is an **UPPER BOUND**, not a floor you can trust (ungrounded row).
* **4 of the top-10 current decks have ZERO cells**: Azorius Midrange (6.9%), Energy (6.5%),
  Dimir Midrange (5.8%), Grixis Reanimator (3.8%). that's the whole coverage hole, and it is
  exactly the part of the field that grew while this deck was away.

honest verdict: the measured record says a fair, slightly-underwater blue value deck that beats
Delver and loses to Show and Tell. it has no read at all on a third of the room. play it because
you like the engine, not because the numbers say to.
:::

---

**the engine — and the number everyone gets wrong:**
* **Up the Beanstalk** {1}{G}: "When this enchantment enters and whenever you cast a spell with mana value **5 or greater**, draw a card."
* -> it is **MV 5**, not 4. count your hits before you build.
* this list has **9** of them: 4 Force of Will (MV5), 3 Murktide Regent (MV7), 1 Lórien Revealed (MV5), 1 Murderous Cut (MV5)
* **alternative costs do not change mana value** — this is the whole trick:
  * pitching **Force of Will** still *casts* it -> Beanstalk draws. a free counterspell that replaces itself.
  * **Murderous Cut** delved to {B} is still MV 5 -> draws.
  * **Murktide Regent** is MV 7 no matter how much you delve.
* ⚠ **Lórien Revealed's islandcycling does NOT trigger Beanstalk.** "Islandcycling {1} ({1}, Discard this card: Search your library for an Island card...)" — cycling is an activated ability, not casting. you only draw off Lórien when you hard-cast it for {3}{U}{U} (which then draws 3 + 1 = 4).

**the payoffs:**
* **Murktide Regent** — delve flier; "enters with a +1/+1 counter for each instant and sorcery card exiled with it," and grows whenever an instant/sorcery *leaves* your graveyard
* **Tamiyo, Inquisitive Student** {U} — flying 1-drop; "Whenever Tamiyo attacks, investigate." and "**When you draw your third card in a turn**, exile Tamiyo, then return her transformed." // with Beanstalk + 8 cantrips the third draw is routine — count your draws before you attack
* **Orcish Bowmasters** {1}{B} flash — "When this creature enters and whenever an opponent draws a card except the first one they draw in each of their draw steps, this creature deals 1 damage to any target. Then amass Orcs 1." // taxes every Brainstorm/Ponder/Beanstalk draw in the room

**the interaction suite:**
* 3 Fatal Push, 1 Murderous Cut (delve, instant, unconditional), 2 **Sheoldred's Edict** (modal: nontoken creature / creature token / planeswalker — the answer to hexproof + Marit Lage + a resolved planeswalker), 2 **Witherbloom Command** (choose two: mill-3-and-rebuy-a-land / destroy MV<=2 noncreature nonland / -3/-1 / drain 2)
* 4 Force of Will, 2 Daze, 3 Wasteland — the tempo half

**the mana:** 21 lands + Lórien Revealed as a pseudo-land (islandcycle for {1} when you need the drop). **Mystic Sanctuary** rebuys Force of Will if you control three other Islands — remember Underground Sea, Tropical Island and Hedge Maze all *are* Islands by type.

---
---

**mulligans:**
* you want: 2+ lands, a cantrip, and either Beanstalk or a counterspell
* keep: any hand with Up the Beanstalk + 2 lands. the enchantment is the deck.
* keep: Delver-style hands (Tamiyo + Daze + FoW + cantrip) even without Beanstalk
* ship: no blue source. ship 1-landers without a cantrip. ship all-payoff hands (Murktide/Lórien uncastable early).
* // Beanstalk is a t2 play that does nothing on its own — don't keep a hand whose only action is the enchantment

**interaction targets — what you save it for:**
* **Force of Will** -> a t1-t2 combo kill, or the one resolved permanent you can't beat. NOT their cantrip.
* **Daze** -> the tempo tax while you're deploying. dead on the draw and vs 4+ untapped lands — first cut most places.
* **Sheoldred's Edict** -> hexproof/indestructible things a Push can't touch: Marit Lage, a Kappa with ward, an Emrakul. the sacrifice bypasses targeting entirely.
* **Witherbloom Command** -> mode 2 is the quiet one: "destroy target noncreature, nonland permanent with mana value 2 or less" answers Chalice on 0/1, Bridge from Below-adjacent enchantments, Sneak-support artifacts, Up the Beanstalk in the mirror.
* **Nihil Spellbomb** (main 1-of) -> "{T}, Sacrifice: Exile target player's graveyard," and it cantrips for {B} when it hits the yard. free-roll graveyard hate that isn't a dead card.

**⚠ your Bowmasters are a liability against yourself.** Beanstalk draws, Tamiyo's clue, and 8 cantrips mean *you* are a draw-heavy deck. Opposing Bowmasters punishes this list harder than most; play around it when a Dimir deck holds up {1}{B}.

---
---

**sideboard (15) — what each card is for:**
* **2 Consign to Memory** (100% camp adoption) — "Counter target triggered ability or colorless spell." the format's best answer to cast triggers and colorless spells: Eldrazi, Mystic Forge, Tron, opposing Thassa's Oracle wins.
* **2 Carpet of Flowers** (77%) — "add X mana of any one color, where X is the number of Islands target opponent controls." in a format this blue it is a genuine mana engine, not a hoser. // worth noting: this is the same card the sideboard advisor keeps suggesting for decks where it's ~0% of the field. here it is real, because *this* deck is green and the room is Islands.
* **2 Hydroblast** (68%) — counters a red spell OR destroys a resolved red permanent (Blood Moon, Cori-Steel, a Painter naming red)
* **1 Force of Vigor** (62%) — free, destroys two artifacts/enchantments
* **1 Barrowgoyf** (62%) — deathtouch/lifelink grind threat vs fair decks
* **1 Surgical Extraction** (62%) / **1 Endurance** (28%) — graveyard hate, one surgical one blanket. Endurance also flashes in as a 3/4 reach blocker.
* **1 Null Rod** (60%) — "Activated abilities of artifacts can't be activated." vs Blue Artifacts, Mystic Forge, Tron's rocks
* **1 Force of Negation** (53%) — free on their turn vs noncreature combo
* **1 Thoughtseize** (44%), **1 Veil of Summer** (40%), **1 Toxic Deluge** (28%) — the flex tail

**swap budget:** realistically ~7 — 2 Daze, 2 Thoughtseize, 1 Nihil Spellbomb, 2 Sheoldred's Edict, with 3 Orcish Bowmasters coming out only vs creature-light decks. The Beanstalk engine (4 Beanstalk + the 9 MV5+ hits) never gets cut; cutting hits turns the enchantment off.

---
---

**matchups — measured cells first, then the holes**

*shrunk / raw / n, over the era window. 16 of 77 cells measured, 48.6% coverage.*

**Show and Tell — 5.1% field · 37.6 / 34.8 / n=46 — your worst relevant matchup, big sample**
* they go over the top of a fair deck on turn 1-2 and your removal is blank.
* IN: 1 Force of Negation, 1 Thoughtseize, 1 Veil of Summer, 1 Surgical Extraction  //  OUT: 3 Fatal Push, 1 Sheoldred's Edict
* // Edict is not blank here — it answers a resolved Emrakul/Atraxa — keep one

**Blue Artifacts — 7.1% field · 44.0 / 42.1 / n=19**
* Chalice on 1 blanks your cantrips; Kappa/Emry grind past your removal.
* IN: 1 Null Rod, 1 Force of Vigor, 2 Consign to Memory  //  OUT: 2 Daze, 1 Nihil Spellbomb, 1 Sheoldred's Edict
* // Witherbloom Command mode 2 kills Chalice on 0-2 — remember it before you board

**Dimir Tempo — 8.7% field (biggest deck) · 46.1 / 46.0 / n=37**
* mirror-adjacent fair blue. their Bowmasters punish your draw engine harder than yours punish theirs.
* IN: 1 Barrowgoyf, 1 Thoughtseize  //  OUT: 1 Nihil Spellbomb, 1 Sheoldred's Edict
* // near-even and well sampled — this one is a real coin flip, play tight rather than boarding hard

**Doomsday — 7.3% field · 46.7 / 47.1 / n=17**
* library combo, so graveyard hate does nothing. discard + permission is the whole plan.
* IN: 1 Force of Negation, 1 Thoughtseize, 1 Veil of Summer  //  OUT: 3 Fatal Push
* // Consign counters the Thassa's Oracle win trigger AND the Fantasticar token trigger — both are triggered abilities

**Death & Taxes — 3.3% field · 45.3 / 44.4 / n=18** — Thalia taxes your MV5 engine badly.
* IN: 1 Toxic Deluge, 1 Barrowgoyf  //  OUT: 2 Daze

**Lands — 3.4% field · 43.8 / 40.0 / n=10** — Wasteland/Port on a 21-land deck, and Marit Lage.
* IN: 1 Force of Vigor, 1 Surgical Extraction  //  OUT: 1 Nihil Spellbomb, 1 Daze
* // Sheoldred's Edict is your clean Marit Lage answer — never board both out

**Izzet Delver — 4.1% field · 56.5 / 60.5 / n=38 — your best big-sample matchup**
* you out-card them; their Pyroblasts are live but your threats outclass theirs.
* IN: 2 Hydroblast, 1 Barrowgoyf  //  OUT: 2 Daze, 1 Nihil Spellbomb

**White Beanstalk — 1.3% field · 59.8 / 80.0 / n=10** — the same engine, worse mana. favored.
* IN: 1 Barrowgoyf, 1 Thoughtseize  //  OUT: 2 Daze

**Eldrazi — 1.0% · 41.8 / 36.4 / n=11** — Chalice/Sphere + cast triggers.
* IN: 2 Consign to Memory, 1 Force of Vigor, 1 Null Rod  //  OUT: 2 Daze, 2 Thoughtseize

**Red Stompy 51.1/53.8/n=26 · Goblins 48.1/50.0/n=14 · Painter 49.8/55.6/n=9 · TES 47.6/50.0/n=8**
· **Post 43.1/30.0/n=10** · **Grixis Delver 43.8/40.0/n=10** — all roughly even, all thin-to-modest.
Hydroblast comes in for every red deck; Consign + Null Rod for Post.

**Blue Painter — 0.4% field · 27.8 / 0.0 / n=10 — this is your "floor," and it's a bad number
attached to a deck nobody plays.** 0-for-10 raw. Board Hydroblast and Consign and hope; it sets
the agency figure but it is 0.4% of the room, so don't let it drive your deck choice.

**⚠ THE HOLES — no cells at all, and they are 23% of the field:**
* **Azorius Midrange (6.9%)**, **Energy (6.5%)**, **Dimir Midrange (5.8%)**, **Grixis Reanimator (3.8%)**
* the deck has literally never been measured against any of them in this window. reason from the
  cards: Energy goes wide under your spot removal (Toxic Deluge is your card); Azorius taxes with
  Thalia + Phelia (as D&T); Dimir Midrange is a Bowmasters-heavy grind you're soft to; Grixis
  Reanimator wants Surgical/Endurance/Nihil Spellbomb.
* -> **do not read the 46.3% adjusted field WR as a real number.** Half the coverage is missing and
  the missing half skews toward decks this shell has structural problems with.

---
---

**the other camp (Rakshasa's Bargain), if you want the grindier build:**
* n=41 in-window. swaps the Tamiyo/Daze/Nihil tempo package for **2 Rakshasa's Bargain, 1-2 Uro,
  2 Endurance main**, plus 2 Murderous Cut and a heavier land count.
* its modal counts sum to **56**, so it needs 4 judgment adds — there is no unanimous list to hand
  you, which is why this primer ships the non-Rakshasa's build instead.
* both camps are `evolving`, both have May-2025 medians. neither is a current deck.

**references:**
* archetype `Sultai Beanstalk`, era window since 2025-08-04 (unattributed disturbance), pool n=87 [evolving]
* camp `non-Rakshasa's Bargain` n=45 in-window; signature Tamiyo / Nihil Spellbomb / Daze
* current-regime presence: **3 decks of 2,218 (0.14%)**; 3 in the last 4 corpus weeks
* ranking row: agency **27.8% ungrounded (upper bound)**, adj field WR 46.3%, **48.6% measured coverage**, floor 27.8% vs Blue Painter
* all oracle text quoted verbatim from the local card DB, corpus through 2026-08-05

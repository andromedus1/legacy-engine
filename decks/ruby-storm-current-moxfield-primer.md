# Ruby Storm — current build, Moxfield paste

Source: the **only** current-regime configuration in the corpus — `ClydeCash`, MTGO, 2026-07-05 and
2026-07-12, the same 60 both weeks. Sideboard from the 07-12 copy. Corpus through 2026-08-05.

⚠ **Read the honesty block first.** "Current Ruby Storm" is two decklists from one pilot. The
archetype's full-history consensus (n=228) differs from this list, and the deck has essentially
left the format.

<!-- PASTE BELOW -->

:::notes:::
ruby storm, mono-red medallion storm. corpus thru 2026-08-05.

⚠ THIS IS ONE PLAYER'S LIST, NOT A FIELD READ.
* **2 decks in the entire current ban regime** (0.1% field share, 1 in the last 4 corpus weeks).
* both are **the same pilot** (ClydeCash), one week apart, running an identical 60. so the
  effective sample for "what current Ruby Storm looks like" is **n=1 player**.
* the engine's era detector gives this deck **no boundary at all** — its window is full history
  (n=228 established), meaning the corpus has never detected a disturbance that reshaped it.
  that sounds reassuring but it mostly means the deck is too thin to detect anything on.
* the full-history consensus differs from this list: it runs **4 Desperate Ritual / 2 Lotus Petal /
  3 Bonus Round / 1 Wish** and **no Storm of Memories**. this list runs 2 / 3 / 2 / 0 plus
  **2 Storm of Memories** and **1 Will of the Jeskai**. that is a real, recent retune — which is
  why the current list is worth shipping over the historical average.

what IS measured: 11 of 77 cells, **37.3% coverage** — a third of the field, so the adjusted
49.6% field WR is leaning hard on imputation. agency 37.4% is an UPPER BOUND.
:::

---

**the engine:**
* **Ruby Medallion** {2}: "Red spells you cast cost {1} less to cast." every red spell, all game.
* **Ral, Monsoon Mage** {1}{R}: "Instant and sorcery spells you cast cost {1} less to cast." — a second, cheaper Medallion on a body. Plus: "Whenever you cast an instant or sorcery spell during your turn, flip a coin. If you lose the flip, Ral deals 1 damage to you. If you win the flip, you may exile Ral. If you do, return him to the battlefield transformed."
* -> with either out, your rituals go from break-even to profitable. With **both**, the deck simply wins.

**the mana:**
* **Seething Song** {2}{R} instant: "Add {R}{R}{R}{R}{R}" — +2 raw, **+3 under a Medallion**
* **Rite of Flame** {R}: "Add {R}{R}, then add {R} for each card named Rite of Flame in each graveyard" — note **each graveyard**, so a mirror or a previous game's copies matter
* **Desperate Ritual** {1}{R} instant: adds {R}{R}{R} (+1, +2 discounted)
* **Ancient Tomb**: "{T}: Add {C}{C}. This land deals 2 damage to you." — the discount cards are colorless-castable, so Tomb powers out a t1 Medallion
* **Manamorphose** {1}{R/G}: "Add two mana in any combination of colors. Draw a card." — free, replaces itself, **+1 storm count**

**the card flow:** 4 Reckless Impulse + 4 Wrenn's Resolve (both "exile the top two cards of your
library. Until the end of your next turn, you may play those cards"), 3 **Jeska's Will** ("Add {R}
for each card in target opponent's hand" *or* "exile the top three and play them this turn" — you
choose one; you do not control a commander, so never both).

**the payoff:**
* **Bonus Round** {1}{R}{R}: "Until end of turn, whenever a player casts an instant or sorcery spell, that player copies it." ⚠ **symmetric** — it says *a player*. Do not cast it into an open opposing hand of instants.
* **Storm of Memories** {2}{R}{R}{R}, storm: each copy exiles a **random** MV≤3 instant/sorcery from your graveyard and casts it free. Random, not chosen — in a deck of rituals and cantrips that is mostly fine, but it is a lottery, not a tutor.
* **Burning Wish** {1}{R}: "You may reveal a sorcery card you own from outside the game and put it into your hand." — your kill and your toolbox both live in the board.

**the kill:** you do not run a maindeck win condition. You **Burning Wish** for it. That is the
whole design: the board is half combo pieces, and the Wish targets are the actual endgame.

---
---

**plan:** ritual into a discount permanent, chain draw-spells, then Burning Wish for the finisher
once storm is lethal. Ancient Tomb + Medallion on turn 1 is the dream; Ral on turn 2 into a Bonus
Round turn is the realistic one.

**mulligans:**
* keep: any hand with Ancient Tomb or Lotus Petal + a discount permanent (Medallion / Ral)
* keep: double-ritual + Wrenn's Resolve/Reckless Impulse
* ship: no fast mana and no discount permanent — the deck is unplayable at retail prices
* ship: all-payoff hands (Bonus Round + Storm of Memories with two Mountains is nothing)
* // 12 Mountain is not a lot of *fast* mana. Ancient Tomb and Lotus Petal are what make turn-1-2 happen.

**interaction targets — you have none maindeck, so:**
* your only "interaction" is speed and, post-board, **Hexing Squelcher**: "This spell can't be countered." / "Spells you control can't be countered." / ward—pay 2 life on it and your other creatures. That is the entire answer to permission.
* against Force of Will decks the plan is to bait, or to resolve Squelcher first, or to go so fast they cannot hold up mana. There is no third option.

---
---

**sideboard (15) — this is a toolbox, not a hate package:**
Wish targets (sorceries, fetched with Burning Wish): **1 Galvanic Relay** (storm; exile top card, play next turn — the grindy "draw a lot" line), **1 Inspired Tinkering**, **1 Elemental Eruption**, **1 Fiery Confluence**, **1 Alchemist's Gambit**, **1 Meltdown**, **1 Rite of Flame**, **1 Jeska's Will**, **1 Storm of Memories**, **1 Bonus Round**, **1 Will of the Jeskai** ("Each player may discard their hand and draw five cards" *or* "each instant and sorcery card in your graveyard gains flashback until end of turn").

Actual sideboard cards: **2 Hexing Squelcher** (anti-permission), **2 Blast Zone**.

⚠ note what is **absent**: no Grapeshot and no Empty the Warrens in this 75. The historical
consensus board carries both. If you want the conventional storm kill, that is the first change
to make — Burning Wish with no Grapeshot means your finisher is Elemental Eruption / Fiery
Confluence damage or a Galvanic Relay grind, which is slower and more fragile.

---
---

**matchups (11 measured cells, 37.3% coverage — two thirds of the field is unmeasured)**

**Cradle Control — 1.1% · 72.2 shrunk / 100.0 raw / n=13 — your best cell.** They cannot interact on the stack fast enough.
**Show and Tell — 5.1% · 57.6 / 63.0 / n=27 — best big sample.** A combo race you usually win; they are not faster and Force of Will is their only brake.
* IN: 2 Hexing Squelcher  //  OUT: 2 Storm of Memories

**Energy — 6.5% · 55.9 / 64.3 / n=14** · **Izzet Delver — 4.1% · 52.5 / 57.1 / n=14** · **Red Stompy — 0.5% · 52.8 / 60.0 / n=10**
* creature decks with little stack interaction. just go off.
* IN vs Delver: 2 Hexing Squelcher  //  OUT: 2 Storm of Memories

**White Beanstalk — 1.3% · 50.9 / 55.6 / n=9** — even.

**⚠ Dimir Tempo — 8.7% field, the format's #1 deck · 38.4 / 22.2 / n=9** — Daze, Force, Bowmasters, and a fast clock. The raw 22% is thin but directionally brutal.
* IN: 2 Hexing Squelcher  //  OUT: 2 Storm of Memories
* // Squelcher is the whole plan. Resolve it, then combo.

**Eldrazi — 1.0% · 37.4 / 25.0 / n=12 — the floor.** Chalice of the Void on 1 turns off Ral, Rite of Flame, Manamorphose, Burning Wish, Reckless Impulse, Wrenn's Resolve. Chalice on 0 eats Lotus Petal.
* IN: 2 Blast Zone  //  OUT: 2 Storm of Memories
* // Blast Zone on 1 is the only real answer you have

**Lands — 3.4% · 38.4 / 22.2 / n=9** — Sphere effects tax every ritual; Chalice out of the board.
**Death & Taxes — 3.3% · 44.4 / 37.5 / n=8** — Thalia doubles every spell's cost, which in a storm deck is fatal.
* IN vs both: 2 Blast Zone, 2 Hexing Squelcher  //  OUT: 2 Storm of Memories, 1 Will of the Jeskai, 1 Bonus Round

**Unmeasured and dangerous:** Blue Artifacts (7.1%), Azorius Midrange (6.9%), Dimir Midrange
(5.8%), Doomsday (7.3%), Grixis Reanimator (3.8%) — all zero cells. Chalice and Thalia decks are
your structural enemy and several of those play both; combo decks race you. That is 31% of the
field with no data at all, skewed toward your bad half.

**references:**
* archetype `Ruby Storm`, window = **full history** (no detected disturbance), pool n=228 [established]
* current-regime presence: **2 decks, one pilot** (ClydeCash 2026-07-05 + 2026-07-12), 0.1% field share
* ranking row: agency **37.4% ungrounded (upper bound)**, adj field WR 49.6%, **37.3% measured coverage**, floor 37.4% vs Eldrazi
* all oracle text quoted verbatim from the local card DB, corpus through 2026-08-05

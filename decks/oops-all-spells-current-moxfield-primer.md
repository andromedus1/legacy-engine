# Oops! All Spells — current build, Moxfield paste

Source: cluster-scoped consensus over the `Oops! All Spells` era window since **2026-05-25**
(trigger: Undercity Informer ban 2026-05-18), pool n=42 **[evolving]**. Corpus through 2026-08-05.

Built from the **Summoner's Pact cluster** (17 of 42 in-window decks), not from the raw whole-pool
consensus. Reason: the pool splits into two mutually exclusive builds, and the whole-pool generator
blends them into a list nobody actually plays (it emitted **1 Thoughtseize** — of 22 decks that run
Thoughtseize, *all 22 run exactly 4*, and zero decks run 1). The Pact cluster is unanimous — 17/17
decks agree on 22 of the 24 maindeck slots — and its modal list sums to exactly 60 + exactly 15
with no reconciliation guesswork.

Every rules claim below is quoted from `cards.oracle_text`.

<!-- PASTE BELOW -->

:::notes:::
oops! all spells, summoner's pact build. zero lands, mill yourself out t1-t2, win w/ oracle.
window since 2026-05-25 (post Undercity Informer ban). pool n=42 evolving. corpus thru 08-05.

⚠ READ THIS FIRST — THE DATA IS NOT THERE.
this deck has **ZERO measured matchups** in the current window. 0 of 77 field cells clear the
engine's n>=8 gate. measured coverage = 0%.
-> the "53.7% agency / adjusted field WR" the ranking page shows is a PURE UPPER BOUND. it is
   100% imputation. there is no floor, because nothing has been measured to set one.
-> biggest opponent samples in-window: Dimir Tempo n=4 (25%), Azorius Midrange n=3 (67%),
   Show and Tell n=3 (100%), Lands n=3 (100%), Blue Artifacts n=2 (50%). that's noise, not data.
-> current field share 0.8%, 13 decks in the last 4 corpus weeks. it is a fringe deck right now.
DO NOT read the ranking page's OAS row as a real 53.7%. treat every number here as a lean.

the ban that matters: **Undercity Informer is banned (2026-05-18)**. it was the redundant
enabler. you are now on 4 Balustrade Spy and nothing else. the deck went from 8 enablers to 4.
that is the whole story of why this is fringe now, and why hands are mulliganed differently.
:::

---

**the deck in one line:** you play zero land cards, so Balustrade Spy mills your entire library,
and everything that hits the yard assembles the kill.

**the enabler:**
* Balustrade Spy {3}{B} — "When this creature enters, target player reveals cards from the top of their library until they reveal a land card, then puts those cards into their graveyard." // **target YOURSELF**
* zero land cards in library -> it never finds one -> whole library to yard
* 4 copies. that's it. Undercity Informer is banned. // this is the deck's single point of failure

**why the "lands" aren't lands:**
* Agadeem's Awakening, Fell the Profane, Boggart Trawler are MDFCs w/ land backs
* a double-faced card in your library has **front-face characteristics only** -> sorcery / instant / creature
* -> they do not stop the mill, and they still cast off rituals // verified: front-face type lines are Sorcery / Instant / Creature

**the kill (main line):**
* Spy mills out -> 3 Narcomoeba: "When this card is put into your graveyard from your library, you may put it onto the battlefield." -> 3 free bodies
* Bridge from Below in yard: "Whenever a nontoken creature is put into your graveyard from the battlefield, if this card is in your graveyard, create a 2/2 black Zombie creature token."
* Cabal Therapy flashback = "Sacrifice a creature" -> sac a Narcomoeba -> Bridge makes a Zombie -> net-neutral bodies, and Therapy strips their answer
* Poxwalkers: "Whenever you cast a spell from anywhere other than your hand, return this card from your graveyard to the battlefield tapped." // every flashback cast rebuys it. free extra body.
* Dread Return flashback = "Sacrifice three creatures" -> return **Thassa's Oracle**
* Oracle: "look at the top X cards of your library, where X is your devotion to blue... **If X is greater than or equal to the number of cards in your library, you win the game.**"
* -> library is 0 cards. devotion is >=2 (Oracle's own {U}{U}). 2 >= 0. **you win on the ETB trigger.**

**the second kill (don't forget this one):**
* Lively Dirge {1}{B}, Spree: "+{2} — Return up to two creature cards with total mana value 4 or less from your graveyard to the battlefield."
* Thassa's Oracle is MV 2 -> **Dirge for {3}{B} returns Oracle directly**
* -> this line needs NO creatures on board, no Dread Return, no Bridge. it dodges "sacrifice" hate
  and it dodges having your Narcomoebas answered. 4 copies. it is not a backup, it's a co-primary.

**Summoner's Pact — why 4, and what it actually does:**
* {0} instant: "Search your library for a green creature card, reveal it, put it into your hand, then shuffle. At the beginning of your next upkeep, pay {2}{G}{G}. If you don't, you lose the game."
* green targets in the 60: **Elvish Spirit Guide** (exile from hand: add {G}), **Wild Cantor**, **Disciple of Freyalise**
* -> it is a FREE tutor for a ritual. it converts to mana at zero cost.
* the upkeep clause never resolves because you win this turn. // if you don't win this turn you were losing anyway
* ⚠ it shuffles your library. cast it BEFORE the Spy, never after.

**the mana:** 4 Dark Ritual, 4 Cabal Ritual, 4 Lotus Petal, 4 Simian Spirit Guide, 4 Elvish Spirit
Guide, 2 Chrome Mox, 1 Wild Cantor, 1 Jack-o'-Lantern.
* Jack-o'-Lantern: "{1}, Exile this card from your graveyard: Add one mana of any color." // mana AFTER you've milled, which is the only mana that exists post-Spy
* Cabal Ritual threshold is live the moment the Spy resolves // 7+ in yard is automatic

**the protection:** 4 Pact of Negation — {0} "Counter target spell." same never-pay-the-upkeep logic.

---
---

**mulligans:**
* you need: **Spy + 4 black mana**, or a Pact/tutor chain that gets there
* 4 mana from: Ritual + Petal + Petal, Dark Ritual + Simian, Pact->ESG + Ritual, etc.
* keep: any hand that casts Spy on t1 or t2. that's the whole heuristic.
* keep: Spy + 3 mana + Summoner's Pact (Pact->ESG is the 4th)
* ship: **no Spy, no Pact.** 4 outs in 60 and no tutor is not a hand. // post-Informer-ban this
  ships more hands than the old deck did — internalize that, it's the ban tax
* ship: all-mana-no-Spy. ship all-payoff (Oracle/Dread Return/Narcomoeba) with no enabler.
* // Lively Dirge's "+{1} — Search your library for a card, put it into your graveyard" does NOT
  find you a Spy to cast. it puts it in the yard. it is not a tutor for the enabler.

**interaction targets — what you save it for:**
* **Pact of Negation** -> the one spell that stops the kill THIS turn. not their Brainstorm.
  * Force of Will / Daze on your Spy
  * Surgical Extraction / Faerie Macabre on Narcomoeba or Bridge after the mill
  * a removal spell on the Oracle in response to the ETB // note: countering the removal is right,
    the win is on the trigger, not the body
* **Cabal Therapy (from hand, pre-combo)** -> name their interaction, not their threat. FoW, Force
  of Negation, Surgical, Endurance.
* **Memory's Journey** -> "Target player shuffles up to three target cards from their graveyard into their library. Flashback {G}"
  * this is your **anti-Surgical / anti-deckout button**. if they Surgical your Narcomoeba or exile
    Bridge, Journey puts pieces back and you re-mill or Dirge.
  * also: if the combo fizzles you have an EMPTY library. you lose on your next draw. Journey
    (flashback {G} off ESG) is the only thing that stops that. // do not board it out. ever.
* **Fell the Profane** {2}{B}{B} instant, destroy creature or planeswalker -> Endurance, Archon,
  a Thalia that's taxing you out of the kill

---
---

**matchups & sideboard**

⚠ every cell below is n<=4. these are LEANS with no statistical standing. play the deck, don't
trust the numbers. what follows is reasoning from the cards, tagged where data exists.

**the only thing that matters:** does the opponent have graveyard hate, and is it a permanent?
* permanent hate (Leyline of the Void, Rest in Peace, Grafdigger's Cage, Soul-Guide Lantern) -> Force of Vigor / Foundation Breaker / reanimate a Stormbrood
* instant-speed hate (Surgical, Faerie Macabre, Endurance) -> Memory's Journey, or go under it
* stack interaction (FoW, Daze, Flusterstorm) -> Pact of Negation + Therapy

**vs Dimir Tempo** *(8.7% field, lean 25% n=4 — worst measured lean, tiny)*
* their plan: Daze/FoW/Brainstorm + a clock. they hold up interaction on your combo turn.
* their interaction: Force of Will, Daze, Brazen Borrower, sometimes SB Surgical/Endurance
* -> race the Daze window: **t1 kill or wait until you can pay for Daze**. a t2 kill through an
  untapped Island is often worse than a t3 kill with Pact backup.
* IN: 3 Thoughtseize, 1 Foundation Breaker  // OUT: 1 Fell the Profane, 1 Poxwalkers, 1 Bridge from Below, 1 Reanimate

**vs Doomsday** *(7.3% field, n=0)*
* their plan: they're faster than you and they don't care about your graveyard.
* -> this is a pure race with discard as the only lever. Therapy/Thoughtseize their Doomsday.
* IN: 3 Thoughtseize  // OUT: 1 Fell the Profane, 1 Poxwalkers, 1 Reanimate

**vs Blue Artifacts** *(7.1% field, lean 50% n=2)*
* their plan: Chalice of the Void on 0 is a disaster for you — Petal, Pact of Negation, Summoner's Pact, Chrome Mox all die
* -> **Force of Vigor is the card**. keep one green card in hand to pitch.
* IN: 4 Force of Vigor  // OUT: 1 Fell the Profane, 1 Poxwalkers, 1 Reanimate, 1 Bridge from Below

**vs Azorius Midrange / Phelia** *(6.9% field, lean 67% n=3)*
* their plan: Thalia taxes, hexproof-relevant discard, Leyline of the Void out of the board
* -> Thalia makes Spy cost {4}{B}. Fell the Profane her.
* IN: 4 Leyline of Sanctity, 4 Force of Vigor  // OUT: 1 Poxwalkers, 1 Reanimate, 1 Bridge from Below, 1 Jack-o'-Lantern, 3 Narcomoeba, 1 Disciple of Freyalise
* // that OUT list is deliberately deep — vs a deck w/ post-board Leyline you want the Dirge line and the Charbelcher-free redundancy, not more bodies

**vs Energy** *(6.5% field, lean 100% n=2)*
* their plan: fast creatures + Ocelot/Guide. they do not interact with your graveyard game 1.
* -> just combo. g1 is a goldfish race you win.
* IN: 4 Leyline of Sanctity (vs their discard/Thoughtseize splashes)  // OUT: 1 Fell the Profane, 1 Poxwalkers, 1 Reanimate, 1 Bridge from Below

**vs Dimir Midrange** *(5.8% field, lean 100% n=1)*
* their plan: discard + removal + grind. Thoughtseize/Bowmasters, SB Surgical.
* -> Leyline of Sanctity blanks their entire discard suite: "You have hexproof."
* IN: 4 Leyline of Sanctity, 3 Thoughtseize  // OUT: 1 Fell the Profane, 1 Poxwalkers, 1 Reanimate, 1 Bridge from Below, 1 Jack-o'-Lantern, 2 Cabal Therapy

**vs Show and Tell** *(5.1% field, lean 100% n=3)*
* their plan: t1-t2 Show and Tell -> Omniscience/Sneak. also a combo race.
* -> you are usually faster. Pact of Negation their S&T if you can't kill first.
* IN: 3 Thoughtseize  // OUT: 1 Fell the Profane, 1 Poxwalkers, 1 Reanimate

**vs Izzet Delver** *(4.1% field, lean 100% n=1)*
* same shape as Dimir Tempo but more Daze, less discard. same plan.
* IN: 3 Thoughtseize  // OUT: 1 Fell the Profane, 1 Poxwalkers, 1 Reanimate

**vs Grixis Reanimator** *(3.8% field, lean 0% n=1)*
* their plan: they also want the graveyard, and they bring Surgical + Faerie Macabre for the mirror-ish matchup
* -> their hate is instant-speed, so Memory's Journey is your out. don't board it away.
* IN: 3 Thoughtseize, 1 Foundation Breaker  // OUT: 1 Fell the Profane, 1 Poxwalkers, 1 Bridge from Below, 1 Reanimate

**vs Lands** *(3.4% field, lean 100% n=3)*
* their plan: slow. Sphere effects tax you; Endurance out of the board.
* -> Sphere of Resistance/Thorn makes every free spell cost {1}. count mana twice.
* IN: 4 Force of Vigor, 1 Foundation Breaker  // OUT: 1 Fell the Profane, 1 Poxwalkers, 1 Reanimate, 1 Bridge from Below, 1 Jack-o'-Lantern

**vs Death & Taxes** *(3.3% field, n=0)*
* their plan: Thalia + Cage/Leyline. the worst fair matchup for you.
* -> Grafdigger's Cage stops Dread Return AND Lively Dirge reanimation. you need Force of Vigor.
* IN: 4 Force of Vigor, 1 Foundation Breaker, 1 Disruptive Stormbrood  // OUT: 1 Poxwalkers, 1 Reanimate, 1 Bridge from Below, 3 Narcomoeba, 1 Disciple of Freyalise

**vs Mystic Forge Combo** *(2.3% field, lean 0% n=1)* — Chalice on 0 again. as Blue Artifacts.
**vs Tron** *(2.2% field, n=0)* — Karn + Cage/Leyline off the board. as Death & Taxes.
**vs TES / ANT** *(2.0% / ~1% field, n=0)* — pure race, Therapy their ritual or their payoff. Pact of Negation is live.
**vs Painter** — Grindstone kills you by milling you... which you want. they still have to Painter first. race.
**vs Cradle Control / White Beanstalk / Jeskai Midrange** — fair, slow, SB hate. Force of Vigor + Leyline plan.
**vs Eldrazi** — Sphere/Chalice + Cage. Force of Vigor. // engine declined a data-backed swap here
**vs Aluren, Sultai/Golgari Reanimator, Smallpox** — graveyard-adjacent, expect Surgical. Memory's Journey stays in.

---
---

**board logic recap:**
* **4 Force of Vigor** — free (exile a green card) "Destroy up to two target artifacts and/or enchantments." the single most important 4 cards vs Chalice / Leyline of the Void / Rest in Peace / Cage. // you have 6 green cards maindeck to pitch: 4 ESG, Wild Cantor, Disciple
* **4 Leyline of Sanctity** — "If this card is in your opening hand, you may begin the game with it on the battlefield. You have hexproof." blanks Thoughtseize/Duress/Bowmasters-targeting entirely.
* **3 Thoughtseize** — vs combo races and vs decks whose only answer is one card
* **2 Disciple of Freyalise** — extra Summoner's Pact targets + a real card vs grind
* **1 Disruptive Stormbrood** {4}{G} — "When this creature enters, destroy up to one target artifact or enchantment." **reanimate it** off Dread Return / Lively Dirge to blow up a Leyline of the Void from under the graveyard hate. this is the trick.
* **1 Foundation Breaker** — evoke {1}{G}, same effect cheaper, and a Pact target

**what this list deliberately does NOT run:**
* **Goblin Charbelcher + Lion's Eye Diamond** (the Belcher plan-B package) — 18/22 of the *Discard*
  cluster runs Charbelcher, but only 0/17 of this Pact cluster does. it's a genuinely different
  deck: Belcher wins without the graveyard, which is the correct hedge vs heavy hate, at the cost
  of 8 slots. if your room is full of Leyline/RIP, build the Discard cluster instead.

**the other build (Discard cluster) — direction, not a clean swap:**
* 22 of 42 in-window decks. defining slots: **4 Thoughtseize**, 4 Fell the Profane, 4 Chrome Mox,
  4 Narcomoeba, 4 Agadeem's, 2 Poxwalkers, no Summoner's Pact, no Wild Cantor, no Disciple main.
  board goes to **4 Goblin Charbelcher + 4 Lion's Eye Diamond** (the non-graveyard plan B).
* ⚠ honest caveat: that cluster's modal counts sum to **64**, not 60 — the 22 decks disagree on
  which 4 to trim. there is no unanimous Discard list to hand you, which is exactly why this
  primer ships the Pact build instead.
* game WR since 05-25: **Discard 56.6% (n=36 matches) vs Pact 55.9% (n=13)** — statistically
  indistinguishable at these samples. the Discard build has ~3x the reps and a real anti-hate
  plan B; the Pact build has a unanimous list. pick on room, not on the numbers — they don't separate.

**references:**
* window: era since 2026-05-25, trigger = Undercity Informer ban 2026-05-18
* pool: 42 in-window decks [evolving]; Pact cluster 17, Discard cluster 22, other 3
* engine ranking row: agency 53.7% **ungrounded / 0% measured coverage** — upper bound only
* all oracle text quoted from the local card DB, corpus through 2026-08-05

# Doomsday — Flow State + 4 Fantasticar ("Flow-car") — Moxfield primer

Paste everything below the marker into the Moxfield deck description.
List = `decks/doomsday-flowstate-fantasticar.txt` (Eureka22422 5-0, 2026-07-01, unmodified).

**Updated 2026-08-05** against corpus through 2026-08-05, field window since the **Candelabra of
Tawnos ban (2026-06-29)**, camp re-staged 2026-08-05.

What changed since the 2026-07-23 version:
- Camp is now **`Doomsday [The Fantasticar]`** (renamed from `Flow State` — same cluster, more
  discriminating signature card), **n=144 [established]** in-window.
- **Your 75 is the camp consensus.** Only diff: consensus runs 1 Bloodstained Mire where you run
  1 Marsh Flats. Both fetch Underground Sea or a basic Swamp; neither fetches your Island —
  functionally identical. Keep what you own. **No changes recommended.**
- Matchup evidence graduated: **16 of the top 20** archetypes now have measured (n>=8) parent
  cells, 6 have measured camp cells. The old "post-Candelabra sample ≈ 0" caveat no longer holds.
- Sideboard guide for the top 20 archetypes added.
- Two corrections to the previous version: The Fantasticar is a **4/4**, not 3-power; and the
  "6.9% meta-blowout / best deck in format" framing is replaced by the measured coverage numbers,
  which now exist and are less flattering.

<!-- PASTE BELOW -->

---
---
:::notes:::
doomsday flow-car. UB doomsday, flow state + 4 fantasticar. camp n=144 **ESTABLISHED**.
corpus thru 2026-08-05, field window since candelabra ban 06-29. your 75 == camp consensus.

the numbers, honestly:
* PARENT Doomsday: agency 35.5% **GROUNDED**, adj field WR 53.5%, **84% measured coverage**.
  floor = 35.5% vs Grixis Midrange — that one cell is the whole parent row.
* THIS CAMP: adj 54.2%, floor 48.8% vs Blue Artifacts, but only **39% measured coverage**
  -> camp agency 48.8% is an **UPPER BOUND**. 6 measured cells of 78.
* camp is **6.5% of the current field, 118 decks in the last 4 corpus weeks** — second-biggest
  deck in the format behind Dimir Tempo (8.7%).
-> read the PARENT row for grounded matchup evidence, the CAMP row for what your exact build does
   where it has data. both are labeled below.

camp measured cells (shrunk / raw / n):
  Grixis Reanimator 62.8 / 75.0 / 8 · Show and Tell 58.7 / 62.5 / 8 · Energy 55.1 / 50.0 / 8
  Dimir Midrange 51.4 / 37.5 / 8 · Dimir Tempo 50.3 / 58.3 / 12 · Blue Artifacts 48.8 / 50.0 / 10

the structural edge that hasn't changed: **you are a LIBRARY combo, not a graveyard combo.**
leyline of the void / RIP / surgical do ~nothing to you. that's the standing edge over cephalid
breakfast and oops!, which fold to exactly those cards.
:::

---

**the two kills (oracle-grounded):**
* **The Fantasticar** — {3} Legendary Artifact — Vehicle, **4/4**, flying
  * "Whenever you cast a noncreature spell, you may have The Fantasticar become an artifact creature until end of turn." // so it's also just a **4/4 flier** you cast t1-t2 and attack with when the combo is walled off
  * "Whenever you cast your fourth noncreature spell each turn, you may sacrifice The Fantasticar. If you do, create four 4/4 colorless Construct artifact creature tokens with flying and haste." // **16 power of haste fliers**
  * a Doomsday turn casts four noncreature spells as a matter of course
* **Doomsday** {B}{B}{B}: "Search your library and graveyard for five cards and exile the rest. Put the chosen cards on top of your library in any order. **You lose half your life, rounded up.**"
* **Thassa's Oracle** {U}{U} (1-of): ETB "If X is greater than or equal to the number of cards in your library, you win the game," X = devotion to blue. post-pile library <=5 -> trivially true.
* **Jace, Wielder of Mysteries** (SB): "If you would draw a card while your library has no cards in it, you win the game instead." the third angle.

⚠ **the Fantasticar is NOT immune to Consign to Memory.** Consign reads "Counter target **triggered
ability** or colorless spell" — the sac-for-tokens is a triggered ability, exactly like the Oracle
ETB. The car's real advantages: it dodges **graveyard hate entirely**, it dodges **spell-based
permission** (FoW / Force of Negation counter spells, not triggers), and it's a proactive 4/4
clock. A second angle, not an unanswerable one.

**Flow State** {1}{U}: "Look at the top three cards of your library. Put one of them into your hand and the rest on the bottom of your library in any order. **If there is an instant card and a sorcery card in your graveyard, instead put two of them into your hand**..."
* delirium-lite — one cantrip + one sorcery turns it on. in a pile it's a **draw-2 for {1}{U}**.
  that's the reason this build exists.

**accelerants:** 4 Dark Ritual, 4 Lotus Petal, 1 Lion's Eye Diamond ("Discard your hand, Sacrifice
this artifact: Add three mana of any one color. **Activate only as an instant.**" — after Doomsday
resolves your hand is fodder anyway, so LED is free mana at no real cost).

---
---

**plan:**
* fast, disruptive combo: cantrip + Flow State into Doomsday, protect the turn with
  FoW/Daze/Thoughtseize, kill with tokens (or Oracle)
* deploy the Fantasticar early when you can — it beats down in the air, makes the eventual combo
  one card cheaper to assemble, and baits removal that would rather have been a counter
* Thoughtseize FIRST vs blue decks — strip the FoW/Consign before you go off. you usually win the
  turn *after* you clear the road, not the turn you draw the kit.
* fair backup: Fantasticar + Murktide/Barrowgoyf (post-board) beats decks that overload on combo hate

**mulligans:**
* keep: Doomsday + black source + accelerant (ritual/petal) + protection or a cantrip to find it
* keep: a Fantasticar-first hand with cantrips + disruption
* the 8 cantrips + 3 Flow State + Consider dig hard — one-piece hands with 2 diggers are keeps
* ship: no black mana; all-payoff-no-mana; a combo hand with zero protection into a known blue deck
* g2: don't keep a hand that ONLY combos into their known disruption — value the fair beatdown
* // LED is a PILE card first, a mana source second. don't count it as t1 mana.

**interaction targets — what you save it for:**
* **Force of Will** -> their disruption on your combo turn, or a t1-t2 kill from faster combo. NOT their Ponder.
* **Daze** -> the tax on their t2-t3 interaction while you set up. weak on the draw and vs 4+ untapped lands -> the first cut in most grindy matchups (out in 15 of the 20 guides below).
* **Thoughtseize** -> pre-combo, name their **counterspell/Consign**, not their threat.
* **Cavern of Souls** -> name **Merfolk** and cast Thassa's Oracle uncounterable: "that spell can't be countered." your out through a permission wall. remember it *before* you tap out.
* **Consign to Memory** (SB) -> "Replicate {1} ... Counter target **triggered ability or colorless spell**." hits opposing Oracle triggers, Eldrazi cast triggers, ETBs, colorless spells. does **not** counter an ordinary colored spell.

**⚠ the pile-lock constraint — read before you sideboard:**
* your real swap budget is **~9 cards**: 3 Thoughtseize, 3 Daze, 2 Mishra's Bauble, 1 Consider.
* everything else is mana or a **pile component**: Thassa's Oracle, Street Wraith (cycling—pay 2
  life), Edge of Autumn (cycling—sacrifice a land), Lion's Eye Diamond, Lotus Petal, Dark Ritual,
  Flow State, Cavern of Souls.
* -> cutting a pile component changes which piles are legal. the board is 15 but the deck only
  absorbs 6-9 swaps without breaking lines. **plan against 9, not 15.** every guide below fits.

**what this deck folds to** // the answer to "what's my leyline of the void": it ISN'T graveyard hate
* **countermagic on the combo turn** — FoW, Daze, Flusterstorm, Force of Negation
* **Consign to Memory** — the one card that answers both kills
* **Chalice of the Void on 1** — blanks the cantrip engine; on 0 it eats Petal/LED/Bauble
* **Collector Ouphe / Null Rod** — turns off Petal, LED, Bauble
* **Endurance** — shuffles the yard, blanks Flow State's two-card mode
* **Thalia / Sphere effects** — the tax that makes a four-spell turn impossible

---
---

**sideboard (15) — what each card is for:**
* **4 Barrowgoyf** — deathtouch, lifelink; power = card types in ALL graveyards, toughness = that +1. the transform plan's threat vs fair blue.
* **2 Murktide Regent** — delve flier, the other half of the transform plan
* **2 Consign to Memory** — triggered abilities + colorless spells
* **2 Force of Negation** — free on their turn; counters **noncreature** spells and **exiles** them
* **2 Dauthi Voidwalker** — shadow (near-unblockable) + "If a card would be put into an opponent's graveyard from anywhere, instead exile it with a void counter on it" -> hoses Reanimator/Delver yards while clocking
* **1 Fatal Push** — MV<=2, or MV<=4 with revolt
* **1 Long Goodbye** — "This spell can't be countered." destroys creature/planeswalker MV<=3
* **1 Jace, Wielder of Mysteries** — the third win condition when Oracle triggers keep getting answered

⚠ **on the transform plan:** boarding into Barrowgoyf/Murktide as a tempo deck is a **live
hypothesis, not a validated edge.** The engine's earlier "transform → Dimir envelope" measurement
was over-credited and doesn't survive scrutiny. Use it where the combo is genuinely contested
(dense permission, or a Chalice that turns the cantrips off), not as a default.

---
---

**sideboard guide — top 20 archetypes by current field share**

*share · parent cell (shrunk/raw/n) · camp cell where measured.* No cell = below the n>=8 gate,
reasoning only.

**1. Dimir Tempo — 8.7% · parent 50.0/53.8/n=13 · camp 50.3/58.3/n=12**
* their plan: Daze/FoW + Nethergoyf/Barrowgoyf clock, Bowmasters, post-board Consign
* -> dead even. they interact on your axis; Cavern naming Merfolk is your best card.
* IN: 2 Force of Negation, 1 Long Goodbye, 1 Fatal Push  //  OUT: 3 Daze, 1 Mishra's Bauble
* // on the draw, cut the 2nd Bauble for a 5th piece of interaction

**2. Blue Artifacts — 7.1% · parent 52.6/61.5/n=13 · camp 48.8/50.0/n=10 — sets your camp floor**
* their plan: Chalice on 1 blanks your cantrips (on 0 it eats Petal/LED/Bauble); Kappa Cannoneer, Emry, Welder loops
* -> the problem is Chalice, not their clock.
* IN: 2 Consign to Memory, 4 Barrowgoyf, 1 Long Goodbye  //  OUT: 3 Daze, 3 Thoughtseize, 1 Consider
* // the clearest transform matchup in the format — under Chalice you're a fair deck whether you like it or not

**3. Azorius Midrange — 6.9% · parent 49.1/33.3/n=9**
* their plan: Phelia, Stoneforge, Thalia taxes, post-board Consign/Containment Priest
* -> Thalia is what kills combo turns. Push/Goodbye her on sight.
* IN: 1 Long Goodbye, 1 Fatal Push, 2 Force of Negation, 4 Barrowgoyf  //  OUT: 3 Daze, 2 Mishra's Bauble, 1 Consider, 1 Thoughtseize
* // raw 33% on n=9 is uglier than the 49% shrunk estimate — don't get comfortable

**4. Energy — 6.5% · parent 55.1/50.0/n=8 · camp 55.1/50.0/n=8**
* their plan: fast wide creatures — Ocelot Pride, Guide of Souls, Amped Raptor. almost no stack interaction.
* -> pure race, you're favored. do NOT dilute; keep the fastest configuration.
* IN: 1 Fatal Push, 1 Long Goodbye  //  OUT: 2 Thoughtseize
* // Thoughtseize costs 2 life vs a deck racing you — a real cut, not a hedge

**5. Dimir Midrange — 5.8% · parent 51.2/40.0/n=10 · camp 51.4/37.5/n=8**
* their plan: Thoughtseize + Bowmasters + removal, then grind. Bowmasters punishes every cantrip.
* -> **both rows show raw well below shrunk (37-40% vs ~51%).** respect the raw.
* IN: 4 Barrowgoyf, 2 Murktide Regent, 1 Long Goodbye  //  OUT: 3 Daze, 2 Mishra's Bauble, 1 Consider, 1 Thoughtseize

**6. Show and Tell — 5.1% · parent 55.9/50.0/n=8 · camp 58.7/62.5/n=8**
* their plan: t1-t2 Show and Tell into Omniscience/Sneak. a combo race you usually win.
* IN: 2 Force of Negation, 2 Consign to Memory  //  OUT: 3 Daze, 1 Mishra's Bauble
* // Consign hits the Sneak Attack activation and Emrakul's cast trigger

**7. Izzet Delver — 4.1% · parent 43.2/42.1/n=114 — huge sample, genuinely bad**
* their plan: Delver/Tamiyo/Cori-Steel + Daze/FoW/Pyroblast. the classic combo predator.
* -> **114 matches at 42-43%.** your worst well-measured top-20 matchup, and it's real.
* IN: 4 Barrowgoyf, 2 Force of Negation, 1 Fatal Push, 1 Long Goodbye  //  OUT: 3 Daze, 2 Mishra's Bauble, 1 Consider, 2 Thoughtseize
* // transform hard: their board is full of Pyroblasts and counters that are dead vs a Barrowgoyf

**8. Grixis Reanimator — 3.8% · parent 60.2/65.2/n=23 · camp 62.8/75.0/n=8 — best camp cell**
* their plan: t1-t2 Entomb/Reanimate into Archon/Atraxa. little stack interaction beyond FoW/Daze.
* IN: 2 Dauthi Voidwalker, 1 Fatal Push, 1 Long Goodbye  //  OUT: 2 Mishra's Bauble, 2 Daze
* // Voidwalker exiles their Entomb target on the way to the yard — hate card AND clock

**9. Lands — 3.4% · parent 55.5/56.6/n=53**
* their plan: Wasteland/Port lock, Mox Diamond, Marit Lage. slow; can't touch the combo g1.
* IN: 1 Fatal Push  //  OUT: 1 Thoughtseize
* // near-zero changes; keep the fast deck. Push is for Sphere-carriers, not a 20/20 Marit Lage.

**10. Death & Taxes — 3.3% · parent 70.3/76.7/n=43 — your best big-sample matchup**
* their plan: Thalia + Port + Vial taxes; no stack interaction.
* IN: 1 Fatal Push, 1 Long Goodbye  //  OUT: 2 Thoughtseize
* // Thalia is the only card that matters; everything else they do is too slow

**11. Mystic Forge Combo — 2.3% · thin (n=5), reasoning only**
* their plan: Chalice/Sphere lock into Forge loops — colorless spells everywhere
* -> **Consign to Memory is exceptional** here ("or **colorless spell**")
* IN: 2 Consign to Memory, 2 Force of Negation, 4 Barrowgoyf  //  OUT: 3 Daze, 3 Thoughtseize, 2 Mishra's Bauble

**12. Tron — 2.25% · thin (n=2), reasoning only**
* their plan: big mana into Karn/Forge; Chalice + Sphere post-board
* IN: 2 Consign to Memory, 2 Force of Negation, 4 Barrowgoyf  //  OUT: 3 Daze, 3 Thoughtseize, 2 Mishra's Bauble
* // open bug `bug-tron-candelabra-cliff-not-detected` — Tron's post-ban read may be stale; trust the cards over the number

**13. TES — 2.0% · parent 58.8/63.6/n=22**
* their plan: faster storm. Defense Grid out of the board is the card that beats you.
* IN: 2 Force of Negation  //  OUT: 2 Mishra's Bauble
* // keep all 3 Thoughtseize — stripping their payoff is how this is won

**14. Aluren — 2.0% · parent 57.8/64.3/n=14**
* their plan: it's a Show and Tell deck (Aluren / Omniscience / Atraxa). same shape as #6.
* IN: 2 Force of Negation, 2 Consign to Memory  //  OUT: 3 Daze, 1 Mishra's Bauble

**15. Izzet Midrange — 1.5% · thin (n=2), reasoning only**
* treat as Izzet Delver, slower and more permission-dense.
* IN: 4 Barrowgoyf, 2 Force of Negation  //  OUT: 3 Daze, 2 Mishra's Bauble, 1 Consider

**16. White Beanstalk — 1.3% · parent 52.5/52.8/n=36**
* their plan: Beanstalk/Stock Up value + Solitude; some permission post-board
* IN: 4 Barrowgoyf, 1 Long Goodbye  //  OUT: 3 Daze, 2 Mishra's Bauble

**17. Cradle Control — 1.1% · parent 36.0/26.9/n=26 — YOUR WORST TOP-20 MATCHUP**
* their plan: Cradle mana into Green Sun / Collector Ouphe / Endurance, plus counterspells on a huge mana base
* -> **26 matches at 26.9% raw.** this is bad and it is measured. Ouphe turns off Petal/LED/Bauble; Endurance shuffles your yard and blanks Flow State's two-card mode.
* IN: 4 Barrowgoyf, 1 Fatal Push, 1 Long Goodbye, 2 Force of Negation  //  OUT: 3 Daze, 3 Thoughtseize, 2 Mishra's Bauble
* // if your room has Cradle Control in it, that's the deck to fear — not Delver

**18. Eldrazi — 1.0% · parent 43.3/41.4/n=70 — bad, well measured**
* their plan: Chalice/Sphere/Ancient Tomb into big colorless threats with cast triggers
* -> Consign answers cast triggers **and** colorless spells; its best matchup in the format.
* IN: 2 Consign to Memory, 4 Barrowgoyf, 1 Fatal Push, 1 Long Goodbye  //  OUT: 3 Daze, 3 Thoughtseize, 2 Mishra's Bauble

**19. Jeskai Midrange — 1.0% · parent 51.4/51.2/n=41**
* their plan: permission + Stoneforge/planeswalkers. fair blue.
* IN: 4 Barrowgoyf, 2 Force of Negation, 1 Long Goodbye  //  OUT: 3 Daze, 2 Mishra's Bauble, 1 Consider, 1 Thoughtseize

**20. Doomsday (the mirror) — 7.3% of field · no cell (mirrors excluded by construction)**
* -> whoever combos first wins; FoW and Thoughtseize decide it.
* IN: 2 Force of Negation, 2 Consign to Memory, 1 Jace  //  OUT: 3 Daze, 2 Mishra's Bauble
* // Consign on their Oracle trigger is a clean 2-for-1 that also just wins on the spot

---
---

**board logic recap:**
* the **9-card swap ceiling** is the real constraint. every guide above sits at or under it — deliberate.
* **Daze is the most-cut card in the deck** — out in 15 of 20. it's a play-first, race-first card,
  and most of the current field goes longer than that.
* **Barrowgoyf is a transform card, not a hate card.** bring it where their interaction is dense
  and their clock is slow (fair blue, Chalice decks). never where you're racing.
* **Consign to Memory** is the format's best answer to cast triggers and colorless spells: Eldrazi,
  Mystic Forge, Tron, and every opposing Oracle trigger.
* **Cavern of Souls naming Merfolk** is a free maindeck answer to permission — the most under-used
  card in the 75.

**references:**
* camp `Doomsday [The Fantasticar]`, **n=144 [established]**, window since 2026-06-29 (Candelabra of Tawnos ban)
* camp: adj 54.2%, floor 48.8% vs Blue Artifacts, **39% measured coverage -> agency is an upper bound**
* parent `Doomsday`: agency 35.5% **grounded**, adj 53.5%, **84% coverage**, floor 35.5% vs Grixis Midrange
* 16 of the top 20 have measured (n>=8) parent cells; 6 have measured camp cells
* all oracle text quoted verbatim from the local card DB, corpus through 2026-08-05

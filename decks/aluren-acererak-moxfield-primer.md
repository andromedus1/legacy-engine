# Aluren [Acererak the Archlich] — Moxfield paste

Source: engine consensus, `Aluren` / camp `Acererak the Archlich`, era window since 2026-05-11, sample n=47 **[evolving]**.
Copy-counts from the same camp pool. Corpus through 2026-07-30.
One judgment fix off raw consensus: **+2 Veil of Summer to the board** (100% adoption, mode 2x — the generator dropped it entirely), −1 Endurance, −1 Defense Grid.

**Heads-up on the name:** this is not the old creature-chain Aluren deck. It's a Show and Tell shell where Aluren is one of three things you cheat into play.

<!-- PASTE BELOW -->

:::notes:::
aluren, acererak build. it's a SHOW AND TELL deck — Aluren / Omniscience / Atraxa are
the things you put in. camp n=47 evolving, corpus thru 07-30.
camp marginal 57.3% (n=185) · post-ban 62.9% (n=35) — genuinely performant.
BUT field-weighted vs the measured top field = 50.7% (66 share-pts covered). the gap
means it beats the long tail harder than it beats the top decks. read both.
camp matters: the parent "Aluren" label also holds a DEAD Baleful Strix generation
(nothing since 2026-01-31) which drags the parent to 43.2% weighted. build the camp.
TAXONOMY: this is really a UG SHOW AND TELL deck, not its own archetype. vs the
`Show and Tell` label it shares 15 core cards and the whole engine (S&T / Omniscience /
Emrakul / Atraxa / Tomb / City / Petal / FoW / Brainstorm / Ponder / Stock Up) —
core Jaccard 0.54. the only real difference is the second cheat package + colors:
Aluren+Acererak in UG here vs Sneak Attack (77%) in UR there. S&T's own camps are
already Sneak / non-Sneak; this is effectively a third camp under a different parent
because the rules-based labeler keys on the card Aluren.
-> so the 73.9% "vs Show and Tell" cell below is an INTRA-FAMILY matchup, not an edge
   against a distinct strategy. discount it accordingly.
all %s below are camp RAW leans w/ n. everything is under n=30 -> speculative.
:::

---

**the three cheat targets (what Show and Tell puts in):**
* Show and Tell — "Each player may put an artifact, creature, enchantment, or land card from their hand onto the battlefield." // SYMMETRIC. they get one too.
* -> **Omniscience** — "You may cast spells from your hand without paying their mana costs." then cast Emrakul for free
* -> **Aluren** — "Any player may cast creature spells with mana value 3 or less without paying their mana costs and as though they had flash." // also SYMMETRIC, see the trap below
* -> **Atraxa** — ETB reveal top ten, take one card of each card type into hand. the fair-ish refuel + a flying deathtouch lifelink body

**the kill — Omniscience line (fastest):**
* S&T -> Omniscience -> cast Emrakul, the Aeons Torn from hand for {0}
* Emrakul: "This spell can't be countered." / "When you cast this spell, take an extra turn after this one." / flying, protection from spells that are one or more colors, annihilator 6
* -> the extra turn triggers ON CAST, so it happens even if they somehow deal w/ the body

**the Acererak engine (Aluren line):**
* Acererak the Archlich is {2}{B} = mana value 3 -> Aluren makes it free, at flash speed
* ETB: "if you haven't completed Tomb of Annihilation, return Acererak to its owner's hand and venture into the dungeon"
* -> bounce + venture, recast free, repeat. four ventures completes the dungeon:
  * Trapped Entry — each player loses 1 life
  * Veils of Fear — each player loses 2 life unless they discard a card
  * Sandfall Cell — each player loses 2 life unless they sacrifice a creature, artifact, or land of their choice
  * Cradle of the Death God — create The Atropal, a legendary 4/4 black God Horror creature token with deathtouch
* // route through Veils of Fear, NOT Oubliette — Oubliette reads "Discard a card and sacrifice a creature, an artifact, and a land," and that's YOU paying, unconditionally
* once the dungeon is complete the ETB condition is false -> **Acererak stops bouncing and stays on board**
* then attacking w/ Acererak: "for each opponent, you create a 2/2 black Zombie creature token unless that player sacrifices a creature of their choice"
* **be honest about what this is:** ~5 symmetric life-drain + a 4/4 deathtouch + a resident 3-drop that taxes their board every attack. it is an ENGINE, not an instant kill. the kill is Emrakul, or beating down w/ Atropal/Atraxa/Zombies.

**⚠ the Aluren symmetry trap — this is the deck's real weakness:**
* Aluren lets *any player* cast MV≤3 creature spells free, at flash speed
* vs a deck that is nothing but cheap creatures, you just untapped their whole hand
* this is almost certainly why the **Energy matchup is 11.1% (n=9)** — every relevant Energy card is MV≤3 (Guide of Souls, Ocelot Pride, Ajani, Amped Raptor, Voice of Victory, Thalia, Sand Scout)
* -> vs creature decks, win with the Omniscience line and treat Aluren as a dead card

**mulligans:**
* you need: a fast mana source (Ancient Tomb / City of Traitors / Lotus Petal) + a cheat spell (Show and Tell) + a payoff, or blue cantrips + Force of Will
* keep: any hand w/ S&T + a target + a land. that's the deck.
* keep: cantrip-heavy hands w/ Force of Will vs unknown opponents
* ship: no-fast-mana, no-cantrip hands. ship all-payoff-no-enabler hands (Omniscience/Emrakul are uncastable at retail).
* // Stock Up (look at top five, put two in hand) is the deck's best raw dig — it finds enabler + payoff

**interaction targets — what you save it for:**
* Force of Will -> their counterspell on your combo turn, or the opposing combo. not their fair 2-drop.
* Veil of Summer -> the counterspell. "Spells you control can't be countered this turn" + hexproof from blue and black + it draws if they've cast a blue or black spell. this is your combo-protection card, cheaper than any alternative.
* Boseiju, Who Endures -> channel {1}{G} discard: destroy target artifact, enchantment, or nonbasic land an opponent controls. their Chalice-shaped permanent, or a manland. // costs {1} less per legendary creature you control
* Consign to Memory (board) -> counters a triggered ability OR a colorless spell. their Emrakul cast trigger, their Karn/Forge colorless spells, their ETB triggers.

---
---

**matchups & sideboard**

// camp cells, since 2026-01-01. ALL n<30 -> direction only.

**Show and Tell (the mirror-ish) — 5.4% field — 73.9% (n=23)**
* best measured matchup and the healthiest sample you have
* their plan: the same cheat, into Omniscience or Sneak Attack
* you're favored because your S&T targets are better and you have Consign for their triggers
* IN: 2 Consign to Memory, 1 Force of Negation, 2 Veil of Summer // OUT: 3 Atraxa, 1 Emrakul, 1 Aluren
* // vs their Sneak Attack, Grafdigger's Cage does nothing — it stops graveyard/library, not hand. don't misboard it here.

**Dimir Tempo — 8.6% field — 62.5% (n=16)**
* the field's #1 deck and you're ahead of it. they're a fair tempo deck; your free-spell density beats their Daze/Stifle math
* IN: 2 Veil of Summer, 1 Force of Negation // OUT: 1 Emrakul, 2 Omniscience
* // Veil blanks their entire interaction suite for a turn — it's blue and black

**Doomsday — 7.5% field — 57.1% (n=7) ?**
* combo race. you're the faster deck on the S&T-Omniscience line
* IN: 2 Consign to Memory, 1 Force of Negation, 2 Veil of Summer // OUT: 3 Atraxa, 1 Aluren, 1 Emrakul
* // Consign counters the Thassa's Oracle win TRIGGER, not just the creature

**Azorius Midrange — 7.4% field — 30.0% (n=10) ?**
* bad. Phelia/Riddler + Stifle/Daze/FoW pressures you while holding counters
* IN: 2 Veil of Summer, 1 Force of Negation, 1 Hydroblast // OUT: 3 Atraxa, 1 Emrakul
* // their creatures are mostly MV≤3 -> Aluren is a liability, board some out

**Blue Artifacts — 6.9% field — 66.7% (n=12) ?**
* IN: 2 Force of Vigor, 1 Pithing Needle // OUT: 3 Atraxa
* // Force of Vigor is free on their turn by exiling a green card — destroys up to two artifacts

**Energy — 6.6% field — 11.1% (n=9) ⚠ WORST CELL**
* 1-for-9. read the symmetry trap above — Aluren hands them their deck for free
* they also have Thalia (noncreature spells cost {1} more) and 4 Deafening Silence ("each player can't cast more than one noncreature spell each turn") — your deck is nearly all noncreature spells
* IN: 2 Force of Vigor, 1 Hydroblast, 2 Veil of Summer // OUT: 4 Aluren, 1 Emrakul
* // yes, board out all four Aluren. the Omniscience line is your only real plan here.

**Dimir Midrange — 6.3% field — 33.3% (n=3) ??**
* IN: 2 Veil of Summer, 1 Force of Negation // OUT: 1 Emrakul, 2 Omniscience

**Izzet Delver — 4.1% field — 85.7% (n=7) ??**
* IN: 1 Hydroblast, 2 Veil of Summer // OUT: 3 Atraxa
* // Hydroblast: counter target spell if it's red, or destroy target permanent if it's red

**Grixis Reanimator — 3.5% field — 50.0% (n=6) ??**
* IN: 2 Grafdigger's Cage, 1 Faerie Macabre // OUT: 2 Omniscience, 1 Emrakul
* // Cage stops creature cards entering from graveyards AND libraries, and stops casting from either. it does not touch your own hand-based plan.
* // Faerie Macabre exiles from graveyards by DISCARDING it — uncounterable, no mana

**Lands — 3.3% field — 37.5% (n=8) ?**
**Tron — 2.0% field — 37.5% (n=8) ?**
* both bad: prison mana + Sphere-shaped taxes on a deck that wants to resolve one big spell
* IN: 2 Force of Vigor, 1 Boseiju is already main, 1 Pithing Needle // OUT: 3 Atraxa
* // Needle names their activated engine; it can't stop mana abilities

**Death & Taxes — 2.8% field — 40.0% (n=5) ??**
* Thalia + Karakas + Wasteland into a deck full of noncreature spells and few lands
* IN: 2 Force of Vigor, 1 Hydroblast // OUT: 3 Atraxa
* // Karakas bounces your Atraxa and your Emrakul — both legendary. plan around it.

---
---

**board logic recap:**
* 3 Carpet of Flowers — 100% adoption, **mode 3x**. vs blue decks it adds X mana per Island they control, every main phase
* 2 Consign to Memory — 100%, mode 2x. counters triggered abilities or colorless spells; replicate {1} for extras
* 2 Veil of Summer — 100% of boards run it, mode 2x. **the raw consensus omitted this entirely — added back**
* 2 Force of Vigor — 70%, mode 2x
* 2 Grafdigger's Cage — 51%, mode split 1x/2x
* 1 Faerie Macabre — 38%, mode 1x
* 1 Force of Negation — 55%, mode 1x
* 1 Hydroblast — 68%, mode 1x
* 1 Pithing Needle — 55%, mode 1x
* **the judgment fix: +2 Veil of Summer, −1 Endurance (32%, lowest adoption, overlaps Cage/Faerie), −1 Defense Grid (43%, overlaps Veil's uncounterable clause at higher cost).**
* other real board cards not in this 15: Flusterstorm (32%), Nature's Claim (28%), Silent Gravestone (26%), Blue Elemental Blast (21%)
* maindeck note: Emrakul is only a **66%** card — a third of the camp cuts it. if you never assemble Omniscience, it's a brick.

**references:**
* engine: `generate consensus --archetype "Aluren" --variant "Acererak the Archlich"`
* copy-counts: Acererak camp pool, since 2026-05-11, n=47
* camp marginal 57.3% (n=185) · post-ban 62.9% (n=35) · camp field-weighted vs measured top field 50.7%
* parent-label marginal 50.8% (n=427) — includes the dead Baleful Strix generation; don't use it to judge this build
* dungeon text (Tomb of Annihilation) and all card text quoted verbatim from the corpus oracle data

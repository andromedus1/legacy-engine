# Golgari Cradle Control — Moxfield paste

Source: engine consensus, `Cradle Control`, era window since 2026-05-11, sample n=73 **[evolving]**.
Copy-counts validated against the whole Cradle family (all color labels), 2026 YTD, n=320.
Corpus through 2026-07-30. One judgment swap off raw consensus (see board logic).

**Read the honesty note first — this deck's recent record does not match the "performing well" impression.**

<!-- PASTE BELOW -->

:::notes:::
golgari cradle control. GSZ/Natural Order toolbox on a Gaea's Cradle mana engine.
HONESTY: family match record is ~50% 2026 YTD (n=594), 44.7% in the current era
window (n=141), 38.5% post-Candelabra (n=26, thin). it is NOT a top performer in
raw match data right now. its high agency score comes from a few small-n lopsided
cells (Lands 85.7% n=7, Blue Artifacts 80% n=5) — those are speculative.
label is also fragmented: "Cradle Control" 800 decks + 4c/Golgari/Abzan variants.
all matchup %s below are RAW leans w/ n. EVERY cell is under n=30 -> all speculative.
:::

---

**the plan:**
* ramp on 1: Ignoble Hierarch / Birds of Paradise
* Badgermole Cub is the engine: "whenever you tap a creature for mana, add an additional {G}" -> every mana dork doubles
* Badgermole also earthbends a land (that land becomes a 0/0 haste creature w/ a +1/+1 counter, still a land) -> an animated land taps as a *creature* for mana, so it triggers Badgermole too
* Gaea's Cradle taps for {G} per creature -> tokens and dorks convert directly into explosive mana
* payoff: Green Sun's Zenith for the right creature at the right X, or Natural Order (sac a green creature) -> Craterhoof Behemoth to end it, or Atraxa to refuel
* Wight of the Reliquary tutors lands (T, sac another creature -> any land tapped) and grows w/ each creature card in your yard
* Springheart Nantuko bestowed -> every landfall can copy the enchanted creature for {1}{G}

**GSZ targets by X (the toolbox):**
* X=0 -> Dryad Arbor // it's a land creature, fetchable, and a Natural Order sac body
* X=1 -> Ignoble Hierarch, Sylvan Safekeeper
* X=2 -> Badgermole Cub, Collector Ouphe, Springheart Nantuko
* X=3 -> Grist, the Hunger Tide // off-battlefield Grist is a 1/1 Insect *creature card*, so GSZ finds it
* X=4 -> Icetill Explorer
* X=8 -> Craterhoof Behemoth // realistically you Natural Order for this instead

**mulligans:**
* keep: t1 dork + a green source + a payoff (GSZ / Wight / Badgermole)
* keep: anything w/ Once Upon a Time — free if it's the first spell you cast this game, and it digs 5 for a creature or land
* ship: no-dork hands. this deck is a mana-engine deck; without acceleration it's a pile of 2-drops.
* ship: Cradle-w/o-creatures hands // Gaea's Cradle taps for nothing on an empty board

**interaction targets — what you save it for:**
* Sylvan Safekeeper -> sac a land, target creature gains shroud. protects Wight/Atraxa from targeted removal. // shroud, so it also stops YOUR own targeting
* Talon Gates of Madara -> ETB phases out up to one target creature. removal-ish tempo, or save your own guy from a wrath/exile
* Bojuka Bog -> ETB exiles a player's whole graveyard. Wight can tutor it up at instant speed vs Reanimator
* Endurance -> flash, and ETB puts a player's graveyard on the bottom of their library. evoke by exiling a green card if you need it free
* Collector Ouphe -> "activated abilities of artifacts can't be activated." // it hits YOUR nothing; you run zero artifacts
* Wasteland -> their Cradle/Tomb/manlands. you have plenty of land tutoring to rebuild

---
---

**⚠ the Gaddock Teeg trap (read before boarding):**
* Teeg: "Noncreature spells with mana value 4 or greater can't be cast. Noncreature spells with {X} in their mana costs can't be cast."
* Green Sun's Zenith is {X}{G} -> **Teeg turns off all 4 of your GSZ.**
* Natural Order is {2}{G}{G} = MV 4 -> **Teeg turns off your Natural Order too.**
* it's a 1-of in 48% of real boards and it is symmetric-hostile to this deck's two best cards.
* only bring it in when their key spells are MV≥4 or carry {X} (Doomsday MV4, TES's Ad Nauseam MV5) AND you're willing to be a creature-only deck that game. // it does NOT stop Show and Tell (MV 3)

---
---

**matchups & sideboard**

// top of the current-regime field by share. ALL cells n<30 -> direction only, not verdicts.

**Dimir Tempo — 8.8% field — 33.3% (n=6) ?**
* their plan: Flow State velocity + Wasteland/Daze/Stifle on your mana engine
* your dorks are Bowmasters/removal magnets and your Cradle is a Wasteland target -> the bad side of a mana-denial fight
* IN: 4 Thoughtseize, 2 Snuff Out // OUT: 1 Craterhoof, 1 Icetill Explorer, 2 Springheart Nantuko, 2 Endurance
* // Snuff Out: pay 4 life if you control a Swamp — Bayou and Underground Mortuary both are Swamps

**Doomsday — 7.6% field — 0.0% (n=1) ??**
* essentially unmeasured. clock + discard is the plan; you have no counterspells
* IN: 4 Thoughtseize, 1 Duress, 1 Mindbreak Trap, 1 Gaddock Teeg // OUT: 1 Collector Ouphe, 2 Endurance, 2 Springheart, 2 Once Upon a Time
* // Teeg is live here (Doomsday is MV 4) but read the trap box first

**Azorius Midrange — 7.5% field — 80.0% (n=5) ??**
**Blue Artifacts — 7.0% field — 80.0% (n=5) ??**
* both lopsided on 5 matches — do not trust these numbers, they're the ones inflating the deck's agency score
* vs Blue Artifacts: Collector Ouphe maindeck is already a haymaker
* IN (Blue Artifacts): 2 Force of Vigor, 2 Abrupt Decay // OUT: 2 Springheart, 1 Icetill, 1 Craterhoof

**Energy — 6.7% field — 50.0% (n=4) ??**
* their Wastelands + Static Prison attack your engine; their Price of Progress punishes your all-nonbasic mana
* Grist is good here (−2: sac a creature, destroy target creature or planeswalker)
* IN: 2 Snuff Out, 2 Abrupt Decay // OUT: 2 Springheart, 1 Icetill, 1 Atraxa

**Show and Tell — 5.5% field — 25.0% (n=12) ?**
* worst real matchup by sample. they cheat a fatty in before your engine matters
* IN: 4 Thoughtseize, 1 Duress, 1 Mindbreak Trap // OUT: 1 Craterhoof, 1 Icetill, 2 Springheart, 2 Endurance
* // Karakas is a 9%-adoption board card in the family for exactly this — consider it if S&T is heavy in your room

**Izzet Delver — 4.2% field — 57.1% (n=7) ??**
* IN: 2 Abrupt Decay, 2 Snuff Out // OUT: 2 Springheart, 1 Icetill, 1 Atraxa
* // Abrupt Decay can't be countered and kills anything MV≤3 — their whole deck

**Grixis Reanimator — 3.5% field — 0.0% (n=6) ?**
* 0-for-6. your Bojuka Bog / Endurance are the outs and they're too slow as drawn
* IN: 4 Thoughtseize, 1 Duress // OUT: 1 Craterhoof, 2 Springheart, 2 Once Upon a Time
* // Endurance stays in from the maindeck; Wight can fetch Bojuka Bog at instant speed

**Lands — 3.3% field — 85.7% (n=7) ??**
* the headline "good" cell, on 7 matches. mechanically plausible: you tutor lands and Wasteland them, Ouphe hits nothing but your Wastes fight their engine
* IN: 2 Force of Vigor // OUT: 2 Springheart

**Death & Taxes — 2.8% field — 50.0% (n=4) ??**
* IN: 2 Snuff Out, 2 Abrupt Decay // OUT: 2 Springheart, 1 Icetill, 1 Atraxa
* // their Karakas bounces your Atraxa; their Wasteland hits your Cradle

**Tron — 2.1% field — 66.7% (n=6) ??**
* IN: 2 Force of Vigor, 2 Disruptor Flute // OUT: 2 Springheart, 1 Icetill, 1 Endurance
* // Disruptor Flute: flash, name a card -> it costs {3} more and its non-mana activated abilities shut off

---
---

**board logic recap:**
* 4 Thoughtseize — 74% adoption, mode 4x. also maindecked in 50% of the family (mode 3x) — a real field call, move 2-3 main if combo is heavy
* 2 Force of Vigor — 94%, mode 2x. free on their turn by exiling a green card
* 2 Abrupt Decay — 75%, mode 2x
* 2 Snuff Out — 68%, mode 2x
* 2 Disruptor Flute — 43%, **mode 2x** // engine consensus emitted 1; corrected to the winners' mode
* 1 Duress — 30%, trimmed to 1 to pay for the Flute
* 1 Gaddock Teeg — 48%, mode 1x. see the trap box — it fights your own GSZ/NO
* 1 Mindbreak Trap — 29%, mode 2x
* **the one judgment swap: +1 Disruptor Flute, −1 Duress.** Flute is flash, hits colorless prison pieces (Tron/Forge) and combo payoffs alike; Duress overlaps Thoughtseize which is already a 4-of.
* other real family board cards not in this 15: Leyline of the Void (41%, mode 3x), Endurance (58% side), Karakas (9%) — swap toward Leyline if your room is Reanimator-heavy

**references:**
* engine: `generate consensus --archetype "Cradle Control"` (era since 2026-05-11, n=73 evolving)
* copy-counts: whole Cradle family (all color labels), 2026 YTD, n=320
* marginals: family post-ban 38.5% (n=26) · era 44.7% (n=141) · 2026 YTD 50.0% (n=594) · bare label 2026 YTD 51.9% (n=474)
* honesty gate: **zero** Cradle cells clear the engine's display threshold vs the current-regime field (largest is n=10). every % here is a raw lean.

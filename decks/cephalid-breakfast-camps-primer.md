# Cephalid Breakfast — Stoneforge vs non-Stoneforge camps (Moxfield primer, the maintainer's list conventions)

Paste everything below the marker into the Moxfield deck description.
Lists = decks/cephalid-breakfast-tempo.txt (non-Stoneforge, current) and
decks/cephalid-breakfast-stoneforge.txt (Stoneforge, Feb–Apr build). 2026-07-23.

<!-- PASTE BELOW -->

---
---
:::notes:::
* one archetype, two engine-discovered camps (stability 0.993, no temporal mixing — a real coexisting build choice, NOT list generations): **non-stoneforge tempo** (n=59 evolving, the live build — decks through 2026-07-01, MINE3016 6th at Legacy Challenge 06-13) vs **stoneforge** (n=36 evolving, feb–apr build — L4rss0n back-to-back league 5-0s, list shipped unmodified)
* both are the SAME combo (cephalid illusionist self-mill -> dread return -> thassa's oracle). the split is the backup plan: tempo runs murktide + more counters; stoneforge runs stoneforge mystic -> kaldra compleat as a fair kill that dodges combo hate
* why the interest: cephalid is the format's #1 agency deck — best measured floor of any current deck (42.8% vs post, n=11) and only 9.4% of the meta blows it out (2nd-lowest, behind doomsday) — it concedes almost no free wins
* DATA HONESTY: this deck was invisible to the engine until today (a date-parse bug crashed discovery on it — now fixed, PR #55). camp n is evolving-tier and there are only ~2 post-candelabra decks, so matchup %s below are FULL-CORPUS parent cells + judgment, not camp-current reads. tune at the table.

---
**the kill (oracle-grounded — this is the whole deck):**
* **cephalid illusionist** ({1}{U}): "whenever this creature becomes the target of a spell or ability, mill three cards"
* free targeting engine, either piece:
  * **shuko** equip {0} = "{0}: attach to target creature you control" — re-equip to the illusionist for {0}, mill 3, repeat infinitely
  * **nomads en-kor** "{0}: the next 1 damage that would be dealt to this creature this turn is dealt to target creature you control instead" — target the illusionist for {0}, same loop
* -> mill your ENTIRE library. during the mill: **narcomoeba** "when this card is put into your graveyard from your library, you may put it onto the battlefield" — 3 of them walk into play free
* **dread return** (milled to yard) flashback = "sacrifice three creatures" -> sac the 3 narcomoebas -> "return target creature card from your graveyard to the battlefield" -> get **thassa's oracle**
* **thassa's oracle** etb: "if X [devotion to blue] ≥ the number of cards in your library, you win the game" — library is empty -> win on the spot
* **cabal therapy** (also milled): flashback "sacrifice a creature" -> strip their fow/swords/counter the turn you go off; narcomoebas feed it too
* the deck can kill as early as t2–3 and does it at instant-ish speed off {0} activations — nothing on the stack for them to respond to except the initial equip/target

**protection & tutors:**
* **orim's chant** ({W}, main): "target player can't cast spells this turn" — a silence on the combo turn; cast it AT them, then go off through zero interaction (kicked {W}{W} it also fogs). the real reason this deck's floor is high
* **step through**: wizardcycling {2} = "search your library for a Wizard card" -> finds the missing combo wizard (illusionist / thassa's oracle / tamiyo are all Wizards); the front half bounces two creatures (reset a bolted illusionist)
* **urza's saga**: chapter III fetches an artifact mv≤1 -> **shuko** (mv1, a combo piece!) or pithing needle — a combo tutor stapled to a land
* **tamiyo, inquisitive student** ({U}): cantrip-flip card engine, blocks fliers, and she's a Wizard (step through target); flips on your 3rd draw into a planeswalker
* **force of will / daze / swords**: the tempo shell protects the combo AND lets you play the fair game when they have hate up

**the camp split — pick by what you fear:**
* **non-stoneforge tempo** (current): +murktide regent, +2nd orim's chant, more counters. faster, more consistent, better vs other combo/tempo where the race is tight. the default and the live build.
* **stoneforge**: +3 stoneforge mystic, +1 kaldra compleat, +1 prismatic ending. stoneforge "search for an Equipment" fetches shuko (combo) OR kaldra (fair kill); "{1}{W},{T}: put an Equipment from hand onto the battlefield" cheats **kaldra compleat** in — living weapon 5/5 germ, indestructible, first strike, trample, haste, exiles what it hits. this is a KILL THAT DODGES GRAVEYARD/COMBO HATE — pick it when the room is full of leyline/surgical/rest-in-peace and you want a plan they can't hate out.

---
**plan:**
* you are a combo deck with a tempo backbone: cantrip to the combo, use fow/daze/chant to clear the one turn you need, kill
* don't jam into open mana — bait or strip their interaction (cabal therapy, chant) first; the combo doesn't get worse by waiting a turn behind counters
* fair plan exists: illusionist + shuko also just mills value; tempo camp beats down with murktide/tamiyo; stoneforge camp grinds with kaldra when the combo is contested
* vs no-interaction decks (fringe aggro, ramp), just combo t2–3 and move on

**mulligans:**
* keep: a combo piece (illusionist OR a tutor for one) + a free-target piece (shuko/nomads/saga) + a cantrip, with a blue source. or: disruption-heavy hand (chant/therapy/fow) + cantrips to find the kit
* the 8 cantrips (4 brainstorm/4 ponder) + saga + step through make it dig well — one-piece hands with two cantrips are keeps
* pitch: all-lands, all-payoff-no-cantrip, or a hand with the combo but zero protection vs a known blue deck
* g2 vs graveyard hate: value the stoneforge/kaldra plan (stoneforge camp) or a beatdown hand; don't keep a hand that ONLY does the combo into their leyline

---
---
**matchups & sideboard** // field shares = post-candelabra (since 06-29, thin n=80); wr = FULL-CORPUS parent cell (big n) — camp-current sample ≈ 0, treat as leans

**izzet delver — ~9% field · this is a race + counter war:**
* their daze/pierce/fow tax your combo turn; bolt kills the illusionist mid-loop (respond by finishing the mill — you only need the target trigger, not the creature to survive)
* chant is your best card; cabal therapy naming force of will clears the road
* in: 2 consign to memory (counters their colorless/triggered stuff), +counters // out: slow value (murktide tempo / kaldra stoneforge)

**mystic forge combo / other combo — ~6% · 49.5% (n=161), roughly even:**
* it's a speed + disruption race; you're often faster. therapy/chant strip their combo turn, or just win first
* in: force of negation, flusterstorm, consign to memory // out: swords, orim's chant stays

**post / cradle control / prison — the worst column · post floor 42.8% (n=11):**
* they don't interact with the combo much but grind you out if you stumble; sphere/thorn effects tax your cantrips and chant
* just combo through — they're too slow to punish a t3 kill; don't durdle into their lock pieces
* in: prismatic ending (their spheres/needles), brazen borrower // out: some counters (they have few targets)

**graveyard hate (leyline / surgical / rest in peace) — the deck's real enemy:**
* leyline of the void turns off the whole mill-to-yard line (narcomoeba never triggers, dread return has no yard)
* THIS is why the stoneforge camp exists: stoneforge -> kaldra compleat kills without the graveyard. side into the fair plan
* in (stoneforge camp): keep stoneforge/kaldra; in (both): prismatic ending / serenity for the enchantment; surgical/soul-guide lantern to fight their hate back // out: some narcomoeba/dread return redundancy

---
:::the two lists:::
* **tempo (current):** the default. paste decks/cephalid-breakfast-tempo.txt
* **stoneforge (anti-hate):** L4rss0n's 5-0. paste decks/cephalid-breakfast-stoneforge.txt
* they overlap ~90%; if you own one you nearly own the other — the diff is 3 stoneforge + kaldra + a prismatic vs murktide + a chant + a daze

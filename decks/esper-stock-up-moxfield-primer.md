# Esper Stock Up (Moxfield primer, Andrew's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/esper-stock-up-60.txt (camp consensus n=53, winner-validated vs harmonywoods 6-2; 2026-07-20).

<!-- PASTE BELOW -->

---
---
:::notes:::
* build = consensus over the STOCK UP camp of esper midrange (n=53 since 2025-08, evolving tier) — the camp is tight (snapcaster 98%, murktide 96%, sanctuary 96% incl) and modal counts assemble a clean 60/15, zero judgment swaps
* the BEST-MEASURED esper midrange version: 55.7% (146-116) since 2025-08, 59.6% (56-38) in 2026 — vs phelia-yorion's higher-but-thinner 63.8% (80 matches, CIs overlap = lean not verdict)
* winner validation: harmonywoods = 8 of the camp's top-14 finishes; their 6-2 challenge list (2026-01-10) matches this 75 within one flex slot
* zero phelia — this camp and the phelia camp NEVER co-occur (0 of 162 esper decks run both); this is the snapcaster/draw-go shell
* data honesty: every matchup cell n<30, ZERO post-candelabra-ban sample — matchup notes are mechanics + priors, NO REPS YET
* fork watch: harmonywoods' own 2026-04 list drifted to 4x flow state / 1 stock up + erode; not folded in (n small), but if the camp follows, this primer ages
* this IS a dimir-tempo-adjacent deck — thoughtseize/push-less/fow/tamiyo/kaito bones; your instincts transfer almost 1:1, the new muscle is snapcaster + stock up sequencing

---
**plan:**
* draw-go card-advantage midrange: trade 1-for-1 with cheap interaction, refuel with stock up/snapcaster, close with murktide/kaito/tamiyo-flip; you win the long game by simply having more cards
* stock up (oracle): "look at the top five... put TWO of them into your hand and the rest on the bottom in any order" — 3 mana, 2 cards, bottom-not-shuffle (know what you sank)
  * CRITICAL: stock up does NOT draw — cards are "put into your hand". tamiyo's flip ("when you draw your third card in a turn") does NOT advance off it, and their bowmasters does NOT trigger. stock up into bowmasters mirrors is FREE; brainstorm is not
* snapcaster: etb gives an instant/sorcery in yard "flashback until end of turn... equal to its mana cost" — flashback stock up ({2}{u}) = the 2-for-1 again; flashback stp/thoughtseize/fow (fow flashback = full {3}{u}{u}, no pitch — plan mana)
* murktide: delve dragon, base 3/3 + a counter per instant/sorcery exiled with it, "whenever an instant or sorcery card LEAVES your graveyard, put a +1/+1 counter" — snapcaster's flashback exile grows a resolved murktide; sequencing: murktide first, snapcaster after = bigger dragon
  * yard budget: snapcaster wants the yard, murktide eats it — delve to a 5/5-6/6 and LEAVE two flashback targets when you can
  * mv is SEVEN regardless of delve (their push/scorn/pe never answer it; their fow does)
* tamiyo: attack = investigate; clue crack + draw step + brainstorm flips her on your turn; flipped side takes over grind games
* kaito: ninjutsu off unblocked tamiyo/snapcaster (returning snapcaster = re-buying the etb later); "during your turn... 3/4 ninja and has hexproof" = their push/stp can only hit him on THEIR turn — he mostly just wins fair mirrors
* mystic sanctuary: 8 other islands in the list (3 tundra, 3 usea, island, sewers — sewers verified Land — Island Swamp); eot sanctuary -> put fow/stp/stock up back on top -> brainstorm/draw it = the endgame loop; snapcaster + sanctuary is soft inevitability
* edict: "each opponent SACRIFICES a nontoken creature of their choice" (or the token mode) — the hexproof/protection answer: true-name, marit lage (TOKEN mode), a lone kaito
* no wasteland, no daze, no push in this camp (0/53 each) — the mana is greedy-stable and the deck plays draw-go honest magic

**mulligans:**
* snap keeps: cantrip-dense hands w/ 2+ lands + interaction; thoughtseize + stp + threat + velocity
* good keeps: stock up + snapcaster skeleton (the engine assembles the rest); tamiyo + protection
* pitch: no-cantrip 4-land hands (the deck mulls like dimir tempo — velocity over power); murktide-clump hands (dead until the yard fills)
* count blue for fow before keeping; count WHITE for nothing — stp is your only white main (plains/tundra/scrubland/strand cover it)

---
---
**interaction targets — what you save it for:**
* thoughtseize (3): their plan card — combo piece g1, the sideboard haymaker g2/3; vs fair decks take the card-advantage engine, not the threat
* fow: their broken start only (s&t, doomsday, reanimate, chalice); this deck can afford to hardcast it late — snapcaster gives it flashback at {3}{u}{u} in emergencies
* stp: real clocks — delver-class, guide, goyfs, thalia; do NOT stp value bodies, you outgrind those
* edict: hexproof/prot/lone-threat boards — true-name, lage (token mode), their murktide if stp is spent
* bowmasters: their brainstorm/ponder/lórien/tamiyo-flip draws; flash it in response to a stock up? NO — stock up doesn't draw, hold it for actual draw spells
* snapcaster: the toolbox — removal when behind, counter when ahead, stock up when even; don't burn him as a 2/1 beater unless lethal-adjacent
* consign (board): chalice CAST + trigger, eldrazi/tron casts, saga chapters, oracle triggers
* clarion conqueror (board): activated-ability lock — emry/forge/grindstone/vial decks
* cage (board): reanimator + library-cheat decks ("creature cards in graveyards and libraries can't enter the battlefield"); your murktide is from HAND (cast, delve is a cost) — cage-proof, but it does turn off THEIR snapcaster? no — snapcaster is cast from hand too; cage costs you NOTHING here
* hydroblast (board): "counter target spell if it's red / destroy target permanent if it's red" — bolts aimed at snapcaster/tamiyo, blood moon ON THE STACK, pyroblast wars
* prismatic ending (board): converge X≤3 (three colors in the manabase) — exiles mv≤3 nonland: chalice, thalia, vial, kaito, goyfs; sorcery speed, plan around it
* force of negation (board, 3): the free counter for their post-board hate + combo — noncreature only, exiles what it counters (reanimate targets stay gone)

---
---
**matchups & sideboard** // post-candelabra field (2026-05-18→07-01 shares; tron 9.3% pre-ban, expect redistribution); ALL cells n<30 = mechanics + priors, tune at the table

**izzet delver — 7.7% of field:**
* their plan: bolt your creatures, daze/pierce your 3-drops, murktide/tamiyo clock
* you're the bigger deck — every 1-for-1 trade favors you; play around daze on stock up turns (their best hit); hydro counters bolt for {u}
* in: +2 hydroblast +2 barrowgoyf
* out: -3 thoughtseize -1 stock up

**show and tell — 6.9%:**
* their plan: s&t/sneak the fatty behind counters
* fow/fon the s&t; edict eats a lone emrakul/atraxa ("sacrifices a nontoken creature of their choice" — works while they have only the fatty); thoughtseize before their window
* in: +3 force of negation +2 consign to memory
* out: -4 swords to plowshares -1 orcish bowmasters

**energy — 5.5%:**
* their plan: guide lifegain + fast wr bodies
* stp/edict early, goyf bricks the ground w/ deathtouch+lifelink, murktide flies over the race; pe answers guide/static-class permanents
* in: +2 barrowgoyf +2 prismatic ending
* out: -3 thoughtseize -1 stock up

**grixis reanimator — 5.1%:**
* their plan: discard into rite/exhume archon
* cage is the lock (your whole deck is cast-from-hand — cage costs you zero); consign the archon's etb trigger as the backup; fow/thoughtseize the enabler; slow threats out, all interaction stays
* in: +2 grafdigger's cage +2 consign to memory
* out: -2 kaito, bane of nightmares -2 murktide regent

**blue artifacts — 4.6%:**
* their plan: saga constructs + emry/forge engines + counter backup
* clarion turns the engine off; pe their emry/chalice (saga itself is a LAND — pe can't touch it, consign the chapters instead); consign also catches colorless casts
* in: +2 clarion conqueror +2 consign to memory
* out: -2 sheoldred's edict -1 kaito, bane of nightmares -1 murktide regent

**doomsday — 4.4%:**
* their plan: pile -> oracle behind thoughtseize/duress
* consign the oracle trigger, fon the pile spells, thoughtseize the doomsday; your clock is slow — prioritize interaction density over speed
* in: +3 force of negation +2 consign to memory
* out: -4 swords to plowshares -1 sheoldred's edict

**lands — 4.2%:**
* their plan: loam grind, port/wasteland tax, marit lage
* edict TOKEN mode eats lage; fon their lage-makers/loam engine; pe exploration/sphere-class; your greedy mana hates port — fetch basics early (island/plains/snow swamp are your outs)
* in: +3 force of negation +2 prismatic ending
* out: -4 orcish bowmasters -1 snapcaster mage

**dimir tempo — 4.1%:**
* their plan: your cousin — thoughtseize/push, goyfs, kaito
* stock up doesn't feed their bowmasters (not a draw) — sequence it freely; their push can't touch murktide (mv7); pe exiles their goyfs (mv≤3 w/ converge); grind wins this, protect snapcaster loops
* in: +2 barrowgoyf +2 prismatic ending
* out: -2 force of will -2 sheoldred's edict

**death & taxes — 3.5%:**
* their plan: thalia tax, vial deploys, mom/skyclave value
* thalia taxes half your deck — kill her on sight (stp/pe); pe also exiles vial/skyclave; edict dodges mom protection entirely; murktide over the top
* in: +2 prismatic ending +2 barrowgoyf
* out: -3 thoughtseize -1 force of will

---
---
**board logic recap (why these 15):**
* 3 fon + 2 consign: the counter axis — combo density in the field (s&t/doomsday/reanimator ≈ 16% combined) wants 5 post-board counters beyond fow
* 2 clarion + 2 cage: engine locks, split activated-abilities (artifacts decks) vs yard-to-play (reanimator); both near-free for you (cast-from-hand deck)
* 2 hydroblast: delver's bolts + blood moon insurance + pyro wars
* 2 prismatic ending: the catch-all vs permanents-matter fair decks (chalice/thalia/vial/goyfs at converge 3)
* 2 barrowgoyf: the fair-mirror brick — deathtouch+lifelink wall that outgrinds races
* board = camp consensus modal; harmonywoods' 6-2 board differed only in 3rd hydro + 1 dress down over the cages — swap if local yard decks are thin
* no thoughtseize 4th, no wasteland, no daze anywhere in the camp — resist porting dimir habits into the board

---
---
**references:**
* list: decks/esper-stock-up-60.txt — engine consensus, esper midrange [stock up] camp n=53 since 2025-08
* validation: harmonywoods 6-2 challenge 32 2026-01-10 within one flex slot; 8 of camp's top-14 finishes are theirs
* why this version: best-measured esper midrange — 55.7% since 2025-08 (262 matches), 59.6% in 2026 (94); phelia-yorion points higher (63.8%) on 80 matches w/ overlapping CIs = lean only
* data honesty: zero established matchup cells; zero post-candelabra sample; fork watch on the flow-state drift (harmonywoods 2026-04)

---
---

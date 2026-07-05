# Doomsday Tempo (Moxfield primer, Andrew's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/doomsday-tempo-boulder.txt (consensus tempo camp n=47 + judgment board, 2026-07-04).
Online swap: -1 brazen borrower -> +1 thoughtseize (3rd).

<!-- PASTE BELOW -->

---
---
:::notes:::
* build = consensus over the TEMPO camp of doomsday (mains murktide/tamiyo, no personal tutor/one ring): n=47 of 134 regime decks, evolving tier; paper subset n=8 — predominantly online-informed
* board = JUDGMENT LAYER over the engine reference (same discipline as the dimir board): copy-study mechanics + winner validation, n=97 field-scoped doomsday winner boards
  * 4 barrowgoyf: plan-package class (0-or-max) — winners' copy mode is 4 at 78% adoption; the old transform MEASUREMENT was unreliable but the transform PACKAGE is winners' standard
  * 2 fon (pitch k_min=2; 97% mode 2) / 2 consign / 2 push (63% mode 2) / 2 dauthi (54% mode 2)
  * dropped engine hedges w/ <20% winner adoption: veil 8%, decay 6%, hydro 14%, nihil 14%, carpet 19%, bitter 20%; duress 29% = closest cut (owned swap for flusterstorm if not buying)
* online-meta board swap: -1 brazen borrower -> +1 thoughtseize (3rd) // only card that differs
* matchup wrs are ARCHETYPE-level (camps pooled) — tempo-camp cells don't exist yet; treat as priors
* acquisition: +1 barrowgoyf (own 3) +1 flusterstorm (own 0) + maindeck (~14 names incl. 1 LED)

---
**plan:**
* two decks in one — pick per game, not per match:
  * fair mode: tamiyo/murktide + daze/fow tempo; POST-BOARD the 4-goyf package makes this a real UB grind deck
  * kill mode: doomsday -> 5-card pile -> thassa's oracle // combo UNDER the fair decks that beat tempo
* mode select: vs resilient-permanent/prison (d&t, lands, eldrazi) = combo asap; vs blue mirrors = fair first, combo when shields down; vs grind = TRANSFORM (goyf package in, they face a midrange deck w/ a combo finish)
* doomsday costs HALF YOUR LIFE — track burn range (izzet) + your own wraith/thoughtseize life spend before committing
* the clean pile (top -> bottom): street wraith / edge of autumn / thassa's oracle / buffer / buffer
  * line: kickoff draw -> wraith (cycle, 2 life) -> edge (cycle, sac a land) -> oracle w/ {U}{U} -> devotion 2 >= library 2, win
  * mana math: {B}{B}{B} doomsday + {U}{U} oracle in one turn = why ritual/petal/LED; LED cracks AFTER doomsday (hand is spent anyway)
  * cavern names merfolk or wizard (oracle = merfolk wizard) -> oracle uncounterable
  * count BEFORE you cast doomsday: kickoff draw + free-draws + {U}{U} confirmed, or you just halved your life to show them your hand
* unearth returns oracle (mv2) from the yard — the recovery line vs counters/mill; grindstone milling you can WIN you the game
* goyf/delve tension: barrowgoyf counts card types in yards, murktide EATS the yard — in transform games, goyf first, murktide off the excess

**mulligans:**
* snap keeps: ritual + doomsday + cantrip/protection; LED hands w/ a path to {U}{U}
* good keeps: tamiyo + daze/fow + 2 lands (fair-mode hand — the combo finds itself off cantrips)
* pitch: no-cantrip no-combo 4-land hands; all-protection-no-plan
* life is a resource w/ a floor: wraith cycles + thoughtseize + doomsday half — don't keep greedy-life hands vs red
* count blue cards for fow before keeping

---
---
**interaction targets — what you save it for:**
* fow/daze: protect the combo turn (their response to doomsday/oracle) OR their gameplan card in fair mode — pick a job per game
* fon (2 post-board): free counter on THEIR turn — their combo, their sweeper in transform games
* flusterstorm: the stack war ON your combo turn (instants/sorceries only; storm copies beat their fluster)
* thoughtseize (+3rd online): turn BEFORE you go off — strip the counter, see the coast
* consign: THEIR oracle trigger (mirror), chalice's counter-trigger, saga chapters, eldrazi casts, emrakul
* long goodbye: can't be countered, mv<=3 — thalia, DRC, bowmasters; NOT thought-knot (mv4), NOT murktide (mv7 — delve cuts cost paid, not mv)
* fatal push: cheap threats — DRC, thalia, guide of souls, bowmasters
* dauthi: yard denial that also clocks — their murktide fuel, their unearth-lines, reanimation; shadow = mostly unblockable

---
---
**matchups & sideboard** // wr = adaptive matrix vs boulder field, ARCHETYPE-level (camps pooled); imputed = no cell data // online board: brazen lines become the 3rd thoughtseize

**izzet delver — 11% of field, 41.5% wr (worst measured — their burn taxes doomsday's half-life):**
* their plan: cheap clock + bolt your face (shrinks combo window) + counter war on the oracle
* mode: fair-lean; combo only behind cavern/thoughtseize or when they tap out
* interaction: push/long goodbye = DRC class; murktide (mv7) needs fow/daze on the stack or brazen bounce; dauthi starves their delve
* in: +2 fatal push +1 long goodbye +1 dauthi
* out: -2 thoughtseize -1 unearth -1 consider

**show and tell — 10%, 57.3% wr:**
* their plan: s&t/sneak the fatty; you're faster + your combo ignores their board
* interaction: fow/fon/daze the s&t itself; consign = emrakul cast + trigger; race first, answer second
* in: +2 consign +2 force of negation
* out: -2 murktide -1 unearth -1 consider

**white beanstalk — 7.5%, 47.9% wr:**
* their plan: beanstalk card adv + binding/swords; slow — combo under it OR transform over it
* TRANSFORM game: 4 goyfs out-grind the value pile; they keep dead oracle-hate
* in: +4 barrowgoyf +2 fatal push
* out: -2 daze -2 murktide -1 unearth -1 consider

**dimir tempo — 7.5%, 46.0% wr (the deck you know from the other side):**
* their plan: YOUR fair shell + bowmasters + consign — bowmasters punishes every cycle draw, consign counters YOUR oracle trigger
* protection now = fon/fluster + cavern (no veil in this board); thoughtseize their consign the turn before
* kill bowmasters BEFORE cycling a pile; dauthi voids their goyf/murktide fuel
* in: +2 dauthi +2 fatal push +1 long goodbye
* out: -2 murktide -1 unearth -1 consider -1 wasteland

**jeskai midrange — 7.5%, ~50 (imputed):**
* their plan: counters + REB + swords/phlage
* interaction: fon their phlage/sweepers; combo end-of-their-turn w/ LED; goyf package if they're removal-light
* in: +2 force of negation +1 flusterstorm
* out: -2 murktide -1 unearth

**azorius midrange — 6.5%, ~50 (imputed):**
* counters + binding; slow clock = combo window OR transform grind
* in: +4 barrowgoyf +2 fatal push
* out: -2 daze -2 murktide -1 unearth -1 consider

**black midrange — 6.5%, ~50 (thin data):**
* discard + bowmasters grind; they strip the pile — so stop being a pile deck
* TRANSFORM: goyfs + push; their discard trades into your threats instead of your combo
* in: +4 barrowgoyf +2 fatal push
* out: -2 daze -2 murktide -1 unearth -1 consider

**black saga storm — 6.5%, ~50 (thin data):**
* their plan: beseech storm — a race you win w/ interaction backup
* interaction: flusterstorm + consign (the storm trigger); daze stays (their curve is tight)
* in: +2 consign +1 flusterstorm
* out: -2 murktide -1 unearth

**death & taxes — 5.6%, 68.8% wr (BEST — the whole reason this deck exists):**
* their plan: vial + thalia tax your pile spells; mother protects; jitte grinds
* interaction: thalia ON SIGHT (push/long goodbye — budget her +1 tax while she's out); combo through revoker w/ spare mana sources
* counters near-dead through vial — cut daze
* in: +2 fatal push +1 long goodbye
* out: -2 daze -1 consider

**doomsday mirror — 5.6%, ~50 (thin):**
* race + stack war; discard war decides it
* interaction: consign THEIR oracle trigger; flusterstorm their protection; dauthi voids their unearth-oracle recovery
* in: +2 consign +1 flusterstorm +1 dauthi
* out: -2 murktide -1 unearth -1 consider

**eldrazi — 5.6%, 43.5% wr:**
* their plan: chalice@1 (kills brainstorm/ponder/petal), TKS strips the pile, fast colorless clock
* interaction: consign the chalice counter-TRIGGER (your 1-drops resolve anyway); brazen bounces chalice/TKS; long goodbye does NOT kill TKS (mv4)
* combo before TKS lands or after decoying it
* in: +2 consign +1 brazen borrower
* out: -2 daze -1 consider
  * // online config: brazen unavailable — +1 thoughtseize instead (strip TKS before it strips you)

**painter — 4.7%, 48.5% wr:**
* their plan: painter names blue -> ALL their REBs counter/kill anything, grindstone mills you
* interaction: push/long goodbye the servant (mv2); grindstone milling you is LIVE FOR YOU — unearth returns a milled oracle, devotion vs empty library = win
* in: +2 fatal push +1 long goodbye
* out: -2 daze -1 consider

**blue artifacts — 3.7%, 43.4% wr:**
* their plan: saga constructs + counter backup + colorless spell base
* interaction: consign their colorless casts + saga chapters; wasteland every saga; dauthi clocks through constructs (shadow)
* in: +2 consign +1 dauthi
* out: -2 murktide -1 unearth

**energy — 3.7%, ~50 (imputed):**
* their plan: fast white-red aggro + lifegain; their clock vs your doomsday half-life is the whole matchup
* interaction: guide of souls on sight (push); combo a turn earlier than comfortable
* in: +2 fatal push +1 long goodbye
* out: -2 thoughtseize -1 wasteland

---
---
**board logic recap (why these 15):**
* the 4-goyf transform package (4 goyf + 2 push + 2 dauthi): the fair-mode PLAN — plan packages are 0-or-max (threshold class, like leyline); winners validate at mode 4 / 78% adoption; turns grind matchups into midrange games where their oracle-hate rots
* protection core (2 fon + 2 consign + 1 fluster): pitch k_min=2 on fon (97% of winners, mode 2); consign covers mirror-oracle/chalice/saga/eldrazi axes; fluster = combo-turn stack war
* 1-of tail (long goodbye, brazen/thoughtseize): removal overflow + flex
* dropped engine hedges (veil/decay/bitter/carpet/hydro/nihil): all <20% winner adoption — breadth the winners don't buy; duress (29%) was the closest cut and is the owned swap for fluster
* NOT here: defense grid — engine recommends, 0.0% of winners, systematic false positive (tracked)
* slot-by-slot + camp split: decks/doomsday-tempo-analysis.md

---
---
**references:**
* build + camp analysis: decks/doomsday-tempo-analysis.md
* cross-meta verdict (dimir for boulder; doomsday = online lean + field-drift option): decks/dimir-vs-doomsday-tempo-comparison.md

---
---

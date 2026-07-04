# Doomsday Tempo (Moxfield primer, the maintainer's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/doomsday-tempo-local.txt (consensus tempo camp n=47, 2026-07-04; board = engine
reference vs the local field). Online swap: -1 brazen borrower -> +1 thoughtseize (3rd).

<!-- PASTE BELOW -->

---
---
:::notes:::
* build = consensus over the TEMPO camp of doomsday (mains murktide/tamiyo, no personal tutor/one ring): n=47 of 134 regime decks, evolving tier; paper subset n=8 — predominantly online-informed
* online-meta board swap: -1 brazen borrower -> +1 thoughtseize (3rd) // only card that differs
* board is the engine reference 15 (1-of hedge spread) — pitch counters at 1 is a KNOWN engine bias (fon/flusterstorm want 2 per the copy study); tune with reps
* matchup wrs below are ARCHETYPE-level (all doomsday camps pooled) — tempo-camp cells don't exist yet; treat as priors
* engine override held: defense grid stays OUT (0.0% of winners, systematic false positive)

---
**plan:**
* two decks in one — pick per game, not per match:
  * fair mode: tamiyo/murktide + daze/fow tempo (dimir tempo's shell minus the black grind)
  * kill mode: doomsday -> 5-card pile -> thassa's oracle // combo UNDER the fair decks that beat tempo
* mode select: vs resilient-permanent/prison (d&t, lands, eldrazi) = combo asap; vs blue mirrors = fair game first, combo when their shields are down
* doomsday costs HALF YOUR LIFE — track burn range (izzet) + your own wraith/thoughtseize life spend before committing
* the clean pile (top -> bottom): street wraith / edge of autumn / thassa's oracle / buffer / buffer
  * line: kickoff draw -> wraith (cycle, 2 life) -> edge (cycle, sac a land) -> oracle w/ {U}{U} -> devotion 2 >= library 2, win
  * mana math: {B}{B}{B} doomsday + {U}{U} oracle in one turn = why ritual/petal/LED; LED cracks AFTER doomsday (hand is spent anyway)
  * cavern names merfolk or wizard (oracle = merfolk wizard) -> oracle uncounterable
  * count BEFORE you cast doomsday: kickoff draw + free-draws + {U}{U} confirmed, or you just halved your life to show them your hand
* unearth returns oracle (mv2) from the yard — the recovery line vs counters/mill; grindstone milling you can WIN you the game

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
* flusterstorm: the stack war ON your combo turn (instants/sorceries only; storm copies beat their fluster)
* duress/thoughtseize: turn BEFORE you go off — strip the counter, see the coast; take sweepers in fair mode
* veil of summer: their blue/black targeted response — hexproof stops discard/push/consign-on-your-trigger; does NOT stop red blasts or binding (white)
* consign: THEIR oracle trigger (mirror), chalice's counter-trigger, saga chapters, eldrazi casts, emrakul
* abrupt decay: can't be countered — chalice, painter, grindstone, binding/beanstalk (all mv<=3)
* long goodbye: can't be countered, mv<=3 — thalia, DRC, bowmasters; NOT thought-knot (mv4), NOT murktide (mv7 — delve cuts the cost paid, not mv)
* fatal push: cheap threats; bitter triumph: the mv4+ overflow (discard/3-life cost — mind the doomsday half)

---
---
**matchups & sideboard** // wr = adaptive matrix vs local field, ARCHETYPE-level (camps pooled); imputed = no cell data // online board: brazen lines become the 3rd thoughtseize

**izzet delver — 11% of field, 41.5% wr (worst measured — their burn taxes doomsday's half-life):**
* their plan: cheap clock + bolt your face (shrinks your combo window) + counter war; REB hits doomsday THROUGH painter? no — REB only if blue; their fluster/daze the oracle
* mode: fair-lean; combo only behind cavern/duress or when they tap out
* interaction: hydroblast their bolts/blasts; push/long goodbye = DRC class; murktide (mv7) needs fow/daze on the stack or brazen bounce; carpet ramps you under their daze
* in: +1 hydroblast +1 fatal push +1 long goodbye +1 carpet of flowers
* out: -2 thoughtseize -1 unearth -1 consider

**show and tell — 10%, 57.3% wr:**
* their plan: s&t/sneak the fatty; you're faster + your combo doesn't care about their board
* interaction: fow/daze the s&t itself; consign = emrakul cast + trigger; race first, answer second
* in: +1 consign +1 force of negation +1 flusterstorm
* out: -2 murktide -1 unearth

**white beanstalk — 7.5%, 47.9% wr:**
* their plan: beanstalk card adv + binding/swords; slow — your combo goes under it
* interaction: decay their beanstalk/binding (uncounterable, both mv<=3); duress the counter if they splash
* in: +1 abrupt decay +1 duress +1 barrowgoyf
* out: -2 daze -1 murktide

**dimir tempo — 7.5%, 46.0% wr (the deck you know from the other side):**
* their plan: YOUR fair shell + bowmasters + consign — bowmasters punishes every wraith/edge cycle draw, consign counters YOUR oracle trigger
* interaction: VEIL IS THE CARD — hexproof from blue/black blanks their consign-on-trigger, thoughtseize, push during the combo turn
* duress first, veil on the turn; kill bowmasters BEFORE cycling through a pile
* in: +1 veil of summer +1 duress +1 fatal push +1 long goodbye
* out: -2 murktide -1 unearth -1 consider

**jeskai midrange — 7.5%, ~50 (imputed):**
* their plan: counters + REB + swords/phlage
* interaction: veil (their counters are blue) + duress; hydroblast the blasts; combo end-of-their-turn w/ LED
* in: +1 veil of summer +1 duress +1 flusterstorm +1 hydroblast
* out: -2 murktide -1 unearth -1 consider

**azorius midrange — 6.5%, ~50 (imputed):**
* counters + binding; slow clock = your best combo window
* in: +1 veil of summer +1 duress +1 abrupt decay
* out: -2 murktide -1 unearth

**black midrange — 6.5%, ~50 (thin data):**
* discard + bowmasters grind; they strip the pile pieces
* interaction: kill bowmasters before cycling; barrowgoyf carries fair mode; veil blanks their discard on the key turn
* in: +1 barrowgoyf +1 fatal push +1 long goodbye +1 veil of summer
* out: -2 daze -1 consider -1 wasteland

**black saga storm — 6.5%, ~50 (thin data):**
* their plan: beseech storm — a pure race you usually win w/ interaction backup
* interaction: flusterstorm + consign (the storm trigger) + duress their protection; daze stays (their curve is tight)
* in: +1 flusterstorm +1 consign +1 duress
* out: -2 murktide -1 unearth

**death & taxes — 5.6%, 68.8% wr (BEST — the whole reason this deck exists):**
* their plan: vial + thalia tax your pile spells; mother protects; jitte grinds
* interaction: thalia ON SIGHT (long goodbye/push — both dodge her tax? no: they're cast, taxed +1 — budget for it); combo through revoker by having spare mana sources
* counters near-dead through vial — cut daze
* in: +1 fatal push +1 long goodbye +1 bitter triumph
* out: -2 daze -1 consider

**doomsday mirror — 5.6%, ~50 (thin):**
* race + stack war; duress war decides it
* interaction: consign THEIR oracle trigger; flusterstorm their protection; veil yours
* in: +1 duress +1 flusterstorm +1 consign +1 veil of summer
* out: -2 murktide -1 unearth -1 consider

**eldrazi — 5.6%, 43.5% wr:**
* their plan: chalice@1 (kills brainstorm/ponder/petal), TKS strips the pile, fast colorless clock
* interaction: consign the chalice counter-TRIGGER (your 1-drops resolve anyway); decay the chalice itself (uncounterable); long goodbye does NOT kill TKS (mv4)
* combo before TKS lands or after decoying it
* in: +1 consign +1 abrupt decay +1 brazen borrower (bounce chalice/TKS)
* out: -2 daze -1 consider
  * // online config: brazen unavailable — +1 thoughtseize instead (strip TKS before it strips you)

**painter — 4.7%, 48.5% wr:**
* their plan: painter names blue -> ALL their REBs counter/kill anything, grindstone mills you
* interaction: decay painter/grindstone (uncounterable, mv<=2); hydroblast their now-blue permanents? no — hydroblast targets RED (painter naming blue doesn't remove red); their deck is red anyway ✓
* grindstone milling you is LIVE FOR YOU: unearth returns a milled oracle — devotion vs empty library = win
* in: +1 abrupt decay +1 hydroblast +1 fatal push
* out: -2 daze -1 consider

**blue artifacts — 3.7%, 43.4% wr:**
* their plan: saga constructs + counter backup + colorless spell base
* interaction: consign their colorless casts + saga chapters; decay the saga payoff; wasteland every saga
* in: +1 consign +1 abrupt decay +1 duress
* out: -2 murktide -1 unearth

**energy — 3.7%, ~50 (imputed):**
* their plan: fast white-red aggro + lifegain; their clock + your doomsday half-life is the whole matchup
* interaction: kill guide of souls on sight; combo a turn earlier than comfortable
* in: +1 fatal push +1 long goodbye +1 bitter triumph
* out: -2 thoughtseize -1 wasteland

---
---
**board logic recap (why these 15):**
* engine reference board vs the local field (natural budget 5/15 dedicated + hedge), overrides applied; every slot 1-of = known hedge bias, tune w/ reps
* protection suite (veil/duress/flusterstorm/consign/fon): the combo's real currency — most matchups board 2-4 of these
* removal suite (push/long goodbye/bitter triumph/decay): thalia/bowmasters/chalice class — the cards that tax the pile
* grind package (barrowgoyf/dauthi/brazen/nihil): fair-mode depth; dauthi doubles as yard hate + clock
* carpet of flowers: blue-field mana cheat — combo under daze
* acquisition reality: 5 SB cards unowned (decay, bitter triumph, carpet, flusterstorm, veil) + ~14 maindeck names incl. 1 LED — this is the BUILD-LATER deck; verdict says stay dimir for local until the field drifts fair/prison
* slot-by-slot + camp split: decks/doomsday-tempo-analysis.md

---
---
**references:**
* build + camp analysis: decks/doomsday-tempo-analysis.md
* cross-meta verdict (dimir for local; doomsday = online lean + field-drift option): decks/dimir-vs-doomsday-tempo-comparison.md

---
---

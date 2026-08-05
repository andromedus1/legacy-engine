# Esper Phelia, Yorion 80 (Moxfield primer, the maintainer's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/esper-phelia-yorion-80.txt (Carroz 2nd, Legacy Challenge 32 2025-09-21, unmodified; 2026-07-20).

<!-- PASTE BELOW -->

---
---
:::notes:::
* build = the 80-card YORION mode of the esper midrange [phelia] camp (n=62 camp since 2025-08, evolving tier; camp splits ~17 yorion-80 / ~39 sixty-card) — yorion mode went 51-29 (63.8%) vs 53.3% for the 60s; both thin, lean not verdict
* list = carroz's 2nd-place challenge 75... 95, UNMODIFIED — every slot inside camp histograms; shell re-validated by dan atkins' 1st MLCG 2026-03-07 (same 4x vial/phelia/overlord/recruiter/solitude core)
* camp wr 54.3% (n=127 matches) vs 41.9% for phelia-less esper midrange — the phelia package IS the deck's edge signal
* data honesty: ~95% of camp data is pre-2026-05-18 regimes, ZERO post-candelabra-ban (2026-06-29) sample; every matchup cell insufficient (n<30) — matchup notes below are mechanics + priors, NO empirical cells; NO REPS YET
* NOT a daze deck and not a cantrip deck — 4 brainstorm is the only blue velocity; this is a VIAL BLINK deck that wins on etb-trigger accounting; your consign/fow stack instincts transfer, your tempo instincts don't

---
**plan:**
* board-control value engine: vial deploys bodies at instant speed, every body has an etb, phelia + yorion re-buy the etbs, 80-card yorion build = etbs never run dry
* phelia is the engine (oracle): "whenever phelia attacks, exile up to one OTHER target nonland permanent... return at the beginning of the next end step... if it entered under your control, put a +1/+1 counter on phelia"
  * blink own strix = draw; own solitude = another exile; own recruiter = another tutor; own skyclave = another exile-on-a-stick; own witch enchanter = another disenchant; phelia grows every time
  * overlord line: cast overlord for impending 5—{1}{b} (enters w/ 5 time counters, not a creature) -> phelia attacks, blinks it -> returns WITHOUT time counters = 5/5 NOW, and "whenever this permanent enters or attacks, mill four, return a non-avatar creature or planeswalker from yard to hand" re-triggers
  * offense: exile their blocker pre-damage (returns to THEM at end step — no counter for phelia, still clears the swing); exile their vial/impending permanent = counters reset
* yorion (companion, {3} to hand as a sorcery): "exile any number of other nonland permanents you own and control. return those cards to the battlefield at the beginning of the next end step" — mass re-etb: strix draws, overlords mill+return, skyclave exiles, recruiter tutors; do NOT blink vial (charge counters reset to 0)
* vial ticks: 2 = phelia/strix/bowmasters at flash speed thru counters; 3 = recruiter/flickerwisp; vial ignores the stack entirely — counterspell decks have to fight your 1-mana artifact or lose to topdecks
* recruiter (toughness ≤2 targets, verified): phelia, solitude (3/2), witch enchanter (2/2 — mdfc, land on the back), harbinger of the seas, lavinia, skyclave, strix, bowmasters, flickerwisp — the toolbox IS the deck; recruiter cannot get overlord (5/5), riddler (4/6), or gilded drake (3/3)
* riddler refuels: etb draw + "as long as you have one or fewer cards in hand, you draw that many plus one" — the empty-handed vial deck's dream topdeck; warp {1}{u} deploys it early
* solitude: flash + evoke (exile a white card) = free removal that lifelinks; the deck's answer to being under pressure
* karakas: bounce own phelia vs removal; bounce their marit lage (token = gone forever), emrakul, atraxa
* harbinger 1-of: "nonbasic lands are islands" + 4 wasteland = soft lock vs greedy manabases; recruiter-able

**mulligans:**
* snap keeps: vial + phelia + lands + any etb body; recruiter + solitude/interaction (toolbox skeleton)
* good keeps: 2 lands + vial + 2 bodies (vial IS the mana); stp/fow + phelia + riddler
* pitch: no white mana no vial; all 5-drops (overlord/riddler/solitude clumps); count white cards for solitude evoke + blue for fow before keeping
* 80-card note: yorion consistency math is looser — mull aggressively for VIAL or a 2-land curve-out, the deck floods etbs later regardless

---
---
**interaction targets — what you save it for:**
* fow: their combo card g1 (s&t, doomsday, reanimate-class); post-board the hate they aim at your yard? you barely use the yard — spend it on their PLAN
* swords: real clocks only — murktide, guide-class aggro, marit lage answer #2 (karakas is #1); don't stp their strix-class value bodies
* solitude: the biggest body on the table when you're behind; evoke only under pressure — hardcast when vial=5 or the game is long
* phelia-as-interaction: their attacking/blocking problem for a turn, their vial/saga/impending counters reset — she is removal that grows
* skyclave: nonland NONTOKEN mv≤4 — their vial, their chalice, their kaito; can't touch marit lage (token)
* karakas: legendary creatures only — phelia (save her), lage/emrakul/atraxa (bounce = tempo death for them)
* lavinia (main 1-of): "each opponent can't cast noncreature spells with mv greater than the number of lands that player controls" + "if no mana was spent... counter" — free-spell police: their fow/daze/fon/evoke-solitude all die while she's in play
* witch enchanter: artifact OR enchantment on etb — cage/hearse/moon aimed at you, their saga pre-constructs; mdfc = land drop when you don't need it
* consign (board): counter triggered abilities + colorless casts — their chalice CAST and its counter-trigger, eldrazi casts, saga chapters, their oracle trigger
* clarion conqueror (board): "activated abilities of artifacts, creatures, and planeswalkers can't be activated" — their vial, emry/forge, grindstone, sneak attack? NO (enchantment) — artifacts/creatures/pw only
* gilded drake (board): "exchange control of this creature and up to one target creature an opponent controls" — steal the s&t fatty/murktide/reanimated archon; the exchange is not a may for them
* opposition agent (board): flash + "you control your opponents while they're searching" — their fetch cracks, doomsday piles, recruiter/stoneforge searches; brutal at instant speed
* faerie macabre/cage (board): yard axis — macabre is FREE (discard, exile 2) and dodges counters; cage stops reanimator + their recruiter-class library-to-play but ALSO your nothing (you cheat nothing into play — vial is from HAND, cage-proof)

---
---
**matchups & sideboard** // post-candelabra field (2026-05-18→07-01 window shares; tron 9.3% pre-ban — expect its share redistributed); ALL cells n<30 = mechanics-derived judgment, tune at the table

**izzet delver — 7.7% of field:**
* their plan: bolt your 2-drops, daze/pierce your spells, murktide/tamiyo clock
* vial beats their whole counter suite; every bolt on a strix/recruiter is card-neutral for you (etb already banked); solitude eats murktide; phelia exiles their tamiyo before the flip
* in: +1 gilded drake
* out: -1 lavinia

**show and tell — 6.9%:**
* their plan: s&t/sneak the fatty t2-3 behind counters
* fow the s&t g1; karakas bounces emrakul/atraxa the turn they land; drake STEALS the fatty (exchange is not optional for them); deafening chokes their cantrip setup
* in: +1 gilded drake +2 deafening silence +3 consign
* out: -2 orcish bowmasters -1 witch enchanter -1 skyclave apparition -1 flickerwisp -1 harbinger of the seas

**energy — 5.5%:**
* their plan: guide lifegain + fast wr bodies; a damage race you don't want
* solitude + stp on guide-class on sight; phelia eats attackers mid-combat math; strix chumps forever w/ deathtouch — your bodies outvalue theirs in every trade
* in: nothing (the main is built for this)
* out: nothing // if you must: -1 lavinia +1 drake

**grixis reanimator — 5.1%:**
* their plan: rite/exhume-class the archon behind discard
* macabre is free and counter-proof; cage turns their whole deck off ("creature cards in graveyards and libraries can't enter the battlefield" — your vial is from hand, unaffected); karakas their legendaries; drake steals what resolves
* in: +2 faerie macabre +2 grafdigger's cage +1 gilded drake
* out: -2 orcish bowmasters -1 harbinger of the seas -1 lavinia -1 flickerwisp

**blue artifacts — 4.6%:**
* their plan: saga constructs + emry/forge engines + counter backup
* clarion is the whole matchup ("activated abilities of artifacts... can't be activated" = emry, forge, saga III, constructs still attack but their engine dies); witch enchanter recruiter-able answer #4-6
* in: +3 clarion conqueror +3 consign to memory
* out: -1 solitude -2 swords to plowshares -1 lavinia -1 karakas -1 flickerwisp

**doomsday — 4.4%:**
* their plan: doomsday pile -> oracle behind thoughtseize/counters
* consign their oracle trigger; oppo agent flash on the DOOMSDAY RESOLUTION (they search — you control it, they exile the pile); deafening = one noncreature spell/turn kills the combo turn dead
* in: +3 consign +2 deafening silence +1 opposition agent
* out: -4 swords to plowshares -1 solitude -1 skyclave apparition

**lands — 4.2%:**
* their plan: loam grind + wasteland lock + marit lage out of nowhere
* karakas the lage (token never comes back); harbinger + own wastelands = their nonbasics are islands, the deck stops functioning; vial keeps deploying thru port
* in: +1 opposition agent (their crop rotation/map searches) — cage does nothing here, stay clean
* out: -1 baleful strix

**dimir tempo — 4.1%:**
* their plan: your old seat — push/snuff your bodies, bowmasters, goyf clock, consign your triggers
* they CAN consign phelia's trigger — bait with a strix blink first; their push math drowns in your etb count; drake steals barrowgoyf/murktide
* in: +1 gilded drake
* out: -1 harbinger of the seas

**death & taxes — 3.5%:**
* their plan: thalia tax, mom protection, their own vial/phelia game
* the pseudo-mirror of fair; your riddler/overlord top-end outclasses theirs; phelia exiling THEIR vial resets its counters; skyclave/solitude answer thalia-class
* in: +1 gilded drake
* out: -1 lavinia

---
---
**board logic recap (why these 15):**
* 3 clarion + 3 consign: the artifact/trigger axis — clarion for engines (blue artifacts, painter, breakfast-class activateds), consign for chalice/eldrazi/oracle triggers
* 2 deafening silence: combo tax (doomsday, tes, s&t setup turns) — one noncreature spell per turn vs decks that need three
* 2 macabre + 2 cage: yard axis, split free-and-uncounterable (macabre) vs permanent lock (cage); your own deck is cage-proof (vial = from hand)
* 1 gilded drake: the fatty answer that's also a threat — steal-don't-answer
* 1 opposition agent: search punishment (doomsday, fetches, tutors) at flash speed
* 1 yorion: the companion slot — costs a board slot, returns a maindeck's worth of re-triggered etbs every game it's cast
* carroz's board unmodified; atkins 2026-03 ran wrath of the skies/celestial purge instead of macabre/agent — the flex tail is live, tune to local yard density

---
---
**references:**
* list: decks/esper-phelia-yorion-80.txt — carroz, 2nd, legacy challenge 32 2025-09-21, unmodified
* cross-validation: dan atkins 1st MLCG 2026-03-07 (same core, 80c); camp consensus n=56 since 2025-08 (4x phelia 100%, riddler 96%, stp 100%)
* camp data: esper midrange [phelia] n=62 evolving, 54.3% wr vs 41.9% without; yorion mode 51-29 (63.8%) in 12 entries — thin, lean not verdict
* data honesty: zero established matchup cells; zero post-candelabra sample; primer is mechanics + priors, reps will move numbers

---
---

# Grixis Thundertrap (wizards), Ark4n stock (Moxfield primer, Andrew's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/grixis-thundertrap-75.txt (Ark4n 1st, Legacy Challenge 32 2025-11-08, 7-1, unmodified; 2026-07-20).

<!-- PASTE BELOW -->

---
---
:::notes:::
* build = the THUNDERTRAP camp of grixis midrange (n=62 since 2025-08, evolving tier) — camp wr 60.5% (n=86 matches, evolving) vs 44.5% for thundertrap-less grixis; the wizards package is the whole edge signal
* list = ark4n's 7-1 challenge win UNMODIFIED — he owns this camp (1st 2025-08-30, 1st 8-1 2025-10-04, 1st 7-1 2025-11-08, 3rd 2025-12-06); every slot inside camp histograms (4x thundertrap 60/62, 3x flame 48/62, 4x tamiyo 59/62, 2x kaito 59/62)
* the camp cut LIGHTNING BOLT (3/62 decks) for fatal push — this is NOT bolt grixis; removal is push/edict/scorn + flame's 5 dmg mode
* data honesty: ~98% of camp data is pre-2026-05-18 regimes, ZERO post-candelabra-ban (2026-06-29) sample; every matchup cell insufficient (n<30) — matchup notes = mechanics + priors; NO REPS YET
* sole current-regime sighting (adelman 2026-06-27 hex USQ) is a 4x flow state / 4x lórien / 3x barrowgoyf hybrid — different direction, n=1, watch it but don't chase it
* your dimir instincts mostly transfer (thoughtseize/push/fow/tamiyo core is shared) — the new muscle is WIZARD ACCOUNTING for flame of anor

---
**plan:**
* card-advantage tempo: every threat replaces itself, flame of anor is a 2-for-1 stapled to removal, kaito closes; you win long games by never running out
* wizard accounting (the deck's one new skill): flame of anor = "choose one. if you control a WIZARD as you cast this spell, you may choose two" — draw two / destroy artifact / 5 dmg to a creature
  * your wizards (verified type lines): thundertrap trainer (otter wizard), tamiyo (moonfolk wizard) — that's it; kaito is a planeswalker/ninja, NOT a wizard
  * sequencing: keep a wizard alive INTO your flame turn — draw two + kill their threat is the play pattern the whole deck bends toward
* thundertrap (oracle): etb "look at the top four... reveal a noncreature, nonland card from among them and put it into your hand, put the rest on the bottom in a random order" — hits fow/push/cantrips/flame, NEVER hits creatures/lands; a 1/2 body that replaces itself and holds the wizard slot
* tamiyo: attack = investigate (clue bank); "when you draw your third card in a turn" = flip — thundertrap etb + clue crack + draw step does it on YOUR turn easily; flipped tamiyo takes over grindy games
* kaito: ninjutsu off an unblocked thundertrap/tamiyo (return the etb body = re-buy it later); "during your turn... he's a 3/4 ninja and has HEXPROOF" = removal-proof clock; 0 = surveil 2 + draw when they lost life
* push revolt: fetch first, then push mv≤4 — covers murktide/goyf-class; edict answers hexproof/protection (marit lage, true-name); scorn = bounce the s&t fatty or kill mv≤3
* dress down: flash etb-draw that turns off ALL creature abilities — their goyfs become 0/1s (*/* is a characteristic-defining ability), germ tokens die (0/0), mom/thalia blank; also cycles at eot when you just need a card
* mystic sanctuary: live w/ 7 other islands in the list (3 usea, 2 volc, island, sewers — sewers is verified Land — Island Swamp); eot sanctuary -> rebuy flame/fow/push is the endgame loop
* bowmasters/lórien/spellbomb: the anti-blue + anti-yard glue you already know from dimir

**mulligans:**
* snap keeps: thundertrap + flame + interaction (the engine hand); thoughtseize + push + tamiyo + cantrips (the dimir hand)
* good keeps: 2 lands + ponder/brainstorm density; kaito hands w/ an evasive 1-2 drop to ninjutsu off
* pitch: no-blue hands (fow + flame + thundertrap all want it); 1-land no-cantrip; all-removal no-threat
* count blue for fow; the deck mulls like dimir tempo — velocity over power

---
---
**interaction targets — what you save it for:**
* thoughtseize: their plan card — combo piece g1, the hate piece post-board; you have 4, spend the first on information
* fow: reserve for their broken start (s&t, doomsday, reanimate, chalice on the draw); don't burn it on value spells — flame outgrinds those
* push: real clocks (delver-class, guide, goyfs w/ revolt); NOT strix-class value bodies
* flame 5-dmg mode: the mid-size problem (murktide needs push/edict — 8/8; flame kills tamiyo-flips, bowmasters, phelia-class); artifact mode: cage/hearse/moon aimed at you, saga pre-constructs
* edict: hexproof/prot bodies — marit lage ("each opponent SACRIFICES a nontoken creature"... lage is a TOKEN — use the token mode!), true-name, kaito-mirrors during their turn? no — during YOUR turn kaito is theirs-hexproof only on their side's turn; read the board
* scorn: bounce what you can't kill (s&t fatty, reanimated archon — costs them the cheat), kill mv≤3 otherwise
* dress down: their etb on the stack? no — it's not a counter; use it to blank ability-armor (mom protecting, thalia taxing, goyf math) or eot cantrip
* consign (board): chalice CAST + trigger, eldrazi casts, saga chapters, oracle triggers, tron? (post-candelabra tron is collapsing — deprioritize)
* pyroblast/reb (board): "counter target spell if it's blue / destroy target permanent if it's blue" — their fow war, murktide, tamiyo, delver itself; the grixis mirror-breaker
* null rod/meltdown (board): "activated abilities of artifacts can't be activated" / "destroy each artifact with mv X or less" — blue artifacts, painter, vial decks; meltdown x=1 sweeps saga boards for {1}{r}
* blood moon 1-of (board): "nonbasic lands are mountains" — lands/eldrazi/depths; you keep functioning on 1 island + 1 swamp + volcs (mountains still tap red)
* surgical/hearse/spellbomb: yard axis — surgical their combo piece AFTER a discard/counter confirms it's in the yard; hearse ticks every turn vs reanimator/loam

---
---
**matchups & sideboard** // post-candelabra field (2026-05-18→07-01 shares; tron 9.3% pre-ban, expect redistribution); ALL cells n<30 = mechanics + priors, tune at the table

**izzet delver — 7.7% of field:**
* their plan: the tempo mirror w/ worse card advantage — bolt/daze/murktide
* you're the bigger deck: flame 2-for-1s, thundertrap rebuys, kaito hexproof beats their whole removal suite; push + edict cover murktide
* in: +2 pyroblast +1 red elemental blast
* out: -1 sheoldred's edict -1 dress down -1 nihil spellbomb

**show and tell — 6.9%:**
* their plan: cheat the fatty behind counters
* thoughtseize the s&t, fow the backup, scorn BOUNCES what resolves (they paid 3 + the fatty for nothing); pyroblast their counters AND the s&t itself (blue)
* in: +2 pyroblast +1 red elemental blast +1 consign +1 force of negation
* out: -3 fatal push -1 dress down -1 orcish bowmasters

**energy — 5.5%:**
* their plan: guide lifegain + fast wr bodies
* push/flame their early bodies, bowmasters punishes their draw effects, barrowgoyf (board) blocks forever w/ deathtouch+lifelink and outgrows the race
* in: +2 barrowgoyf
* out: -1 dress down -1 nihil spellbomb

**grixis reanimator — 5.1%:**
* their plan: discard into rite/exhume archon
* thoughtseize/fow the enabler, surgical the archon once it's binned, hearse ticks the yard empty; edict answers a resolved archon (their only body)
* in: +1 surgical extraction +1 unlicensed hearse +1 consign to memory
* out: -2 dress down -1 tyrant's scorn

**blue artifacts — 4.6%:**
* their plan: saga constructs + emry/forge + counters
* null rod turns the deck off; meltdown x=1-2 sweeps; flame's artifact mode maindeck; pyroblast their counter half
* in: +2 null rod +2 meltdown +1 red elemental blast
* out: -3 thoughtseize -1 sheoldred's edict -1 tyrant's scorn

**doomsday — 4.4%:**
* their plan: pile -> oracle behind thoughtseize/duress
* thoughtseize the doomsday, fow/pyroblast the pile spells (all blue), consign the oracle trigger, surgical the pile after it's built (spellbomb their yard BEFORE the crack? spellbomb exiles the whole yard — crack in response to reanimate-class only, vs doomsday crack eot pre-combo turn)
* in: +2 pyroblast +1 red elemental blast +1 consign +1 surgical extraction
* out: -3 fatal push -1 sheoldred's edict -1 dress down

**lands — 4.2%:**
* their plan: loam grind, port/wasteland lock, marit lage
* blood moon ends the game if it sticks; edict's TOKEN mode eats lage; hearse stops loam; you run 0 wasteland — moon IS the land axis, don't pretend otherwise
* in: +1 blood moon +1 unlicensed hearse +2 barrowgoyf
* out: -2 dress down -1 tyrant's scorn -1 nihil spellbomb
* keep fow — it's for the lage-makers (crop rotation is an instant)

**dimir tempo — 4.1%:**
* their plan: your old deck — thoughtseize/push/goyfs/kaito
* dress down is a wrecking ball here (barrowgoyf/nethergoyf -> 0/1s, cast MID-COMBAT after blocks); flame kills their tamiyo/bowmasters + draws two; their kaito/tamiyo/fow are all pyroblast targets
* in: +2 pyroblast +2 barrowgoyf
* out: -1 nihil spellbomb -1 sheoldred's edict -1 lórien revealed -1 tyrant's scorn
* keep BOTH dress down — it's the matchup's best card

**death & taxes — 3.5%:**
* their plan: thalia tax, vial deploys, mom/skyclave value
* dress down blanks mom/thalia mid-combat; flame + push clear the board faster than they rebuild // bowmasters note: recruiter tutors to HAND without drawing — no trigger; bowmasters is body+amass only here
* in: +2 barrowgoyf +1 meltdown (their vial)
* out: -1 nihil spellbomb -1 mystic sanctuary -1 lórien revealed

---
---
**board logic recap (why these 15):**
* red blast suite (2 pyroblast + 1 reb + 1 hydroblast): the format's blue density makes pyro the highest-velocity board card; hydro covers red stompy/burn + the mirror's blasts
* artifact axis (2 null rod + 2 meltdown): blue artifacts/painter/vial decks; rod is the lock, meltdown the sweeper
* grind axis (2 barrowgoyf): the dimir tech transfers — deathtouch/lifelink brick wall that wins fair mirrors
* yard axis (1 surgical + 1 hearse, + 2 spellbomb main): reanimator/doomsday/loam coverage without diluting the main
* 1 blood moon: the lands/depths/eldrazi panic button — one copy because the main barely supports it (respect the basics count)
* 1 consign + 1 fon: trigger/colorless + free-counter tail
* ark4n's board unmodified across his three wins (aug/oct/nov) except flex 1-ofs — treat the 1-of tail as tunable, the 2-of core as fixed

---
---
**references:**
* list: decks/grixis-thundertrap-75.txt — ark4n, 1st (7-1), legacy challenge 32 2025-11-08, unmodified
* validation: ark4n 3 challenge wins in the camp; consensus n=62 matches his 75 on every 3+-of; david adelman 2026-06-27 (current regime, n=1) went flow state/lórien hybrid — a fork to watch
* camp data: grixis midrange [thundertrap] n=62 evolving, 60.5% wr (n=86) vs 44.5% without — the biggest camp-vs-parent wr gap in the registry snapshot
* data honesty: zero established matchup cells; zero post-candelabra sample; primer is mechanics + priors, reps will move numbers

---
---

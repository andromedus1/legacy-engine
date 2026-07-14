# Doomsday Fantasticar Tempo (Moxfield primer, the maintainer's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/doomsday-fantasticar-tempo.txt (the maintainer's build, 2026-07-13).
Camp validation: the Fantasticar-Doomsday camp exists in the corpus — n=19 maindecks, all since
2026-06-20, and the consensus core matches this list nearly card-for-card (4 Fantasticar mode,
~4 Daze, ~4 Bauble+Petal, 1 LED, no Wasteland, 15-16 lands). Early camp record 35-18 (66%),
8 decks with standings — speculative tier. Board is OFF-camp (see board logic recap).

<!-- PASTE BELOW -->

---
---
:::notes:::
* build = the emerging FANTASTICAR camp of doomsday (n=19 corpus maindecks, all since 2026-06-20, copy mode 4x at 95%): tamiyo/murktide tempo package swapped for 4 fantasticar + max 0-drop artifacts (4 petal, 2 bauble, 1 LED) + 4 daze
  * this 75 vs camp consensus — core identical; deviations: +2 flow state +1 jace md (camp runs cabal ritual 11/19, misdirection 5/19, or a 2nd oracle instead)
  * early camp signal: 35-18 (66.0%) across the 8 decks w/ standings — SPECULATIVE tier, not a read
* board = full dimir-shell switch (10 creatures + 5 spells) — NOT the camp's combo-protection board; the goyf half is camp-validated (goyf in 10/19 boards, avg 3.6), the murktide/brazen half is 0/19 = your untested harder-tempo-pivot
* tech NOT in this 75 (vs stock doomsday tempo / camp boards): consign, fatal push, surgical, duress, unearth, wasteland — matchup notes flag each hole where it bites
* matchup wrs = archetype-level doomsday (camps pooled, full corpus) vs local field — priors, not measurements of this build

---
**plan:**
* three decks in one:
  * fair mode: fantasticar + daze/fow tempo — a 4/4 flier that attacks every turn you cast a cantrip
  * kill mode: doomsday -> 5-card pile -> thassa's oracle
  * post-board: real dimir tempo shell (goyf/murktide/brazen/dauthi) w/ a combo finish they must respect
* fantasticar rules block (oracle-verified):
  * {3} legendary artifact — VEHICLE, 4/4, flying; dark ritual casts it t1 ({B}{B}{B} pays {3})
  * every noncreature cast: MAY animate until EOT — your turn = attacker; THEIR turn = instant-speed brainstorm/daze -> surprise 4/4 flying blocker
  * 4th noncreature spell in one turn: may sac -> FOUR 4/4 flying haste constructs = 16 dmg — a second kill that needs no oracle, no graveyard, no library
  * not a creature on their turn unless you animate -> dodges sorcery-speed removal, edicts, wraths; colorless -> pyroblast/reb can't touch it
  * it does NOT pitch to fow/fon (colorless!) — count your actual blue cards before keeping
  * legend rule: extras are redundancy vs removal; or sac the first to the 4th-spell trigger and redeploy the next
* the clean pile (top -> bottom): street wraith / edge of autumn / thassa's oracle / buffer / buffer
  * kickoff draw -> wraith (2 life) -> edge (sac a land) -> oracle w/ {U}{U} -> devotion 2 >= library 2, win
  * cavern names wizard -> oracle uncounterable; LED cracks AFTER doomsday
  * count BEFORE casting: kickoff draw + free-draws + {U}{U} confirmed
* the construct pile: fantasticar already on board -> doomsday just stacks 4 castable spells -> sac -> 16 flying haste dmg this turn; no oracle exposure to counters/consign
* jace wielder = backup win: oracle countered/exiled, or grindstone/bowmasters games — draw from empty library wins; sweeper-proof threat in grinds // NO unearth in this list — jace IS the oracle recovery
* bauble notes: draw lands NEXT upkeep (their bowmasters pings it); sac feeds an artifact card type to goyf; chains the 4th-spell count for free
* flow state @2: instant+sorcery in yard -> impulse 2; fetch+cantrip yard turns it on by t2
* doomsday costs HALF YOUR LIFE — track burn range + your own wraith/thoughtseize spend before committing

**mulligans:**
* snap keeps: ritual + doomsday + cantrip/protection; ritual + fantasticar t1 + cantrips (the fair curve-out)
* good keeps: fantasticar + daze/fow + 2 lands — the tempo hand; combo finds itself off cantrips
* pitch: no-cantrip no-threat no-combo hands; all-protection-no-plan
* fow discipline: fantasticar is NOT a blue card — a hand of fow + 2 fantasticar has no pitch
* life is a resource w/ a floor: wraith + thoughtseize + doomsday half — stingier vs red/energy

---
---
**interaction targets — what you save it for:**
* fow/daze: the combo turn OR their gameplan card in fair mode — pick a job per game; daze also protects an animated fantasticar from instant removal (they must pay 1 more)
* fon (2 post-board): free counter on THEIR turn — their combo, their sweeper
* flusterstorm: the stack war ON your combo turn (instants/sorceries only)
* thoughtseize (2): turn BEFORE you go off — strip the counter, see the coast
* long goodbye (2 post-board): can't be countered, mv<=3 — thalia, DRC, bowmasters, teferi; NOT thought-knot (mv4), NOT murktide (mv7 — delve cuts cost paid, not mv)
* brazen borrower / petty theft {1}{U} (2 post-board): bounce chalice, TKS, saga construct, leyline binding; body blocks only fliers
* dauthi (2 post-board): yard denial that clocks — voids their murktide fuel + reanimation lines; shadow = near-unblockable
* murktide (2 post-board): the finisher in fair games — count your OWN yard vs goyf first (murktide eats the fuel goyf counts)

---
---
**matchups & sideboard** // wr = archetype-level doomsday priors (camps pooled, full corpus) vs local field; imputed = no cell data // standard transform-out = 2 doomsday 1 LED 1 wraith 1 edge (keeps 2 doomsday + oracle to stay honest)

**izzet delver — 11.2% of field, 42.7% wr (n=113, worst measured — burn taxes the half-life):**
* their plan: DRC/cutter clock + bolt your face + daze/fow the oracle
* fantasticar is the tech: bolt doesn't kill a 4/4, pyroblast can't target it, blocks DRC forever; animate on their turn w/ a spare brainstorm
* in: +4 barrowgoyf +2 murktide +2 long goodbye
* out: -2 thoughtseize -2 doomsday -1 LED -1 wraith -1 edge -1 consider
* goyf deathtouch wins the murktide war; their bolt bounces off both threats

**show and tell — 10.3%, 59.0% wr (n=154):**
* their plan: s&t/sneak the fatty; you're faster + your combo ignores their board
* fow/fon/daze the s&t itself // NO consign in this 75: atraxa etb + emrakul trigger go unanswered — race, don't posture
* in: +2 force of negation +1 flusterstorm
* out: -1 jace -1 consider -1 bauble

**white beanstalk — 7.5%, 49.6% wr (n=62):**
* their plan: beanstalk card adv + swords/binding; slow — combo under it OR transform over it
* wrath of the skies is X-energy sweep — hits fantasticar/goyf/constructs at X>=3-4: stagger threats into open mana
* petty theft the binding/beanstalk; jace stays = sweeper-proof win
* in: +4 barrowgoyf +2 murktide +2 brazen borrower
* out: -2 doomsday -1 LED -1 wraith -1 edge -1 consider -1 bauble -1 daze

**dimir tempo — 7.5%, 46.3% wr (n=171 — the deck you know from the other side):**
* their plan: seize/push/snuff + bowmasters + tamiyo/kaito clock
* G1 their removal is half-dead: push/snuff can't touch an un-animated vehicle
* post-board they trim removal vs "combo" -> your 10 threats land unanswered; kill bowmasters BEFORE cycling/bauble draws
* in: +4 barrowgoyf +2 murktide +2 dauthi
* out: -2 doomsday -1 LED -1 wraith -1 edge -1 consider -1 bauble -1 jace
* dauthi voids their goyf/murktide fuel; your goyf outgrows theirs (your yard fills faster)

**jeskai midrange — 7.5%, ~50 (imputed):**
* their plan: counters + REB + swords/phlage + wrath of the skies
* your threat base is REB-proof: fantasticar colorless, goyf black; stagger into the X-sweep
* in: +4 barrowgoyf +2 force of negation
* out: -2 doomsday -1 LED -1 wraith -1 edge -1 bauble
* jace stays: their swords can't answer it, draws through the grind

**azorius midrange — 6.5%, ~50 (imputed):**
* counters + binding + teferi (mv3 = long goodbye, uncounterable through their fow)
* in: +4 barrowgoyf +2 murktide +2 long goodbye
* out: -2 doomsday -1 LED -1 wraith -1 edge -1 consider -1 bauble -1 daze

**black midrange — 6.5%, ~50 (thin data):**
* discard + bowmasters grind; they strip piles — so stop being a pile deck
* edict-proof: sheoldred's edict can't make you sac a vehicle that isn't a creature
* in: +4 barrowgoyf +2 murktide +2 long goodbye
* out: -2 doomsday -1 LED -1 wraith -1 edge -1 consider -1 jace -1 bauble

**black saga storm — 6.5%, ~50 (thin data):**
* beseech storm race // NO consign: the tendrils storm trigger lives — fight the beseech/rituals on the stack instead
* in: +1 flusterstorm +2 force of negation +2 dauthi (voids their yard, clocks behind shadow)
* out: -2 bauble -1 jace -1 edge -1 consider

**death & taxes — 5.6%, 68.1% wr (n=78, BEST — the reason to play doomsday):**
* their plan: vial + thalia tax the pile; mother protects; no counters
* thalia ON SIGHT (long goodbye — uncounterable, budget her tax while she's out); counters near-dead through vial
* karakas CAN bounce an ANIMATED fantasticar (legendary) — keep it an artifact until the swing matters; the construct sac ignores karakas entirely
* oracle isn't legendary — karakas never touches the kill
* in: +2 long goodbye +2 brazen borrower
* out: -4 daze

**doomsday mirror — 5.6%, 50.0% (n=53):**
* discard war decides it // NO consign: you can't fizzle their oracle anymore — win the seize/fluster war or race
* your edge: the construct kill — they hold counters for doomsday->oracle, you kill from a resolved fantasticar w/ 4 cantrips
* in: +1 flusterstorm +2 force of negation +2 dauthi
* out: -2 bauble -1 jace -1 consider -1 flow state

**eldrazi — 5.6%, 45.5% wr (n=137):**
* their plan: chalice@1 (kills petal/bauble/brainstorm/ponder), TKS strips, fast clock
* fantasticar lives @3 and blocks linebreaker/smasher traffic; construct kill under chalice is hard — count castable spells first
* NO consign for the chalice trigger — petty theft bounces the chalice (or TKS) instead
* long goodbye does NOT kill TKS (mv4)
* in: +2 brazen borrower +2 force of negation
* out: -3 daze -1 consider

**painter — 4.7%, 48.9% wr (n=131):**
* their plan: painter names blue -> REBs answer everything blue; grindstone mills you
* your threats don't care: fantasticar colorless, goyf black — REB pile rots
* grindstone milling you is LIVE: oracle devotion vs empty library, or jace draw-from-empty // NO unearth — if oracle is exiled, jace is the ONLY recovery: protect it
* long goodbye the servant (mv2)
* in: +4 barrowgoyf +2 long goodbye
* out: -3 daze -1 consider -1 bauble -1 flow state

**blue artifacts — 3.7%, 44.7% wr (n=96):**
* their plan: saga constructs + kappa (ward {4}, unblockable pump) + counter backup
* kappa is STILL the hole (no hurkyl's in this 75; petty theft + ward = 6 mana, unreal) — race it in the air: murktide outsizes it, your constructs fly, theirs don't
* goyf deathtouch eats saga constructs; daze weak into tomb/saga mana
* in: +4 barrowgoyf +2 murktide
* out: -2 daze -2 doomsday -1 wraith -1 edge

**energy — 3.7%, 55.6% wr (n=11, speculative):**
* their plan: guide/ocelot lifegain swarm; their clock vs your half-life is the matchup
* goyf lifelink stabilizes; animate fantasticar on their turn (spare cantrip) = repeatable 4/4 block
* keep the full combo — they can't touch the pile; just combo a turn earlier than comfortable
* in: +4 barrowgoyf +2 long goodbye
* out: -2 thoughtseize -1 wraith -2 bauble -1 jace

**esper midrange — 3.7%, ~50 (imputed):**
* discard + swords + counters grind; transform
* in: +4 barrowgoyf +2 murktide +2 long goodbye
* out: -2 doomsday -1 LED -1 wraith -1 edge -1 consider -1 bauble -1 jace

---
---
**board logic recap (why these 15):**
* the board IS a dimir tempo shell: 10 creatures (4 goyf, 2 murktide, 2 brazen, 2 dauthi) + 5 spells (2 fon, 2 long goodbye, 1 fluster) — post-board you're a threat-dense fair deck w/ a combo they must respect
* camp check (n=19 fantasticar-doomsday boards): the GOYF half is validated (10/19 run it, avg 3.6 — plan-package class, 0-or-max); the murktide/brazen half is 0/19 — your untested harder-tempo-pivot, settle it by reps
* what you gave up vs camp/stock boards + where it bites:
  * consign (camp 1.9 avg): mirror oracle-fizzle, eldrazi chalice trigger, tendrils storm trigger — flagged in those matchups
  * fatal push: long goodbye x2 covers mv<=3 uncounterably; NOTHING in the 75 kills TKS or an opposing murktide — bounce or block
  * surgical/duress: no yard hate (dauthi is the proxy), no discard #3-4
  * unearth (md): no oracle recovery — jace is the backup win, protect it in grindstone/counter matchups
* goyf/murktide tension: goyf counts yard card types, murktide EATS the yard — goyf first, murktide off the excess
* no wasteland in the 75 — camp-consensus cut (0/19 run it): the slot bought 4 daze + denser combo mana; saga/depths lands go unanswered — race them

---
---
**references:**
* decklist: decks/doomsday-fantasticar-tempo.txt
* stock tempo-camp analysis + prior primer: decks/doomsday-tempo-analysis.md, decks/doomsday-tempo-moxfield-primer.md
* camp discovery + early record: engine corpus, fantasticar-doomsday n=19 (2026-06-20..07-01), standings 35-18
* field + verdicts: decks/best-deck-best-call-ranking.html (2026-07-13)

---
---

# Dimir Tempo — Barrowgoyf Grind (Moxfield primer, the maintainer's list conventions)

Paste everything below the marker into the Moxfield deck description.
Board = decks/dimir-tempo-optimized.txt (2026-07-04 refresh, n=263 field-scoped winners, established tier).

<!-- PASTE BELOW -->

---
---
:::notes:::
* board updated 2026-07-04 (engine refresh, n=263 winners, established tier):
  * -1 fatal push (4th) -> +1 consign (3rd) // winners' copy-mode = 3; pitch-class valley-at-1
* online-meta variant: -1 toxic deluge -> +1 surgical extraction // reanimator+doomsday ~12% online
* engine overrides held: defense grid (0.0% of winners) & damping sphere (3.0%) stay OUT // systematic scorer false-positives, tracked
* prev board (massacre/hurkyl's/flusterstorm era) retired — flusterstorm & echoing truth not in collection anyway

---
**plan:**
* strip -> stick -> ride: t1 discard/cantrip, t2-3 threat w/ prot open, then tax everything they do
  * tamiyo is the engine: attack -> clue -> flip off 3rd draw -> free spells
  * bowmasters on THEIR cantrip, not proactively // flash; punish brainstorm/ponder/flow state
  * kaito via ninjutsu on unblocked tamiyo/dauthi -> surveil engine + hexproof on your turn
* wasteland is a spell: cut the 2nd color / saga / tomb, esp. behind harbinger
  * harbinger = SYMMETRIC (nonbasics -> islands, yours too; only basic swamp makes B after)
    * deploy black FIRST, then harbinger -> mono-blue lock
* murktide vs barrowgoyf: murktide = clock vs combo; barrowgoyf = attrition vs fair
  * tension: delve eats the yard goyf counts — goyf first in grind matchups
* spread honesty: 55-62% vs blue/combo, 36-46% vs fair-creature/prison — spend slots accordingly

**mulligans:**
* keep = 2 lands + threat + interaction, OR cantrip-dense (2+) w/ 2 lands
* pitch: 1-landers w/o brainstorm; 4+ lands no-action; all-interaction-no-clock
* count blue cards before keeping fow hands
* vs combo: thoughtseize/fow + clock > value; vs fair: grind pieces > daze (ship daze-heavy hands)

---
---
**interaction targets — what you save it for:**
* fow/fon: their NAMED gameplan card only (s&t, doomsday, storm engine) — never value/cantrips unless lethal-adjacent
* daze: t1-t2 tempo window; dead late + vs vial/tomb mana — first cut in slow matchups
* consign ("counter target triggered ability or colorless spell"):
  * oracle etb win trigger / emrakul cast trigger + emrakul itself / the storm trigger (copies die) / saga chapters / eldrazi casts / phlage trigger
* thoughtseize: t1 vs combo (take the engine); mid-game vs fair (take sweeper/bomb)
* push/snuff: murktide, DRC, thalia-on-sight, guide of souls — mana-efficient threats only
* null rod: vial, jitte, grindstone, LED, saga constructs // NOTE: turns off OUR ee too — rod first, ee backup

---
---
**matchups & sideboard** // wr = adaptive matrix vs local field; imputed = no cell data

**izzet delver — 11% of field, 55% wr (evolving n=71):**
* their plan: cheap threats + burn/counter, murktide top; bolts your tamiyo/kaito
* interaction: push/snuff = murktide/DRC; hydroblast counters ANY red spell or kills red permanent (bolt, pyroblast, price)
* in: +2 hydroblast +1 snuff out +1 sheoldred's edict
* out: -2 thoughtseize -1 daze -1 brazen borrower
  * // engine also shows consign lift here (n=71) — swap for edict vs trigger-heavy builds

**show and tell — 10%, 62% wr (best matchup):**
* their plan: s&t/sneak -> omniscience/emrakul/atraxa, counter prot
* interaction point: the ENABLER cast (fow/fon/daze the s&t); thoughtseize it pre-cast
  * consign: emrakul = colorless spell AND cast-trigger both; sneak ACTIVATION not consignable (activated, not triggered)
* harbinger islands their sol lands; clock + hold prot
* in: +3 consign +2 force of negation +1 harbinger
* out: -3 fatal push -1 snuff out -2 barrowgoyf

**white beanstalk — 7.5%, 55% wr:**
* their plan: white value pile -> beanstalk card adv, binding/swords on threats
* interaction: counters for beanstalk + their sweeper; grind w/ goyf+kaito; harbinger the greedy whites
* in: +1 barrowgoyf +1 sheoldred's edict +1 harbinger
* out: -2 daze -1 brazen borrower

**mirror — 7.5%, 50%:**
* edges: dauthi (voids their goyf/murktide fuel + shadow clock), 3rd goyf, bowmasters discipline
* counter murktide on the stack; remove goyfs on board
* in: +1 dauthi +1 barrowgoyf +1 snuff out
* out: -2 daze -1 brazen borrower
  * // engine mirror plan wanted hydroblast in — UB mirror, no red targets; rejected as correlational noise

**jeskai midrange — 7.5%, ~50 (imputed):**
* their plan: counters + swords + phlage/clique, pyroblast war postboard
* interaction: hydroblast their pyroblast/bolt/phlage; consign the phlage trigger
* in: +2 hydroblast +1 consign
* out: -2 daze -1 thoughtseize

**azorius midrange — 6.5%, ~50 (imputed):**
* removal pile, few creatures, walkers + equipment
* in: +1 barrowgoyf +1 sheoldred's edict (walker mode) +1 harbinger
* out: -2 fatal push -1 snuff out

**black midrange — 6.5%, ~50 (thin data):**
* discard+goyf grind; whoever's threat sticks
* in: +1 barrowgoyf +1 sheoldred's edict +1 toxic deluge
* out: -2 daze -1 brazen borrower

**black saga storm — 6.5%, ~50 (thin data):**
* their plan: beseech storm on urza's saga mana; LED hands
* CONSIGN IS THE CARD: counters the storm trigger itself + saga chapters; null rod = LED + constructs; dauthi voids their yard
* fow the beseech; thoughtseize the engine t1
* in: +3 consign +1 null rod +1 dauthi
* out: -3 fatal push -1 snuff out -1 murktide

**death & taxes — 5.6%, 36% wr (worst — slot-ROI says punt; board efficient, don't overboard):**
* their plan: vial cheats taxers in; thalia/mother/revoker + swords + jitte
* interaction: thalia ON SIGHT; null rod = vial AND jitte; toxic@2-3 sweeps wide
* counters near-dead through vial — cut daze hard
* in: +1 toxic deluge +1 sheoldred's edict +1 null rod +1 snuff out
* out: -3 daze -1 thoughtseize

**doomsday — 5.6%, 54% wr (evolving n=30):**
* their plan: doomsday pile -> oracle; tempo camp = tamiyo/murktide shell
* interaction ladder: thoughtseize the doomsday -> counter the doomsday cast -> consign the ORACLE ETB TRIGGER (win dies even if oracle resolves)
* bowmasters on their cantrip chain = real damage + kills their tamiyo
* in: +3 consign +2 force of negation +1 dauthi
* out: -3 fatal push -1 snuff out -2 barrowgoyf
  * // engine shows a hydroblast lift signal (n=30) — if you see red g1, 1 hydro over 1 consign

**eldrazi — 5.6%, 46% wr:**
* their plan: tomb/eye ramp -> chalice, TKS, smasher; all colorless
* consign counters their WHOLE DECK (colorless spells + cast triggers); harbinger islands tomb/eye; toxic resets
* chalice@1 is the trap — lead cantrips before their t2 when possible
* in: +3 consign +1 harbinger +1 toxic deluge +1 sheoldred's edict
* out: -3 daze -2 thoughtseize -1 brazen borrower

**painter — 4.7%, 48% wr:**
* their plan: painter's servant + grindstone, REB-heavy red shell
* interaction: null rod stops grindstone; ee@1-2 hits both pieces; hydroblast kills painter / counters blasts
* null rod + ee anti-synergy — rod first, ee backup
* in: +1 null rod +1 engineered explosives +2 hydroblast
* out: -2 daze -1 kaito -1 brazen borrower

**blue artifacts — 3.7%, 41% wr (bad — race or lock):**
* their plan: saga constructs + thought monitor card adv, mostly-colorless base
* consign their colorless casts + saga chapters; null rod their activated base; wasteland every saga
* in: +3 consign +1 null rod +1 engineered explosives
* out: -2 thoughtseize -2 daze -1 fatal push

**energy — 3.7%, ~50 (imputed):**
* their plan: guide of souls/ajani WR energy, wide + lifegain
* guide of souls on sight; toxic@2 sweeps; hydroblast = red threats/removal
* in: +1 toxic deluge +1 engineered explosives +1 sheoldred's edict +2 hydroblast
* out: -3 daze -2 thoughtseize

---
---
**board logic recap (why these 15):**
* 3 consign: triggered abilities + colorless — most systematic card vs this field; winners run exactly 3 (67% of n=263)
* 2 fon / 2 hydroblast: pitch-class, 2nd copy = fuel/redundancy where live (~44% / ~21% of field)
* 1-of flex (dauthi/ee/edict/snuff/rod/harbinger/goyf/toxic): natural-budget insurance, all owned
* NOT here: defense grid (0.0% of 263 winner boards) + damping sphere (3.0%) — engine wants both; overridden, mechanisms tracked
* slot-by-slot + copy histograms: decks/dimir-tempo-optimized-analysis.md

---
---
**references:**
* engine analysis: decks/dimir-tempo-optimized-analysis.md
* cross-meta verdict (stay dimir for local): decks/dimir-vs-doomsday-tempo-comparison.md
* session study: https://claude.ai/code/artifact/b954ac08-4558-4303-8c36-9a9f536ed26f

---
---

# White Beanstalk — Phelia tempo-control (Moxfield primer, Andrew's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/white-beanstalk-moxfield.txt (unstar 6-2, Legacy Challenge 32 2026-07-05; post-Candelabra modal build).

<!-- PASTE BELOW -->

---
---
:::notes:::
* why this deck (agency page 2026-07-31): white beanstalk = #1 grounded agency (40.9, cov 83%) — ZERO measured matchups under 40% shrunk; nothing popular runs it over. adj wr 53.3 vs field; era record 161-124-8 (56.5%) since 2026-05-11
* this is the deck for people who liked the WU phelia/riddler control shell — same spine (fow/fon, stp, brainstorm/ponder, phelia, riddler), plus the green engine: up the beanstalk + domain leyline binding + uro. july lists adopted phelia at 3-4x (62% of post-ban builds) — the two decks are converging
* this 75 = unstar verbatim (challenge 6-2, 07-05) — matches the post-candelabra 60-card modal at essentially every slot; only spice = 2 murktide (minority adoption, kept: the shell's fastest clock)
* the label blends FOUR shells (era pool 75: 54 sixty-card, 21 eighty-card yorion; camp discovery FAILS honestly at stability 0.887): this phelia-tempo build, a binding-less uro-ramp build (reojund 7-2), a scion of draco/leyline of the guildpact domain-zoo (colin logan 7-2 paper), and 80-card yorion. this primer covers the first
* contested slots (post-ban histograms, n=16): riddler 3x:6/4x:6 (4 here); phelia mode 3x (4 here, unstar's count); tamiyo 31% at 3-4x (0 here — it's the OTHER camp's slot); uro mode 1x (1 here); wasteland mode 1-2x (2 here); consign MAIN 3x in 44% of lists (board-only here)
* wr priors below are mostly ban-scoped fallback windows back to 2024-12-16 — they blend this build with older generations. only the izzet cell is established (n=103); era-window cells are thin. priors, not measurements. NO REPS on this 75
* known board gaps vs the july pool: deafening silence (75% adoption, mode 2x) not in this 15 — storm-heavy field: -1 stony -1 pyroblast +2 deafening silence; yard hate = 2 priest only (no surgical/RiP — RiP would kill our own loam/uro anyway)

---
**plan:**
* the engine (all grounded in oracle text): up the beanstalk draws "when it enters AND whenever you cast a spell with mana value 5 or greater" — mv is the PRINTED cost, not what you paid
  * leyline binding = mv6, flash, domain: "costs {1} less for each basic land type among lands you control" — xander's lounge (island/swamp/mountain) + tundra + savannah = all five types across three lands. routinely {1}-{2}, often {W}. one-mana instant-speed exile that cashes a card with beanstalk out
  * quantum riddler = mv5 4/6 flyer, "when this creature enters, draw a card", warp {1}{U} ("cast from your hand for its warp cost. exile it at the beginning of the next end step, then you may cast it from exile on a later turn") — BOTH casts are mv5 casts. warped t2: etb draw + beanstalk draw; recast later from exile: same again. one riddler = up to 4 cards
  * riddler hellbent: "one or fewer cards in hand -> if you would draw, draw that many plus one" — the deck dumps its hand fast; late-game every cantrip and beanstalk trigger doubles
* phelia (2/2 flash dog, attacks -> "exile up to one other target nonland permanent... return at the beginning of the next end step; if it entered under your control, +1/+1 on phelia"):
  * blink OUR stuff: beanstalk (re-trigger etb draw), binding (re-enters -> exiles a NEW target), riddler (etb draw) — each blink also grows phelia
  * exiled TOKENS never return (not cards): marit lage, saga constructs, fantasticar 4/4s — phelia murders tokens on attack
  * their murktide re-enters with zero delve exiles = a 3/3
* removal suite: 4 stp + 4 binding + 1 prismatic ending ("converge — exile if mv <= colors of mana spent" — spend 3 colors off duals, exile mv3)
* murktide tension: delve can eat your OWN loam/uro from the yard — delve away excess lands and spent cantrips, NEVER loam or uro. uro escapes ({G}{G}{U}{U}, exile five others) — escape it before delving when both are live
* loam: dredge 3 REPLACES a draw — don't dredge through beanstalk/riddler triggers blindly; loam rebuys wasteland/fetches and feeds murktide
* karakas: saves our legends (phelia, uro, lavinia post-board), bounces theirs (griselbrand, atraxa) — a bounced marit lage TOKEN dies
* what they do to you: bowmasters taxes the whole engine (every extra draw = a ping — beanstalk/riddler draws all trigger it; kill it on sight); stifle-class effects hit binding's etb trigger and beanstalk triggers; grafdigger's cage only stops uro's escape ("players can't cast spells from graveyards" — escape is a cast from yard); the rest of the deck ignores it

**mulligans:**
* snap keeps: land + fetch + beanstalk + binding/riddler + cantrip — the curve-out (t2 beanstalk, t3 binding + cantrip, t4 warp riddler) buries fair decks
* good keeps: 2 lands + stp/binding + fow + cantrips vs unknown; the deck mulligans well (8 cantrips + riddler hellbent forgives low resources)
* vs combo: fow/fon + blue count is the keep criterion — 21 blue cards in the 60 (brainstorm 4, ponder 4, fow 4, fon 2, riddler 4, murktide 2, uro 1); binding/stp/phelia/beanstalk do NOT pitch
* pitch: all-removal no-engine hands vs blue; hands whose binding needs turn-5 mana (no fetch, no xander's); one-land hands without brainstorm
* xander's lounge and meticulous archive enter TAPPED — sequence t1 or on idle turns; don't let a tapped land delay the binding turn
* wasteland is a 2-of — it's a bonus, never the plan; don't keep denial hands

---
---
**interaction targets — what you save it for:**
* fow/fon: their game-plan card, one job per game; fon ("if it's not your turn... exile a blue card") = free on their turn only, exiles what it counters (kills recursion targets)
* consign to memory (3 post-board): "counter target triggered ability or colorless spell" + replicate {1} — the format's swiss knife: storm triggers, thassa's oracle trigger, saga chapters, dark depths' marit lage trigger, fantasticar (colorless spell AND its token trigger), every eldrazi/tron/forge cast, chalice on the stack
* binding: hold it — flash answers a resolved omniscience, sneak attack, cori-steel cutter, marit lage, their beanstalk; it exiles ANY nonland permanent
* stp/pe: bowmasters, thalia/revoker-class, guide of souls — the cheap engine creatures; pe with 3 colors spent exiles kaito/cutter/static prison tier
* pyroblast/hydroblast: "counter target spell if it's blue/red" OR "destroy target permanent if it's blue/red" — pyro kills kaito, murktide, tamiyo, flow state never resolves; hydro kills blood moon, cutter, channeler and counters bolt
* containment priest (flash): reanimation, show and tell puts, sneak attack, aether vial — "if a nontoken creature would enter and it wasn't cast, exile it instead". WARNING: it exiles our own phelia-blinked creatures (the return isn't a cast) — sequence phelia attacks before flashing priest, or blink only noncreatures (beanstalk/binding) while priest is out
* lavinia: "each opponent can't cast noncreature spells with mv greater than their lands" + "no mana spent -> counter" — their daze/pitch-fow/fon die, doomsday (mv3) dead on 2 lands, beseech (mv4) dead on 3
* wrath of the skies: X energy, pay any amount — "destroy each artifact, creature, enchantment with mv <= energy PAID". dial it: E=1-2 sweeps their cheap board; our beanstalk (mv2) and phelia (mv2) die at E>=2, riddler (mv5)/binding (mv6) survive any sane X
* carpet of flowers: TARGETS an opponent; X = their islands INCLUDING duals (volcanic/tropical/underground sea/tundra all count) — free mana every main phase, both of yours
* stony silence: vial, the one ring, grindstone, keys, monolith-class mana — all activated artifact abilities incl. mana abilities
* karakas: see plan — save ours, bounce theirs, kill lage

---
---
**matchups & sideboard** // shares = current post-candelabra field (2026-07-31 refresh); priors mostly cross-generation BA-window blends — tune at the table // in/out counts balance; the engine core (4 beanstalk, 4 binding, 4 riddler, cantrips) never trimmed unless named

**dimir tempo — 8.6% of field, ~53 prior (era n=9 only, raw 6-3 — unread, treat as even):**
* their plan: thoughtseize/daze/fow tax, bowmasters + push/snuff, goyf + murktide clock, flow state velocity
* bowmasters is THE card vs us — every beanstalk/riddler draw feeds it; stp/binding it on sight, sequence draws when it's off the table
* all their removal is live on our creatures (push, snuff — "nonblack" includes our white/blue bodies — bolt-class no, we're out of burn range); the engine wins anyway: beanstalk/binding are enchantments their whole removal suite can't touch; pyro kills murktide/kaito, carpet runs off their underground seas
* in: +2 pyroblast +2 carpet
* out: -1 loam -1 uro -1 prismatic ending -1 wasteland

**doomsday — 7.5%, ~49 prior (raw 47, n=36 BA):**
* their plan: seize/daze/fow shell into doomsday piles, thassa's oracle kill, tamiyo/murktide fair game
* consign their oracle trigger (the kill dies, they've paid half their life); pyro counters the pile's blue glue AND oracle itself; lavinia = doomsday mv3 dead on 2 lands; binding flash-exiles resolved tamiyo/murktide
* in: +3 consign +2 pyroblast +1 lavinia
* out: -4 swords to plowshares -1 loam -1 uro
* g3 watch: current doomsday boards a 4-barrowgoyf transform package — if g2 showed goyfs, bring 2 stp back (-1 consign -1 lavinia) and play the fair game; binding answers goyfs either way

**azorius midrange — 7.4%, ~57 prior (raw 61, n=18 BA — thin):**
* their plan: the sibling — phelia/riddler bodies, stifle/consign trigger-denial, daze/fow; our engine out-scales their fair game
* play around stifle on binding's etb trigger and beanstalk triggers; their consign can't touch our colored SPELLS but counters our triggers (riddler etb, beanstalk, binding etb) — the warp cast is the bait: one riddler = triggers across two turns, more than their trigger-denial can cover
* we have the green engine and they don't: uro + loam + carpet grind them out
* in: +2 pyroblast +2 carpet
* out: -1 loam -1 uro -1 wasteland -1 prismatic ending

**blue artifacts — 6.9%, ~49 prior (raw 48, n=56 BA):**
* their plan: chalice, saga constructs, emry recursion, thought monitor card adv, fantasticar tokens
* consign = house (chalice cast, saga chapters, fantasticar + its four-4/4s trigger, every colorless cast); wrath at E=0 sweeps every construct token (mv0) for just {W}{W} — dial E to their board; phelia exiles a construct/fantasticar token forever on attack; stony their vial/keys/ring
* chalice@1 hurts (brainstorm/ponder/stp/carpet) — keep a fow for it or consign the cast
* in: +3 consign +1 stony silence +2 wrath of the skies
* out: -1 loam -1 uro -2 wasteland -1 prismatic ending -1 murktide

**energy — 6.6%, ~53 prior (raw 53, n=34 BA):**
* their plan: guide of souls + bombardment engine, static prison on your threats, fast wide boards
* wrath is the card — E=2 sweeps guide/prison/bombardment tier (redeploy beanstalk after, it dies too); hydro kills their red engine pieces; stp the guide t1 every time
* in: +2 wrath of the skies +2 hydroblast
* out: -2 force of negation -1 loam -1 uro

**dimir midrange — 6.3%, ~59 prior (raw 63, n=27 BA — thin):**
* their plan: slower dimir — more discard, bowmasters, goyf grind; our card-per-card engine beats theirs if bowmasters dies
* same package as dimir tempo: pyro + carpet, kill bowmasters on sight
* in: +2 pyroblast +2 carpet
* out: -1 loam -1 uro -1 prismatic ending -1 wasteland

**show and tell — 5.4%, ~44 prior (era n=8, raw 3-5 — thin, our worst top-tier read):**
* their plan: s&t/sneak attack cheat, omniscience free-casts, atraxa/emrakul; our stp is nearly blank
* priest exiles their s&t/sneak CREATURE ("wasn't cast -> exile it instead") — but omniscience is an enchantment and dodges priest: binding is the omniscience answer (flash-exile it before the free-cast turn, or the sneak attack itself); pyro counters s&t on the stack; lavinia counters their omniscience-casts (no mana spent) and pitch-counters; karakas bounces atraxa/griselbrand
* in: +2 pyroblast +2 containment priest +1 lavinia
* out: -4 swords to plowshares -1 loam

**izzet delver — 4.1%, ~61 prior (raw 62, n=103 BA — our best cell, ESTABLISHED):**
* their plan: channeler/murktide + bolt/daze/fow + cori-steel cutter, flow state engine
* the matchup the deck is built for: their bolts don't kill riddler (4/6!), binding/stp answer everything they land, beanstalk out-cards them. hydro counters bolt and kills cutter/channeler; carpet runs off volcanic
* in: +2 hydroblast +2 carpet
* out: -1 loam -1 uro -1 prismatic ending -1 wasteland

**grixis reanimator — 3.5%, no measured cell (imputed favorable — treat as even):**
* their plan: looting/unearth reanimation + discard, archon/atraxa targets, grief evoke
* priest = the plan (reanimated -> exiled); consign counters the archon/atraxa etb trigger if the body lands; pyro their cantrips; stp is LIVE here (kills the reanimated body post-priest)
* in: +2 containment priest +2 pyroblast +1 lavinia (grief/free spells)
* out: -1 loam -1 uro -1 murktide -1 wasteland -1 prismatic ending

**lands — 3.2%, ~56 prior (raw 57, n=53 BA):**
* their plan: loam grind, port/wasteland denial, marit lage; no stack interaction g1
* three lage answers: karakas (token dies), phelia (attack-exile, never returns), binding (exile until it leaves) + consign counters the depths trigger itself; keep basics vs wasteland/port; our loam out-grinds their ports
* in: +3 consign +1 stony silence (skateboard is an equipment — equip off means no hasty lage) +2 wrath of the skies (sphere/exploration/skateboard tier)
* out: -4 swords to plowshares -1 murktide -1 prismatic ending

**death & taxes — 2.8%, ~61 prior (raw 64, n=39 BA):**
* their plan: thalia tax, vial dodge, mom/revoker/overlord bodies, flickerwisp on our binding (their card comes back until binding re-enters and re-triggers — pick the best fresh target)
* wrath at E=2-3 sweeps their board; stony turns vial off; binding/stp thalia FIRST (she taxes the whole engine); priest exiles their vial puts... priest is symmetric-ish — their stuff is CAST except vial: worth it for vial-heavy draws only
* in: +2 wrath of the skies +1 stony silence
* out: -2 force of negation -1 loam

**mystic forge combo — 2.6%, no measured cell (imputed UNFAVORABLE — respect it):**
* their plan: forge top-casts, chalice, grindstone kill, fleshraker; post-candelabra it's slower but live
* consign every colorless cast + chalice; stony = grindstone/keys off; race with warp riddler — their interaction is thin; stp the fleshraker
* in: +3 consign +1 stony silence +1 lavinia
* out: -2 swords to plowshares -1 loam -1 uro -1 prismatic ending

**tes — 2.0%, ~58 prior (raw 62, n=21 BA — thin):**
* their plan: ritual storm, beseech/tendrils, fast; interaction quality decides
* consign the STORM trigger (copies never happen); lavinia = beseech mv4 dead on 3 lands + kills their free-spell lines; fow/fon the business
* in: +3 consign +1 lavinia
* out: -4 swords to plowshares

**tron — 2.0%, no data (n=3; post-candelabra tron is gutted — share still settling):**
* their plan: karn/one ring/kozilek's command over urza lands
* consign every threat they cast (all colorless); stony = one ring/keys/monolith off; wasteland + loam rebuy vs their lands is a real soft-lock
* in: +3 consign +1 stony silence
* out: -4 swords to plowshares

**the soft underbelly (measured bad cells, all low-share):** post ~41 (n=36, THE floor), eldrazi ~45 (n=47), painter ~46 (n=26), aluren ~46 (n=11)
* post: they out-scale the grind and our removal is blank — race with riddler/murktide + wasteland their posts; consign kozilek/ugin casts. in: +3 consign +1 stony; out: -4 stp
* eldrazi: chalice + tks + fast colorless beats; consign every cast, wrath sweeps scions/small stuff; binding answers the big body. in: +3 consign +2 wrath; out: -2 fon -1 loam -1 uro -1 pe
* painter: blood moon HURTS (we run just TWO basics — island + plains; fetch them before moon lands); hydro kills moon/welder, pyro their blue half, stony the grindstone. in: +2 hydroblast +1 stony; out: -1 loam -1 uro -1 wasteland
* aluren: lavinia counters every aluren free-cast ("no mana spent"); binding flash-exiles aluren itself. in: +1 lavinia +2 pyroblast (their blue glue); out: -1 loam -1 uro -1 wasteland

---
---
**board logic recap:**
* 3 consign = the trigger/colorless police — storm, oracle, depths, saga, chalice, fantasticar, all of tron/eldrazi/forge
* 2 carpet = free mana vs every dual-island shell (~a third of the field)
* 2 priest = cheat hate (rean/s&t/sneak/vial) — remember it eats our own phelia returns
* 2 pyro + 2 hydro = the color blasts; pyro doubles as murktide/kaito removal
* 2 wrath = the scalable sweeper vs energy/d&t/wide boards — dial E to spare riddler/binding
* 1 lavinia = free-spell + mv police (tes, aluren, doomsday, omniscience)
* 1 stony = vial/ring/grindstone lock
* known gaps: no deafening silence (july mode 2x, 75% adoption) — storm-heavy field swap: -1 stony -1 pyroblast +2 deafening silence; no surgical/RiP (priest is the only yard hate; RiP would exile our own loam/uro)

**references:**
* list: unstar, Legacy Challenge 32 2026-07-05, 6-2 — post-candelabra 60-card modal
* era sample: 75 decks since 2026-05-11 (54 sixty-card); era record 161-124-8 (56.5%, 51 standings entries); other winners: Jay Wojciechowski 7-0 SCG $1K 05-29 (tamiyo/bowmasters splash), reojund 7-2 challenge 06-21 (binding-less uro ramp), colin logan 7-2 paper 07-11 (scion of draco domain)
* priors: legacy-engine agency page 2026-07-31 (corpus 67,581 decks, corpus_max 2026-07-30; wb row: agency 40.9 #1 grounded, cov 83%, floor = post 40.9 n=36, adj 53.3)
* oracle text grounded via cards.oracle_text (legacy.duckdb, scryfall mirror)

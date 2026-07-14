# Mystic Forge Combo (Moxfield primer, the maintainer's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/mystic-forge-combo.txt (Univerce's exact 75, Legacy Challenge 32 top-10, 2026-07-01).
Moxfield import text: `legacy-engine export deck --deck decks/mystic-forge-combo.txt`.

<!-- PASTE BELOW -->

---
---
:::notes:::
* provenance: the POST-BAN rebuild of mystic forge — candelabra of tawnos (banned 2026-06-29) killed the karn/candelabra tron shape (pre-ban consensus n=53, now illegal). post-ban corpus = 5 decks across THREE shells:
  * THIS 75 = univerce's exact list, challenge top-10 (4-2) — corroborated by ItsSwiftyTime's 5-0 league list (same within 3 cards). the chalice / city of traitors / bauble shell
  * variant (best single result, 6-2 / 3rd same challenge, DethFrmAbove x2): keeps partial tron (4 planar nexus, 4 urza's tower, 4 urza's workshop) + 4 trinisphere; cuts city/bauble/hamlet. two real shells — reps decide
  * a modal consensus over n=5 heterogeneous lists is a franken-list — that's why this is a single winner's 75, not engine consensus
* records: era marginal 55.4% (118-95, 35 decks since 04-20 — this hot marginal is why the engine's ranking flags the deck); post-ban challenge results 6-2 (3rd) + 4-2 (10th). ALL matchup wrs below = full-corpus priors dominated by the DEAD pre-ban tron shape — weakest priors of any primer so far; the new shell is unmeasured
* the redesign has a thesis: the old deck's worst matchup was izzet delver (35.7%, n=155) — the new shell is anti-blue-tempo by construction (chalice@1 vs their one-drops, petrified hamlet vs wasteland, fantasticar vs bolt)
* collection: from-scratch build — own 10/75 (4 leyline, 4 bauble, 1 dismember, 1 flute), zero overlap w/ the blue-black cores; heavy tickets: 4 one ring, 4 ancient tomb, 4 city of traitors, 4 chalice, 4 mox opal, 4 urza's saga, 4 grim monolith

---
**plan:**
* the engine: mystic forge = your library IS your hand (every card colorless or artifact — forge casts artifacts AND colorless spells off the top); one ring draws; monolith + keys make mana; fleshraker turns all of it into damage
* fleshraker rules block (oracle-verified):
  * every colorless spell you CAST -> 0/1 eldrazi spawn token ("sac: add {C}")
  * every OTHER colorless creature ENTERING -> 1 dmg to each opponent — the spawns themselves trigger it
  * so each colorless cast = +1 spawn = +1 dmg (per fleshraker) + a floating mana source; two fleshrakers double the pings
  * a forge turn chains: cast off top -> spawn -> dmg -> sac spawn -> cast the next
* kozilek's command = the flex answer AND the burn kill: {X}{C}{C} instant, choose two — X spawns (= X fleshraker dmg + X mana), scry X + draw, exile creature mv<=X, exile up to X yard cards
  * kill math: fleshraker out, command X=6 for spawns+scry = 6 dmg each opp at instant speed
* fantasticar here is a monster: nearly every spell is a noncreature artifact -> animates on demand (4/4 flying); 4-spell turns are trivial (0-drops + forge) -> sac for four 4/4 flying HASTE constructs = 16 dmg + 4 fleshraker pings
  * skateboard (the saga III bullet): ETB taps a blocker, equip {1} gives fantasticar haste the turn it lands
* chalice discipline (their deck class picks X):
  * X=1 vs cantrip decks — kills brainstorm/ponder/bolt/push/swords; deploy your OWN keys/skateboard FIRST or they're countered too
  * X=0 vs petal/storm decks — but it kills your own petal/opal/bauble/crypt: count what you still need first
* petrified hamlet: name WASTELAND on sight — city/tomb/saga all die to waste otherwise; other names: rishadan port, karakas, maze of ith; still taps for {C}
* one ring: protection from everything until your next turn = the stabilizer vs aggro and the shield on your big turn; burden counters + forge's 1-life exiles add up — track your total
* forge micro: you may look at the top card ALWAYS (free information, check before every fetch-equivalent decision); {T} + 1 life exiles a stuck land; bauble and crypt are free casts off the top that keep the chain moving
* legend rule traffic: forge x3, ring x4, fantasticar x4, opal x4 are all legendary or redundant — extras are removal insurance and forge-exile fodder

**mulligans:**
* the floor: a 2-mana land (tomb/city) or petal+opal start, an engine piece (forge/ring/saga), and something to do turn 1-2
* snap keeps: tomb + monolith + forge/ring; chalice + fleshraker + mana
* one ring stabilizes ANY keep that reaches 4 mana — weight it heavily vs aggro
* pitch: all-payoff no-mana; all-mana no-payoff (the deck mulligans well — forge/ring dig you back)
* no colored mana in the deck — never keep a hand waiting on a color (dismember post-board casts off phyrexian life)

---
---
**interaction targets — this deck interacts with PRISON pieces, not answers:**
* chalice@1: their cantrip/removal engine — the whole reason the new shell exists
* kozilek's command: exile creature mv<=X (DRC X=1, thalia X=2, kappa X=6, murktide needs X=7 — usually too rich); yard mode voids murktide/goyf fuel at instant speed
* tormod's crypt (1 md): reanimator/dredge insurance + free fleshraker trigger off forge
* defense grid (4 post-board): their counters cost +3 off-turn — resolve forge/ring through force of will
* disruptor flute (4 post-board, FLASH): name + lock — the named card costs +3 AND its activated abilities shut off: aether vial, sneak attack, grindstone, lion's eye diamond are all activated-ability cards; flash it in response to the setup
* dismember (3 post-board): the only real removal — it's BLACK (phyrexian), does NOT cast off forge and does NOT trigger fleshraker; hand-cast for {1} + 4 life; kills fleshraker-class hate bears, marit lage needs -5/-5 twice (no)
* leyline of the void (4 post-board): turn-0 yard lock — reanimator/dredge/hogaak class

---
---
**matchups & sideboard** // wr = full-corpus archetype priors — DOMINATED BY THE DEAD PRE-BAN TRON SHAPE; the post-ban shell is unmeasured (n=5). treat every number as a weak prior; the mechanical read is the real content here

**izzet delver — 11.2% of field, 35.7% wr (n=155, WORST — and the matchup the rebuild attacks):**
* their plan: DRC/cutter under daze/fow, bolt your face, waste your city/tomb
* the new shell's answer: chalice@1 (kills bolt/brainstorm/ponder/push — daze is mv2 and lives), hamlet names wasteland, fantasticar shrugs bolt, one ring resets their tempo
* in: +4 defense grid; out: -1 tormod's crypt -1 skateboard -2 manifold key
* deploy chalice BEFORE forge/ring; city of traitors makes 2 — jump straight over their daze window

**show and tell — 10.3%, 45.1% wr (n=193):**
* their plan: goldfish over your prison — chalice@1 misses their top end entirely
* flute is the tech: name SNEAK ATTACK (activated — hard lock) or show and tell (costs +3); grid makes their counter war on your flute/chalice miserable
* in: +4 disruptor flute +4 defense grid; out: -4 chalice -1 crypt -1 skateboard -2 manifold key
* race math: your goldfish is t3-4 w/ fleshraker/fantasticar — you are NOT the beatdown, prison first

**white beanstalk — 7.5%, 56.0% wr (n=89):**
* their plan: beanstalk value + binding/swords; slow
* chalice@1 kills swords/ponder; binding eats one ring (it's not protected after your turn) — bait w/ fantasticar first; saga constructs out-grind
* in: +4 flute (name leyline binding... it's not activated — name up the beanstalk for the +3 tax); out: -2 manifold key -1 crypt -1 skateboard
* honest note: flute's value here is tax-only — thin; keeping 11-12 md cards is fine, don't overboard

**dimir tempo — 7.5%, 48.6% wr (n=197):**
* their plan: thoughtseize + push/snuff + bowmasters + murktide
* discard is HALF-DEAD vs forge (your hand is the library); push kills fleshraker — lean fantasticar (vehicle dodge) + saga; chalice@1 is GOOD here (seize/push/bauble all mv1)
* BOWMASTERS WARNING: one ring draws are a bowmasters feast — under bowmasters, kill it first (command exile X=2 / dismember) or win through fantasticar instead of ring
* in: +3 dismember +4 grid; out: -1 crypt -1 skateboard -2 manifold key -1 voltaic key -1 mystic forge -1 chalice
* command yard-mode eats murktide fuel at instant speed

**jeskai midrange — 7.5%, ~50 (imputed):**
* counters + swords/ending + wrath of the skies (X-energy sweep hits your whole board — stagger, keep command mana up)
* in: +4 grid +3 dismember; out: -4 chalice -1 crypt -1 skateboard -1 manifold key

**azorius midrange — 6.5%, ~50 (imputed):**
* flute names teferi, time raveler — loyalty abilities are activated, so flute locks him out; his STATIC still stops your instant-speed command/flash while he's out, so lock or kill him first
* in: +4 grid +4 flute; out: -4 chalice -1 crypt -1 skateboard -2 manifold key

**black midrange — 6.5%, ~50 (thin data):**
* discard-proof-ish (forge/top-casting), bowmasters vs ring (same warning as dimir); sheoldred's edict eats fleshraker — fantasticar dodges (not a creature on their turn)
* in: +3 dismember; out: -1 crypt -1 skateboard -1 manifold key

**black saga storm — 6.5%, ~50 (thin data):**
* beseech storm race — chalice@1 hits dark ritual (mv1)!; crypt their yard; flute names beseech the mirror (+3 tax) or LED (activation lock)
* in: +4 flute; out: -1 skateboard -2 manifold key -1 forge

**death & taxes — 5.6%, 67.2% wr (n=109, BEST prior):**
* their plan: vial + taxes — but thalia taxes a deck of lands and rocks barely; revoker CAN name your keys/monolith/opal (their best card here)
* chalice@0 counters vial?? vial is mv0 — yes, chalice@0 on the play beats t1 vial; otherwise flute names aether vial (activation lock)
* fleshraker pings clear mother/esper sentinel squads; fantasticar + constructs fly over their board; karakas taxes animated fantasticar — sac-to-constructs ignores it
* in: +4 flute +3 dismember; out: -4 chalice (past t1 it's dead vs vial curve) -1 crypt -1 skateboard -1 manifold key

**doomsday — 5.6%, 40.4% wr (n=97, second-worst prior):**
* their plan: combo under your prison — dark ritual -> doomsday -> oracle, protected by fow/daze
* chalice@1 is your best card: ritual, brainstorm, ponder, flusterstorm all mv1; flute names doomsday itself (+3 tax on a {B}{B}{B} sorcery hurts)
* the dismember line: kill oracle IN RESPONSE to its trigger — devotion drops to 0 and the trigger fizzles (only works if their library isn't already empty; vs the standard 2-buffer pile it works)
* in: +3 dismember +4 flute; out: -1 crypt -1 skateboard -2 manifold key -1 voltaic key -1 mystic forge -1 the one ring
// forge mirror (online only, not a local deck): 50.0% n=106 pre-ban — whoever sticks forge + fleshraker first; dismember their fleshraker; note command can NOT exile the one ring (creatures only)

**eldrazi — 5.6%, 55.6% wr (n=185):**
* THEIR chalice is the real danger at X=0 — it hits your 13 zero-drops (petal/opal/bauble/crypt); @1 only clips keys; TKS strips — forge doesn't care much
* your ring out-values their whole deck; command exile: TKS at X=4 (smasher is mv5 and taxes targeting — usually just block it w/ constructs)
* in: +3 dismember; out: -2 manifold key -1 skateboard

**painter — 4.7%, 64.6% wr (n=162):**
* their REBs are DEAD — every spell here is colorless; grindstone does mill you out eventually (no oracle recovery) — don't ignore a lethal-mill clock, but their speed rarely gets there
* flute names grindstone (activation lock = combo off); dismember the servant (mv2)
* in: +4 flute +3 dismember; out: -2 chalice -1 crypt -1 skateboard -2 manifold key -1 mystic forge

**blue artifacts — 3.7%, 59.0% wr (n=103):**
* the engine mirror — yours is bigger (ring/forge vs emry/saga); kappa dodges nearly everything (mv6 + ward {4} — command needs X=6 PLUS the ward tax): race it in the air w/ constructs/fantasticar instead
* in: +4 grid (their counters) +3 dismember (emry); out: -4 chalice -1 crypt -1 skateboard -1 manifold key

**energy — 3.7%, 56.7% wr (n=7, speculative):**
* their go-wide lifegain vs your pings: fleshraker + spawn chains clear guide/ocelot boards; ring stabilizes; their clock is the whole question
* in: +3 dismember; out: -1 crypt -1 skateboard -1 manifold key

**esper midrange — 3.7%, ~50 (imputed):**
* discard + swords + counters: same shape as dimir/azorius — grid + dismember, ring carefully under bowmasters if they have it
* in: +4 grid +3 dismember; out: -4 chalice -1 crypt -1 skateboard -1 manifold key

---
---
**board logic recap (why these 15):**
* 4 defense grid — the blue plan: your engine resolves through fow when their counters cost +3 off-turn
* 4 disruptor flute — the named-card lock (flash): vial / sneak attack / grindstone / LED / teferi are all activated-ability or tax targets; boardable in half the field
* 3 dismember — the ONLY removal in the 75; black phyrexian: hand-cast only (never off forge, no fleshraker trigger), costs 2-6 life — budget it
* 4 leyline of the void — reanimator/dredge/hogaak; OPENER-ONLY tech: it's {2}{B}{B} (black) and this deck has no black mana — drawn later it is a dead card, NOT forge-castable; mulligan accordingly vs yard decks
* what this board does NOT have (vs the other post-ban shells): portable hole / engineered explosives (DethFrmAbove runs 4+3 — real spot removal), mindbreak trap (swifty 2) — if the field is grindier than expected, that's the first swap axis
* chalice is the most-boarded-OUT card: it's a weapon vs one-drop decks and a brick vs top-heavy ones — count their curve in g1

---
---
**references:**
* decklist: decks/mystic-forge-combo.txt (+ variant notes in header)
* the two challenge lists: univerce (this 75, 4-2) · DethFrmAbove (trinisphere/partial-tron, 6-2 3rd) — legacy challenge 32, 2026-07-01
* field + ranking context: decks/best-deck-best-call-ranking.html (mystic forge = the hot unmeasured marginal, 6.3% of post-ban field)
* prior primers (style + shared field notes): decks/doomsday-fantasticar-tempo-moxfield-primer.md

---
---

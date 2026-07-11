# Cephalid Breakfast, Stoneforge camp (Moxfield primer, Andrew's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/cephalid-breakfast-sfm.txt (SFM-camp consensus n=42, winner-validated board, 2026-07-06).

<!-- PASTE BELOW -->

---
---
:::notes:::
* build = consensus over the STONEFORGE camp of cephalid breakfast (mains sfm/kaldra — the two-style builds): n=42 of 136 regime decks, evolving tier; camp is unusually consensual (14 of 16 maindeck names at 100%) — modal counts assemble a clean 60/15, zero judgment swaps
* board = winner-validated (5-0/top8 subset n=11): consign/fon/needle 100%, surgical 91, fluster 91, stp 82, lantern 82, serenity 73, lavinia 55 (flex tail); dropped: hydroblast 29%, brazen 26%, ghost vacuum 27%
* wr numbers below are ARCHETYPE-level and nearly all SPECULATIVE tier (only 6% of breakfast's matchup cells are established) — treat as priors, not measurements; NO REPS YET on this list
* NOT a daze deck — the sfm camp plays esper control-combo, not tempo; your dimir instincts about daze windows don't transfer, your consign/fow/stack-war instincts do
* why this deck (floor analysis 2026-07-06): only archetype besides doomsday tempo that passes the two-complete-styles test w/ a high floor — worst semi-measured cell 45.2% vs dimir tempo (n=37, the one evolving-tier cell)
* acquisition vs binder: 48 cards / 25 names ≈ $1,422 = 2 tundra $557 + 1 usea $370 + ~$495 rest; blue core (bs/ponder/fow/tamiyo/consign/fon/surgical/needle) already owned; needs only ONE usea (dimir/doomsday gaps carry four)

---
**plan:**
* two decks in one, BOTH maindeck (unlike doomsday's post-board transform — the fair deck is already in g1):
  * kill mode: illusionist + nomads -> mill yourself out -> narcomoebas -> dread return -> thassa's oracle
  * fair mode: stoneblade — sfm -> kaldra t3, saga constructs, tamiyo card adv, stp/pe interaction
* mode select: vs removal-light (combo, big mana) = combo asap; vs removal-dense grind = lead stoneblade, combo when their interaction is tapped/spent; post-board vs yard hate = fair mode + serenity juke (they keep dead/dying hate)
* the combo (all grounded in oracle text):
  * nomads {0}: "the next 1 damage... is dealt to target creature you control instead" — TARGETS illusionist -> "becomes the target of a spell or ability" -> mill 3; repeat, free, INSTANT speed
  * shuko = backup enabler, equip {0} also targets — but "equip only as a sorcery"; nomads combos at eot/in response, shuko only on your main
  * library empty -> 3 narcomoebas ("put into your graveyard from your library, you may put it onto the battlefield") -> dread return flashback (sac 3 creatures) targeting oracle in yard -> devotion X >= library 0 = win // 0 >= 0 wins — devotion can be ZERO
  * cabal therapy flashback (sac a creature) strips their counter BEFORE the dread return; orim's chant = "target player can't cast spells this turn" (kicked: no attacks either) = combo in peace
* oracle is the ONLY kill card — if it's exiled (surgical/tks), you are a full stoneblade deck; that's a real game, not a concession
* what they do to you (know it from the dimir side): consign counters oracle's etb trigger AND narcomoeba triggers; grafdigger's cage is a HARD lock (narcomoeba = creature from library, dread return = creature from yard + flashback cast from yard — all three lines dead) -> counter the cage on the way in (colorless cast = consign-able, noncreature = fon-able), or serenity it away after
* bowmasters does NOT trigger off illusionist mills (draws only) — tamiyo/brainstorm draws do; sequence mills freely vs dimir
* their grindstone milling you is LIVE FOR YOU — narcos enter, dr+oracle land in yard, untap and win unless they exile the yard
* saga is both modes in one card: II constructs = fair wincon; III fetches shuko ({1}) — PUT onto battlefield, not cast -> dodges chalice@1

**mulligans:**
* snap keeps: illusionist + nomads/shuko + protection or cantrip; sfm + saga + interaction (fair skeleton)
* good keeps: tamiyo + stp + lands + a cantrip — fair-mode hand, the combo assembles off cantrips
* pitch: all-interaction no-plan; one-body hands vs bolt decks w/o protection (both combo creatures die to everything)
* count blue cards for fow before keeping
* kill-turn mana ≈ ZERO once both bodies stick — nomads {0}, dr flashback = "sacrifice three creatures" (no mana), oracle enters off dr; the keep question is bodies + protection, not mana

---
---
**interaction targets — what you save it for:**
* fow/fon: the cage/hate cast on your combo turn, or their gameplan card in fair mode — pick a job per game; fon pitch k_min: board brings 3, blue density is fine
* consign (3 post-board): cage/chalice CASTS (colorless), chalice's counter-trigger, saga chapters, eldrazi casts, their beanstalk triggers, THEIR oracle trigger in combo pseudo-mirrors
* flusterstorm: the stack war on your kill turn (instants/sorceries only)
* orim's chant: their upkeep before your combo turn, or your own turn pre-combo — spells off; kicked vs aggro = fog
* stp/pe: bodies that name/block your pieces — revoker-class (names nomads: shuko is the second enabler, they rarely stop both), thalia, bowmasters; pe converge caps at 3 colors here = mv<=3
* pithing needle: grindstone ({3},{T} activated), their equip/vial-class activateds; USELESS vs cage (static ability)
* soul-guide lantern/surgical: their yard (reanimator/doomsday piles); surgical their oracle/dr in combo mirrors
* serenity: the juke — "destroy all artifacts and enchantments" at YOUR upkeep sweeps their cage/leyline; kaldra is indestructible and survives your own serenity; time it AFTER their hate lands, accept losing shuko/saga on board
* lavinia: their FREE spells are countered ("if no mana was spent... counter") = pitch-fow/fon/daze all die; binding stays mv6 (domain reduces COST not mv) — locked until they hit 6 lands

---
---
**matchups & sideboard** // boulder field, archetype-level wr, nearly all speculative = priors // no reps — in/out plans are mechanics-derived judgment, tune at the table

**izzet delver — 11.2% of field, 48.8% wr (n=25, spec):**
* their plan: bolt your combo creatures + counter war; every bolt aimed at illusionist is one off your face
* combo at instant speed via nomads eot when their mana taps; fair mode is real — kaldra outclasses their whole board
* in: +2 stp +1 fluster
* out: -1 orim's chant -1 cabal therapy -1 narcomoeba

**show and tell — 10.3%, 53.8% wr (n=25, spec):**
* their plan: cheat the fatty; you're the faster combo w/ counter backup
* interaction: fow/fon the s&t itself; consign their cast-triggers; your removal is dead vs what they put in
* in: +3 consign +3 force of negation
* out: -2 swords -2 prismatic ending -1 kaldra -1 cabal therapy

**white beanstalk — 7.5%, 34.1% wr (raw 0-7 — tiny n, shrink doing the work; treat as bad-lean unknown):**
* their plan: binding/swords on your creatures + beanstalk card adv; slow kill = your combo window is wide
* lavinia holds binding to honest mv6; consign their beanstalk triggers; combo through, don't grind their value engine
* in: +1 lavinia +1 fluster +2 force of negation
* out: -1 kaldra -1 orim's chant -1 narcomoeba -1 urza's saga

**dimir tempo — 7.5%, 45.2% wr (n=37, evolving — the best-measured cell; the deck you know from the other side):**
* their plan: your old plan — bowmasters, consign on your oracle/narco triggers, push your bodies, murktide clock
* mills don't feed their bowmasters; kill bowmasters before tamiyo draws; fair mode good — kaldra ignores push/bolt math
* in: +2 stp +1 fluster
* out: -1 orim's chant -1 cabal therapy -1 narcomoeba

**jeskai midrange — 7.5%, 55.3% wr (n=4 — ignore the number):**
* their plan: counters + swords/pe + phlage grind
* fair mode trades fine; combo when shields down; fon their sweepers/phlage
* in: +2 force of negation +1 fluster
* out: -1 orim's chant -1 cabal therapy -1 narcomoeba

**azorius midrange — 6.5%, ~47 (n=3, imputed):**
* counters + binding + slow clock; same shape as beanstalk w/ more bodies
* in: +1 lavinia +2 force of negation
* out: -1 orim's chant -1 cabal therapy -1 kaldra

**black midrange — 6.5%, no cell data (~50 prior):**
* their plan: discard strips the combo, bowmasters + grind; they can't strip a stoneblade board state
* lead fair, combo off the top later; therapy-proof your keep (two-plan hands)
* in: +2 stp
* out: -1 orim's chant -1 narcomoeba

**black saga storm — 6.5%, no cell data (~50 prior):**
* their plan: beseech storm race; you're slower g1 unless the nut — interaction backup decides
* fluster/consign in the stack war; lavinia taxes their free half; needle their saga? no — consign the chapters
* in: +1 fluster +1 lavinia +3 consign
* out: -2 swords -2 prismatic ending -1 kaldra

**death & taxes — 5.6%, 48.2% wr (n=13, spec):**
* their plan: thalia taxes your cantrips, revoker/mom protect, vial dodges your counters
* revoker names nomads -> shuko line (sorcery speed — plan the turn); stp thalia/revoker on sight; combo beats their fair game if bodies live
* in: +2 stp
* out: -1 orim's chant -1 narcomoeba

**doomsday — 5.6%, 47.0% wr (n=18, spec):**
* their plan: the mirror-adjacent race; their pile is slower but protected by thoughtseize/duress
* consign THEIR oracle trigger (you know this move); surgical their pile after a doomsday resolves; chant their kill turn = they halved their life for nothing
* in: +3 consign +2 surgical +1 fluster
* out: -2 swords -2 prismatic ending -1 kaldra -1 stoneforge mystic

**eldrazi — 5.6%, 37.5% wr (n=29, spec — worst semi-measured; respect it):**
* their plan: chalice@1 (bs/ponder/chant/therapy/nomads all die), tks strips oracle/dr, fast clock
* consign the chalice trigger AND their casts; saga III puts shuko in uncast; kaldra germ blocks their board honestly
* in: +3 consign +2 stp
* out: -1 orim's chant -1 cabal therapy -1 narcomoeba -1 tamiyo -1 ponder

**painter — 4.7%, ~45 (n=6, imputed):**
* their plan: painter names blue -> rebs kill your everything; grindstone mills you
* their grindstone is YOUR win button (narcos + dr + oracle in yard — win on untap unless yard exiled); needle grindstone anyway; race g1
* in: +1 needle +2 stp
* out: -1 orim's chant -1 cabal therapy -1 narcomoeba

**blue artifacts — 3.7%, 52.9% wr (n=20, spec):**
* their plan: saga constructs + colorless spell base + counter backup
* consign their colorless casts + saga chapters; serenity is a one-card board wipe here — their whole deck is artifacts, your kaldra survives
* in: +3 consign +1 serenity
* out: -2 prismatic ending -1 orim's chant -1 cabal therapy

**energy — 3.7%, ~50 (n=8, imputed):**
* their plan: fast wr aggro + guide lifegain; a clock race your combo doesn't care about
* combo asap — their interaction is thin; kicked chant = fog the alpha strike; stp guide on sight
* in: +2 stp
* out: -1 cabal therapy -1 narcomoeba

**esper midrange — 3.7%, 37.5% wr (raw 0-5 — tiny n, bad-lean unknown):**
* their plan: discard + counters + stoneblade-ish bodies — the grindiest seat in the room
* two-plan keeps; their surgical on oracle is the real threat -> fair mode wins those games; fon their fow in stack wars
* in: +2 force of negation +2 stp
* out: -1 orim's chant -1 cabal therapy -1 narcomoeba -1 shuko

---
---
**board logic recap (why these 15):**
* protection core (3 consign + 3 fon + 1 fluster): breakfast's board is ANTI-HATE, not a transform package — the second mode already lives maindeck (the sfm camp's structural difference vs doomsday's post-board goyf pivot); consign is the format-best answer to cage/chalice/triggers and winners run it 100%
* removal overflow (2 stp): every fair matchup wants 3-4 total
* yard axis (2 surgical + 1 lantern): combo mirrors + reanimator; surgical doubles as mirror-breaker
* the juke (1 serenity): sweeps their post-board hate while kaldra survives — the card that makes "board out combo" a trap for THEM
* 1-of tail (needle, lavinia): grindstone/activated hate; free-spell + binding lock
* dropped from camp consensus: hydroblast (29%), brazen (26%), ghost vacuum (27% of winners) — sub-consensus hedges the winners don't agree on
* every card winner-validated (n=11: consign/fon/needle 100%, surgical+fluster 91%, stp+lantern 82%, serenity 73%, lavinia 55%)

---
---
**references:**
* list: decks/cephalid-breakfast-sfm.txt (camp consensus method = same split discipline as the doomsday murktide camp)
* why this deck: floor/maximin analysis 2026-07-06 — highest-floor multi-modal archetype after doomsday tempo; floor cell 45.2% vs dimir tempo (n=37, evolving), everything else speculative
* data honesty: matchup cov30 = 6% — this deck is UNDER-MEASURED; the primer is mechanics + priors, reps will move numbers

---
---

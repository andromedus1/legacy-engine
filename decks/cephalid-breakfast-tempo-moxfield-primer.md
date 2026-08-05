# Cephalid Breakfast, tempo — Loki generation (Moxfield primer, the maintainer's list conventions)

Paste everything below the marker into the Moxfield deck description.
List = decks/cephalid-breakfast-tempo.txt (L4rss0n 6-2 Challenge 3rd 2026-07-18; winner-modal of the 12-deck July generation).

<!-- PASTE BELOW -->

---
---
:::notes:::
* build = the LIVE cephalid tempo generation: post-candelabra window (06-29→07-26) has 12 breakfast decks, ALL tempo (0 stoneforge — the sfm camp is dead this regime); loki is the july tech (0/11 may -> 11/12 july)
* this 75 = L4rss0n verbatim (challenge 3rd, 6-2) — it IS the winner-modal list: every count matches the mode of the 5 winning lists (two challenge 3rds + three league 5-0s); zero judgment swaps needed
* gen results: posted 28-27 (18-14 challenges incl two 3rd places, 10-13 at one rough paper open) + three league 5-0s (publication-biased, uncounted) — thin sample, treat as "live and competitive," not "proven"
* wr priors below are ARCHETYPE-level FULL-CORPUS cells (label FC) — they blend the nadu/teferi generations w/ this one; the engine's era window (post-entomb/nadu-ban 2025-11-10) only has 4 measured cells. priors, not measurements. NO REPS on this 75
* why this deck (agency page 2026-07-28): breakfast = #1 agency (40.5, cov 93, grounded) — fewest proven blowouts (2.5 of 58 measured) + lowest %-meta-that-blows-you-out (1.1%) on the page; nothing measured runs it over
* why loki: the deck was already a targeting engine — loki makes every first target each turn a free card (see plan). fair mode went from "saga or bust" to a real draw engine
* contested slots (all-12 histograms): loki 3x:5/4x:4 (winners 4x:3 — play 4, it's the engine); tamiyo 3x:4/4x:4 (4 here; the 4th is your first boarding trim); chant 1x:4/2x:4 (1 here); daze 5/12 (0 here — daze lives in the loki-less voice-of-victory shell, walewa's build); relic MAIN 5/12 (1 here, see plan)

---
**plan:**
* the combo (all grounded in oracle text):
  * nomads {0}: "the next 1 damage that would be dealt to this creature this turn is dealt to target creature you control instead" — TARGETS illusionist -> "whenever this creature becomes the target of a spell or ability, mill three cards" -> repeat free, INSTANT speed
  * shuko = second enabler: equip {0} also targets — but "equip only as a sorcery"; nomads combos at eot/in response, shuko only on your main
  * library empty -> narcomoebas ("when this card is put into your graveyard from your library, you may put it onto the battlefield") -> dread return flashback (sac 3 creatures) on oracle -> devotion X >= library 0 = win // X can be ZERO
  * cabal therapy flashback (sac a creature) strips their counter BEFORE dread return; orim's chant ("target player can't cast spells this turn") = combo in peace
* the loki engine (why this generation exists): "whenever a player or permanent becomes the target of an ability you control, draw a card. this ability triggers only once each turn"
  * every nomads {0} targets -> first activation each turn = free card. shuko equip targets. relic tap TARGETS A PLAYER (either player — works with empty yards). karakas tap targets
  * so: eot nomads-at-illusionist = mill 3 + draw 1, untap, do it again on your turn = 2 free cards/turn-cycle at zero mana while you assemble
  * loki is {1}{U} = +1 blue devotion for oracle, and a 2-drop body that blocks
* tamiyo: attack -> investigate (clue = artifact, sac 2 to draw); loki draws + clue draws flip her fast; flipped tamiyo = the fair-mode engine
* surveil lands (archive/sewers): "when this land enters, surveil 1" — a surveiled narcomoeba TRIGGERS (mill from library ✓); dumps therapy/dread-return where they want to be. they enter TAPPED — sequence them t1 or on idle turns
* relic main: half the field plays out of the yard (doomsday 7.3 + grixis rean 3.5 + dimir goyfs 15.5 field-wide); "{T}: target player exiles a card from their graveyard" = repeatable hate that ALSO pings loki every turn (target them, or yourself w/ empty yard just for the draw)
* oracle is the ONLY kill card — exiled (surgical/tks) = you're a fair tempo deck w/ saga constructs + flipped tamiyo + loki cards; that's a real game, not a concession
* what they do to you: consign counters oracle's etb trigger AND narcomoeba triggers; grafdigger's cage = HARD lock ("creature cards in graveyards and libraries can't enter the battlefield. players can't cast spells from graveyards or libraries" — narco, dread return cast, AND the reanimated oracle all dead) -> answer the cage ON THE STACK (colorless cast = consign, noncreature = fon) or exile it after (pe: cast {1}{W} w/ 2 colors of mana handles mv1)
* bowmasters does NOT trigger off illusionist mills (draws only) — but loki/tamiyo/clue draws DO; vs dimir, mill freely, draw carefully
* saga: II constructs = fair wincon; III fetches shuko or relic ({0}/{1}, PUT not cast — dodges chalice@1)

**mulligans:**
* snap keeps: illusionist + nomads/shuko + protection or cantrip; loki + saga + interaction (fair skeleton that draws into combo)
* good keeps: tamiyo/loki + lands + cantrips — the fair hand; combo assembles off the engine
* pitch: all-interaction no-plan; one-body no-protection vs bolt decks (illusionist dies to everything)
* count blue cards for fow before keeping; 28 blue in the 60 — nomads/chant/stp/therapy/relic don't pitch
* kill-turn mana ≈ ZERO once bodies stick (nomads {0}, dr flashback = sac, oracle off dr) — keeps are about bodies + protection, not mana

---
---
**interaction targets — what you save it for:**
* fow/fon: the cage/hate on your combo turn, or their gameplan card in fair mode — one job per game; fon: "if it's not your turn... exile a blue card" = counter their eot/upkeep plays free, exiles what it counters (kills flashback/recursion targets)
* consign (2 post-board): cage/chalice CASTS (colorless), THEIR consign can't be consigned (blue spell) but their oracle/narco/storm TRIGGERS can; saga chapters; eldrazi/forge casts
* flusterstorm: the stack war on your kill turn (instants/sorceries only; storm copies beat their fluster)
* orim's chant: their upkeep before your kill turn, or your own turn pre-combo; kicked = fog
* stp/pe: revoker-class (names nomads — shuko is enabler #2, they rarely stop both), thalia, bowmasters; pe converge = colors of mana SPENT, our three colors (w/u/b) cap it at mv≤3
* pithing needle: "activated abilities of sources with the chosen name can't be activated unless they're mana abilities" — grindstone, vial, thespian's stage, equipment; USELESS vs cage (static)
* lavinia: "whenever an opponent casts a spell, if no mana was spent to cast it, counter that spell" = pitch-fow/fon/daze all die; + "can't cast noncreature spells with mana value greater than the number of lands" = doomsday (mv3) dead on their 2 lands, beseech (mv4) dead on 3
* hydroblast: counter OR destroy red — bolt on your illusionist, blood moon, red stompy permanents
* karakas: bounce THEIR legend (griselbrand, marit lage token — it's legendary, bounce = token dies) or SAVE your tamiyo/loki from removal; every activation pings loki

---
---
**matchups & sideboard** // current field (post-candelabra shares), FC priors — cross-generation blends, tune at the table // in/out counts balance; combo core (4 illusionist, 4 nomads, 2 shuko, 3 narco, dr, oracle) never trimmed unless named

**dimir tempo — 8.8% of field, ~47 prior (n=191 FC, CI 39-53):**
* their plan: bowmasters + push/snuff on your bodies, consign on your oracle/narco triggers, goyf clock; you know this seat
* mills don't feed bowmasters — draws do: sequence loki/tamiyo triggers when bowmasters is off the table or you can pay the squirrel tax; kill bowmasters on sight
* relic is LIVE here (barrowgoyf/nethergoyf are yard cards)
* in: +2 stp +1 fluster
* out: -1 orim's chant -1 karakas -1 tamiyo

**azorius midrange — 7.7%, ~48 prior (n=31 FC, CI 29-62 — wide; july azorius is the new stifle/consign build, treat prior as stale):**
* their plan: stifle/consign trigger-denial (both hit your oracle trigger + narco triggers), phelia/riddler bodies, daze/fow
* this is the matchup that reshaped doomsday — assume it's aimed at you too; fight the stack war with fluster/fon, combo when their mana taps out, fair mode through karakas + saga
* lavinia turns off their free counters (daze/pitch-fon die)
* in: +2 lavinia +1 fluster +1 fon
* out: -1 orim's chant -1 cabal therapy -1 relic -1 tamiyo

**blue artifacts — 7.3%, ~49 prior (n=78 FC, CI 38-60):**
* their plan: chalice (your 1-drops die: nomads/therapy/chant/needle), saga constructs, thoughtcast card adv, welder recursion
* consign the chalice cast (colorless ✓) + their colorless casts generally; stp welder/memory guardian; saga III fetches around chalice@1 (PUT not cast)
* in: +2 consign +2 pe +1 fon
* out: -1 orim's chant -1 cabal therapy -1 relic -2 loki // pe cast w/ 2+ colors exiles chalice/cage

**doomsday — 7.3%, ~54 prior (n=102 FC, CI 44-63):**
* their plan: the adjacent race; thoughtseize/duress strip, then pile + oracle — but their kill needs mana and a turn window, yours is instant-speed
* consign THEIR oracle trigger (you know this move from the dimir seat); relic their yard (ritual threshold/flow state fuel); chant their pile turn = they halved their life for nothing; fluster the stack war
* in: +2 consign +1 fluster +1 lavinia (their doomsday mv3 > their lands early)
* out: -2 stp -1 karakas -1 tamiyo

**dimir midrange — 6.7%, ~46 prior (n=29 FC, CI 25-59 — wide):**
* their plan: discard + bowmasters + goyf grind; slower than dimir tempo, more hand attack
* two-plan keeps beat therapy/seize; loki out-grinds them if the combo gets stripped; relic eats their goyf fuel
* in: +2 stp +1 fon
* out: -1 orim's chant -1 cabal therapy -1 narcomoeba // 3rd narco flex vs discard decks — they strip the combo anyway, the body count matters less

**energy — 6.3%, ~53 prior (n=38 FC, CI 37-68):**
* their plan: guide-of-souls life + static prison on your bodies + fast fair clock; folds to combo speed (their interaction is prison-shaped, not stack-shaped)
* combo asap — they beat your fair mode, not your combo; pe their static prison (mv1-2)
* in: +2 pe +2 stp
* out: -1 relic -1 karakas -1 orim's chant -1 tamiyo

**show and tell — 5.3%, ~64 prior (n=151 FC, CI 57-72 — your best measured matchup):**
* their plan: cheat a fatty; you're faster with counter backup, and their removal is nearly blank vs you
* fow/fon the s&t itself; karakas bounces griselbrand/legendary fatties; your stp is dead
* in: +3 fon +1 fluster
* out: -2 stp -1 relic -1 cabal therapy

**izzet delver — 4.2%, ~51 prior (n=102 FC, CI 41-60):**
* their plan: bolt your combo bodies + daze/fluster war + murktide clock; every bolt at illusionist is one off your face
* combo at instant speed via nomads when their mana taps; hydroblast = bolt insurance AND kills murktide (red)
* in: +2 stp +1 hydroblast +1 fluster
* out: -1 orim's chant -1 cabal therapy -1 relic -1 tamiyo

**grixis reanimator — 3.5%, ~49 prior (n=22 FC, CI 26-66 — wide):**
* their plan: entomb-less reanimator (looting/unearth shells) + discard; a yard race you're favored to win at instant speed
* relic main is your best card — exile their target at upkeep; fon their animate/reanimate (noncreature ✓, exiles it); their cage/vacuum hurts you back — keep pe/consign answers
* in: +3 fon +1 consign
* out: -2 stp -1 orim's chant -1 tamiyo

**lands — 3.2%, ~54 prior (n=104 FC, CI 44-63):**
* their plan: loam grind + port/wasteland mana denial + marit lage; NO stack interaction g1 — combo in peace, just beat sphere effects
* karakas KILLS marit lage (legendary token, bounce = gone); needle names thespian's stage; chant their key turn; keep basics vs wasteland
* in: +2 needle +1 pe +1 fon
* out: -2 stp -1 cabal therapy -1 loki

**mystic forge combo — 2.7%, ~49 prior (n=163 FC, CI 41-56):**
* their plan: forge + top-of-library engine, chalice in the shell, grindstone kills; a race with colliding hate
* consign = house (forge cast, chalice cast, ALL their colorless casts + "{T}, pay 1 life: exile the top card" is activated — needle names forge); their grindstone milling YOU is live FOR you (narcos enter, dr+oracle in yard)
* in: +2 consign +2 needle +1 fon
* out: -2 stp -1 orim's chant -1 relic -1 tamiyo

**death & taxes — 2.6%, ~56 prior (n=13 era, CI 22-72 — tiny, ignore the point estimate):**
* their plan: thalia taxes, revoker names nomads, mom protects, vial dodges counters, flickerwisp messes your saga
* shuko line beats revoker (plan the sorcery-speed turn); stp thalia/revoker on sight; karakas their legends? no — bounce YOUR tamiyo from mom-fight removal instead
* in: +2 stp +2 pe
* out: -1 orim's chant -1 cabal therapy -1 relic -1 loki

**tes — 1.9%, ~57 prior (n=57 FC, CI 45-70):**
* their plan: ritual storm into beseech/tendrils, faster than you by a turn on the draw — interaction decides
* consign the STORM TRIGGER (triggered ability ✓ — copies never happen); lavinia = beseech mv4 dead on 3 lands + free-spell line off; fluster their kill turn; chant their upkeep
* in: +2 consign +2 lavinia +1 fluster
* out: -2 stp -1 relic -1 karakas -1 tamiyo

**tron / eldrazi / red stompy (colorless-prison block, ~4% combined; tron cell n=2 — no data, mechanics-derived):**
* their plan: chalice@1 + big colorless threats (tks strips oracle/dr from hand) + fast clock
* consign their casts + chalice; saga III fetches shuko/relic under chalice; hydroblast vs red stompy's moon/bolt suite (moon hurts — you keep basics + karakas is colorless-usable? no: karakas taps for {W} — fetch basics EARLY vs moon)
* in: +2 consign +2 pe +1 hydroblast (stompy only)
* out: -2 stp -1 chant -1 relic -1 loki (stompy: also -1 tamiyo for the hydro)

**cephalid mirror — 0.7%:**
* the relic war: first resolved yard-hate piece usually decides; consign their oracle trigger; surgical isn't in this board — respect theirs
* in: +2 consign +1 fluster
* out: -1 karakas -1 orim's chant -1 tamiyo

---
---
**board logic recap:**
* 3 fon = the flexible wall: s&t, reanimator, artifact hate on the stack, sweepers
* 2 consign = cage/chalice casts + every big trigger in the format (their oracle, storm, forge)
* 2 lavinia = the free-spell police (tes, azorius/izzet pitch-counters); dies to bolt — board it where their removal is thin or spent
* 2 needle = activated-ability lock (grindstone, stage, vial, equipment)
* 2 pe = the catch-all exile for mv≤2 permanents (cage, chalice, static prison, revoker)
* 2 stp = fair-matchup removal top-up (dimir/d&t/energy)
* 1 fluster + 1 hydroblast = stack war + red insurance
* known gap: NO surgical/serenity — cage answers are stack-side (consign/fon) + pe after; if your local field is cage-heavy, the named swap is -1 lavinia -1 needle +1 serenity +1 surgical (paired swaps, tune to field)

**references:**
* list: L4rss0n, Legacy Challenge 32 2026-07-18, 6-2 (3rd)
* gen sample: 12 decks 06-29→07-26 (challenges 18-14 w/ two 3rds; one paper open 10-13; three league 5-0s uncounted-biased)
* priors: legacy-engine agency page 2026-07-28 (corpus 67,426 decks / 66,086 decisive matches; breakfast row: agency 40.5 #1, cov 93%, floor 40.5 vs mardu stompy n=27 FC)
* oracle text grounded via cards.oracle_text (legacy.duckdb, scryfall mirror)

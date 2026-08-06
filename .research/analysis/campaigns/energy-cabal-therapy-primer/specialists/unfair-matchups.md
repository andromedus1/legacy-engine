---
description: Unfair-matchup specialist report for the Energy Cabal Therapy primer
type: research
summary: Exact-75 plans for current combo, graveyard, Lands, prison, and artifact strategies.
updated: 2026-08-03
decisions:
  - Board to the opposing engine actually observed, especially for hybrid Aluren and broad Blue Artifacts labels.
  - Preserve a real clock while adding narrow hate; the deck cannot win by locking alone.
  - Treat Therapy names and exact swaps as matchup synthesis rather than copied pilot authority.
key_findings:
  - Null Rod and Clarion Conqueror overlap against activated artifact engines but not triggered or static abilities.
  - Leyline plus Priest covers Reanimator's graveyard plan and its current non-graveyard sideboard pivot.
  - Dredge labeling in the corpus requires card-level verification before matchup advice is attached.
---

# Unfair-matchup report: Energy Cabal Therapy

## Evidence boundary

The current preparation set includes Tron, Show and Tell, Doomsday, Blue Artifacts, Grixis
Reanimator, Lands, TES, Eldrazi, Mystic Forge, Aluren, Golgari Landfall, Dredge, Painter, and Oops
among the project's top 24 [ecp-current-corpus]{2}. Their current configurations are attested from
published July lists [ecp-unfair-current-lists]{1} [ecp-unfair-current-lists]{2}
[ecp-unfair-current-lists]{3} [ecp-unfair-current-lists]{4} [ecp-unfair-current-lists]{5}
[ecp-unfair-current-lists]{6} [ecp-unfair-current-lists]{7} [ecp-unfair-current-lists]{8}.

Every swap below is `{inferred: adapted}` from those configurations, the registered 75, and Oracle
interactions. It is not presented as published sideboard authority. Each baseline exchange sums
evenly and returns a legal 60. “Current list” means the attested representative, not every build
under the label. The registered sideboard is four Leyline, three Silence, and two each of Priest,
Null Rod, Conqueror, and Surgical [ecp-exact-75]{1}.

## Shared rules against unfair decks

- **Role:** become disruptive aggro. A hate permanent without a two- or three-turn clock gives the
  opponent time to draw an answer; a fast creature hand without interaction loses the race. Keep
  hands that combine pressure with discard or a sideboard axis.
- **Discard:** Thoughtseize before Therapy when possible. After seeing the hand, take the card that
  beats the hate already available, then flash Therapy back only when it strips a duplicate,
  enables Ajani, or converts a soon-to-be-irrelevant token into a full card. Therapy chooses a
  nonland name, so attack land engines with Wasteland/Surgical rather than illegal land calls
  [ecp-scryfall-oracle]{1}.
- **Hate sequencing:** lead Leyline from the opener; hold Surgical until it removes a load-bearing
  set, unless spending it early is required to survive. Cast Null Rod before the artifact engine
  can activate. Clarion Conqueror also shuts our Guide and transformed Ajani activations, whereas
  Null Rod does not [ecp-scryfall-oracle]{4}. Sequence energy spending and planeswalker value first
  when feasible.
- **Priest precision:** Containment Priest stops nontoken creatures that enter without being cast,
  including reanimation and Show and Tell entries, but it does not stop an Aluren creature because
  Aluren casts it. Priest must already be on the battlefield before Show and Tell resolves; putting
  it in from that same Show and Tell does not make it a pre-existing replacement effect.
  [ecp-unfair-oracle]{2} [ecp-unfair-oracle]{5}
- **Silence precision:** Deafening Silence constrains cantrip-plus-combo and ritual/tutor chains. It
  does not stop a noncreature spell followed by a creature, nor an Acererak loop consisting of cast
  creature spells [ecp-unfair-oracle]{3}.

## 1. Tron

**Their plan.** Planar Nexus counts as Mine, Power-Plant, and Tower, letting the deck power out
Kozilek's Command, The One Ring, Karn, and Ugin while Forces and Stock Up bridge the blue game
[ecp-unfair-current-lists]{1}. Nexus's all-land-types text explains why a single Nexus amplifies the
traditional pieces [ecp-unfair-oracle]{4}.

**Our role and counter-plan.** Race as disruptive aggro. Wasteland Nexus first when that breaks the
mana jump; otherwise hit the missing Tron piece. Null Rod disables Ring draw, Monolith, and Map;
Conqueror adds Karn loyalty abilities to that lock, although neither turns off Command or the
static/card-casting portions of their engine [ecp-unfair-oracle]{1}. Resolve Squelcher before the
threat wave when their Forces matter, and do not spend discard on a redundant mana piece if Stock
Up, Command, Ring, or Karn is the actual stabilizer.

**Mulligan shift.** Keep a colored one-drop plus Wasteland/discard or a castable artifact hoser.
Ship removal-heavy hands and hands whose only mana is Wasteland. A turn-two Null Rod with no clock
is marginal; a turn-two Rod behind Guide/Ocelot is strong.

**Therapy names.** Blind **Kozilek's Command** when the board is developing, **Stock Up** when their
mana is constrained, or **Force of Will** before the lock piece. After a Ring or Karn tutor line is
telegraphed, name the known payoff.

**Board:** **+2 Null Rod, +2 Clarion Conqueror; -4 Swords to Plowshares.** On the draw against a
Thundertrap-heavy build, retain two Swords and cut **-2 Cabal Therapy, -2 Swords** instead. Do not
bring Surgical by default: extracting one Tron land after Wasteland is attractive, but Nexus and
the remaining mana engines make that exchange unreliable.

## 2. Show and Tell / Omni-Tell

**Their plan.** Use Tomb plus cantrips/Stock Up and discard/Force to resolve Show and Tell for
Omniscience, Atraxa, or Emrakul. The current Dimir representative can pivot after boarding into
Barrowgoyf and Bowmasters [ecp-unfair-current-lists]{1}.

**Our role and counter-plan.** Game one, discard **Show and Tell**, keep Karakas untapped for Atraxa
or Emrakul, and present lethal quickly. After boarding, Silence breaks cantrip-then-Show turns and
Priest already in play exiles a creature put in by Show and Tell; neither answers Omniscience, so
discard still targets the enabling sorcery or enchantment [ecp-unfair-oracle]{2}
[ecp-unfair-oracle]{3}. Voice is excellent because it denies their interaction during our lethal
turn.

**Mulligan shift.** Require discard, Silence, Priest, or a truly fast Karakas-backed clock. Ship
fair-value sevens with no turn-one disruption. Do not keep Priest as the sole answer without mana
to flash it before Show and Tell.

**Therapy names.** Blind **Show and Tell**. If they already have it covered by discard information,
name **Force of Will**, **Omniscience**, or the known sideboard threat. Never spend the blind name on
one of several interchangeable creatures while Show and Tell remains live.

**Board:** **+3 Deafening Silence, +2 Containment Priest; -4 Swords to Plowshares, -1 Goblin
Bombardment.** If game two reveals four Barrowgoyf plus Bowmasters, return **+2 Swords; -1 Therapy,
-1 Amped Raptor** for game three while keeping all five hate cards.

## 3. Doomsday

**Their plan.** Resolve Doomsday behind discard, Daze, and Force, reduce the deck to a chosen five,
then draw into an Oracle win with Baubles, Street Wraith, Edge, or cantrips [ecp-unfair-current-lists]{2}
[ecp-unfair-oracle]{5}. The current sideboard can become a Barrowgoyf/Murktide/Bowmasters tempo deck.

**Our role and counter-plan.** Attack hand, mana, and draw access while ending the game. Silence
prevents the common cantrip-then-Doomsday or Ritual-then-Doomsday turn. Null Rod disables LED and
Bauble activations, forcing a less flexible pile. Surgical is best paired with discard on Doomsday;
after a resolved Doomsday it may be too late if they retain an immediate draw effect.

**Mulligan shift.** Keep pressure plus two distinct disruptions. A one-drop + Thoughtseize +
Silence/Rod is ideal. Ship Swords-heavy and slow Ajani-only hands. Post-board, respect their creature
pivot: a hate-only hand with no clock still loses to Barrowgoyf.

**Therapy names.** Blind **Doomsday**; name **Force of Will** or **Daze** immediately before a hate
piece, and **Dark Ritual** only when their hand is clearly speed-dependent. After Doomsday resolves,
name the known draw effect only if discard information establishes it.

**Board:** **+3 Deafening Silence, +2 Null Rod, +2 Surgical Extraction; -4 Swords to Plowshares,
-2 Goblin Bombardment, -1 Ajani.** If the full creature pivot appears, return **+2 Swords; -2
Surgical** for game three.

## 4. Blue Artifacts / Affinity

**Their plan.** Empty cheap artifacts to turn on Opal, Emry, Thoughtcast, and large synergy threats;
Saga and recursive baubles sustain the game, while Force protects the engine
[ecp-unfair-current-lists]{3}.

**Our role and counter-plan.** Land an activated-ability lock, then kill their creatures before the
static/triggered portion wins anyway. Null Rod switches off Opal, baubles, Saga's token activation,
and Emry; Conqueror covers the same activations. Neither stops Thoughtcast, Force, artifact cost
reduction, Pinnacle Emissary, Patchwork triggers, or Kappa's combat text [ecp-unfair-oracle]{1}.
Preserve Swords for Kappa/Automaton/Emissary and Wasteland for Saga or Seat when it constrains metalcraft.

**Mulligan shift.** Keep a fast white start plus Swords/discard or a turn-two Rod. Ship hands that
only interact on turn three. On the draw, a discard spell is much better than speculative Therapy
because their hand can empty immediately.

**Therapy names.** Blind **Force of Will** before Rod, **Emry** when holding Swords for the large
threat, or the threat revealed by Thoughtseize. Once they have emptied artifacts, do not name a
generic zero-mana card hoping to hit.

**Board:** **+2 Null Rod, +2 Clarion Conqueror; -3 Voice of Victory, -1 Cabal Therapy.** On the play
against a Force-heavy build, cut the second Therapy rather than the third Voice. Against a nonblue
Saga swarm with little instant interaction, the baseline Voice cut is preferred.

## 5. Grixis Reanimator

**Their plan.** Free discard clears a turn-one reanimation line; Looting supplies the graveyard,
and twelve reanimation spells return Atraxa, Griselbrand, or Archon. The current sideboard's four
Show and Tell plus four Stronghold Gambit explicitly pivots around graveyard hate
[ecp-unfair-current-lists]{4}.

**Our role and counter-plan.** Mulligan aggressively to Leyline, then protect it with discard and
clock them. Surgical backs Leyline or extracts the target in response to reanimation. Priest covers
both reanimation and the non-graveyard entry pivot; Karakas covers legendary Atraxa/Griselbrand but
not Archon. Swords remains insurance against a creature that enters after stripping Priest, though
Griselbrand may draw before Swords resolves.

**Mulligan shift.** A Leyline six with a colored source and creature is better than a strong fair
seven. Without Leyline, require Thoughtseize/Therapy plus Surgical or Priest. Do not keep a slow
Swords-only hand. Because Unmask/Thoughtseize attack the backup, redundant hate is valuable.

**Therapy names.** Blind **Unmask** when protecting Leyline plus backup; otherwise **Reanimate** or
**Animate Dead** according to the card put in the graveyard. Informed names prioritize **Show and
Tell** or **Stronghold Gambit** once the pivot is seen.

**Board:** **+4 Leyline of the Void, +2 Surgical Extraction, +2 Containment Priest; -3 Voice of
Victory, -3 Amped Raptor, -2 Goblin Bombardment.** Keep all four Swords because the attested pivot
can bypass Leyline. On the play against a list confirmed to have no alternative-entry sideboard,
cut **-4 Swords, -3 Voice, -1 Bombardment** instead.

## 6. Lands

**Their plan.** Exploration/Mox accelerates Loam and utility lands; Sphere taxes spells;
Stage/Depths creates Marit Lage; Saga, Maze, Tabernacle, Wasteland, Boseiju, and Crop Rotation make
the battlefield itself the control engine [ecp-unfair-current-lists]{5}. Loam recurs up to three
lands and Stage can copy Depths [ecp-unfair-oracle]{4}.

**Our role and counter-plan.** Pressure while shutting off recursion. Leyline turns off Loam;
Surgical can remove Loam or a combo land after discard/Wasteland; Null Rod disables Mox, Map,
Needle, and Saga's activated token ability. Save Wasteland for Stage/Depths unless a mana-denial
window is decisive. Keep Karakas ready for Marit Lage and deploy only enough bodies to pay
Tabernacle.

**Mulligan shift.** Keep Leyline plus colored mana and a threat; ship Leyline-only hands that cannot
play Magic through Sphere/Wasteland. Surgical plus Wasteland/discard and a clock is a valid
non-Leyline keep.

**Therapy names.** **Crop Rotation** first, **Exploration** when speed is the threat, **Sphere of
Resistance** against a one-drop-heavy hand, and **Life from the Loam** only when Leyline is absent.

**Board:** **+4 Leyline of the Void, +2 Surgical Extraction, +2 Null Rod; -4 Swords to Plowshares,
-3 Orcish Bowmasters, -1 Voice of Victory.** On the draw against four Sphere, cut **-1
Thoughtseize** instead of the boarded-out Voice. This matches the fair-matchup branch's independently
derived baseline.

## 7. TES

**Their plan.** Chain artifact mana and Ritual into Gamble/Beseech/Burning Wish; Echo and Gaea's
Will rebuild resources, and Tendrils ends the chain. The current main deck contains sixteen
zero-mana activated artifacts and brings Thoughtseize after boarding [ecp-unfair-current-lists]{2}.

**Our role and counter-plan.** Discard the tutor or engine, land Silence or Rod, then kill quickly.
Silence prevents multi-spell noncreature chains; Rod shuts LED, Petal, Chrome Mox, and Mox Opal
activations [ecp-unfair-oracle]{1} [ecp-unfair-oracle]{3}. Surgical converts discard into permanent
tutor/engine removal. Wasteland the land that strands their remaining colored requirement, not an
automatic turn-one target.

**Mulligan shift.** Require turn-one discard or a turn-two hate piece backed by a one-drop. On the
draw, a hand with only a turn-two Rod is too slow. Ship Swords and Bombardment hands regardless of
their fair-game quality.

**Therapy names.** Blind **Gamble** or **Burning Wish**; use **Beseech the Mirror** when their mana
already supports bargain, and **Thoughtseize** when protecting a known hate permanent after board.
Name the duplicated tutor seen by Thoughtseize rather than Ritual by rote.

**Board:** **+3 Deafening Silence, +2 Null Rod, +2 Surgical Extraction; -4 Swords to Plowshares,
-2 Goblin Bombardment, -1 Ajani.** If Echo/Gaea's Will proves central and they show answers to Rod,
**+4 Leyline; -2 Surgical, -2 Amped Raptor** is a contingent game-three pivot, not the baseline.

## 8. Eldrazi

**Their plan.** Sol lands, Temple, and Petal deploy Thought-Knot, Fleshraker, Command, Linebreaker,
and Smasher ahead of curve. The current representative boards Chalice rather than starting it
[ecp-unfair-current-lists]{5}.

**Our role and counter-plan.** This is a creature race, not a matchup for narrow artifact hate.
Swords Thought-Knot, Linebreaker, or the creature making combat impossible; Wasteland Temple/Tomb
only when it buys a full turn. Go wide around their large bodies, and use Bombardment/Ajani to turn
blocked tokens into reach. Null Rod stops Petal or Hearse but not Fleshraker's triggered abilities;
Conqueror likewise misses those triggers [ecp-unfair-oracle]{1}.

**Mulligan shift.** Require white mana, an early creature, and Swords or a fast token engine. Ship
discard-only hands. Post-board, preserve hands that can cast through Chalice on one by using
two-drops and Bombardment.

**Therapy names.** Blind **Kozilek's Command**; name **Thought-Knot Seer** when their mana points to
four, **Chalice of the Void** after seeing the sideboard pattern, or the duplicated threat revealed
by Thoughtseize.

**Board:** **no mandatory change.** If Disruptor Flute, Hearse, and additional activated artifacts
are all observed, **+2 Null Rod; -2 Cabal Therapy** is defensible. Do not bring Conqueror merely for
those cards; three mana is too slow and it suppresses our own Guide/Ajani activations.

## 9. Mystic Forge Combo

**Their plan.** Tomb/City, Monolith, Petal, and Opal accelerate Ring/Forge; Keys untap mana or Ring;
Forge chains colorless spells, while Fleshraker converts the chain into bodies and damage. The
current list also starts four Chalice and four Saga [ecp-unfair-current-lists]{3}.

**Our role and counter-plan.** Resolve Rod before the first engine activation, then remove
Fleshraker and race the static top-of-library casting engine. Rod/Conqueror disable Monolith, Keys,
Ring draw, Forge's exile activation, Saga's token activation, and Tezzeret loyalty abilities, but
they do **not** disable Forge's permission to cast from the top or Fleshraker triggers
[ecp-unfair-oracle]{1}. Wasteland Saga/City and discard Forge/Ring according to which half remains.

**Mulligan shift.** Look for turn-one discard into turn-two Rod, or a white one-drop plus Swords and
Wasteland. A Conqueror-only hand on the draw is too slow. Account for Chalice: a Raptor/Voice/Squelcher
curve is better than seven one-mana spells.

**Therapy names.** Blind **The One Ring** or **Mystic Forge**; name **Chalice of the Void** when your
hand is one-mana dense, and **Kozilek's Command** when the board is vulnerable.

**Board:** **+2 Null Rod, +2 Clarion Conqueror; -3 Voice of Victory, -1 Cabal Therapy.** Swords stays
for Fleshraker. On the draw, where Conqueror may miss the first engine turn, use **+2 Null Rod;
-2 Therapy** only and preserve creature density.

## 10. Aluren / Aluren–Show and Tell hybrid

**Their plan.** The current representative is not pure Aluren: it combines Aluren/Acererak with
Show and Tell, Atraxa, Omniscience, and Emrakul under Force, Veil, cantrips, and Stock Up
[ecp-unfair-current-lists]{6}. Aluren casts Acererak for free and at instant speed; it does not put
it directly onto the battlefield [ecp-unfair-oracle]{5}.

**Our role and counter-plan.** Discard the enabler matching their hand. Silence delays cantrip-then-
Aluren/Show and Tell but does not stop the creature loop after Aluren resolves. Priest covers the
Show and Tell creature branch only and must be cast first. Karakas can return Acererak, Atraxa, or
Emrakul, and Swords can interrupt Acererak while its enter trigger is pending; neither answers
Omniscience. Bowmasters punishes their heavy draw suite, so keep it.

**Mulligan shift.** Require discard/Silence plus a clock; Karakas upgrades a borderline hand.
Against the known hybrid, Priest is a keepable second axis but not a complete answer. Ship hands
whose plan is only creature removal.

**Therapy names.** Blind **Aluren** against the pure shell and **Show and Tell** against the current
hybrid; after a cantrip, use the enabler or protection revealed by the line. Name **Force of Will**
or **Veil of Summer** immediately before committing hate.

**Board against the current hybrid:** **+3 Deafening Silence, +2 Containment Priest; -3 Amped
Raptor, -2 Goblin Bombardment.** Against a confirmed pure Aluren list with no alternative-entry
package, use **+3 Silence; -2 Bombardment, -1 Raptor** and leave Priest out.

## 11. Golgari Landfall / Hogaak

**Their plan.** Supplier fills the graveyard for Hogaak while Moonshadow/Wight/Reclaimer create a
land-driven fair attack; Bowmasters, Thoughtseize, Push, Safekeeper, Wasteland, and Boseiju let the
deck fight without its graveyard [ecp-unfair-current-lists]{6}. Hogaak can be cast from the
graveyard using convoke and delve [ecp-unfair-oracle]{6}.

**Our role and counter-plan.** Leyline removes Hogaak and Supplier velocity, then win the ordinary
creature game with Swords and tokens. Do not overboard as though this were Dredge: they can cast
threats, remove creatures, and bring Force of Vigor. Kill Safekeeper before aiming Swords at Hogaak
or Wight; use Wasteland on a land that breaks Wight/Reclaimer utility, not reflexively.

**Mulligan shift.** A functional Leyline hand is strong, but a balanced creature/Swords hand is
keepable without it. Ship slow graveyard hate plus no board. On the draw, prioritize Swords for an
early Hogaak and basic Plains access against Wasteland.

**Therapy names.** Blind **Thoughtseize** when protecting Leyline, **Fatal Push** when one engine
creature matters, or **Force of Vigor** after sideboarding. Informed names prioritize duplicated
Hogaak or Wight only if Leyline is absent.

**Board:** **+4 Leyline of the Void; -3 Voice of Victory, -1 Cabal Therapy.** If game one shows an
all-in Hogaak configuration rather than the attested fair shell, **+2 Surgical; -2 Amped Raptor** as
well. Do not baseline Surgical into their diversified creature plan.

## 12. Dredge

**Their plan.** Replace draws with dredges, use Narcomoeba/Poxwalkers and Bridge to create free
material, Therapy away interaction, then Dread Return a payoff or win through combat. The
card-verified current list also has Force, making hate protection relevant
[ecp-unfair-current-lists]{8}. Bridge creates Zombies from its controller's deaths but exiles when
one of our creatures goes to our graveyard [ecp-unfair-oracle]{6}.

**Our role and counter-plan.** Mulligan for Leyline; back it with Surgical or Priest. Priest stops
Narcomoeba/Poxwalker entries and Dread Return targets. Keep Bombardment: sacrificing our nontoken
creature puts it in our graveyard and exiles their Bridges, which can collapse the token engine.
Surgical the first dredger only when necessary; Dread Return or the remaining high-density dredger
is often more load-bearing after the engine begins.

**Mulligan shift.** A Leyline hand with any clock is the benchmark. Without Leyline, require two of
Surgical, Priest, discard, and fast pressure. A Thoughtseize-only seven is not enough because their
graveyard is a resource.

**Therapy names.** Blind **Force of Will** when protecting Leyline/Priest, **Otherworldly Gaze** or
**Careful Study** before their first enabler, and **Into the Flood Maw** after seeing the bounce
sideboard. Use informed Therapy immediately; their own Therapy will strip the known hate.

**Board:** **+4 Leyline of the Void, +2 Surgical Extraction, +2 Containment Priest; -4 Swords to
Plowshares, -3 Voice of Victory, -1 Ajani.** Do not cut Bombardment. If their verified build has no
Bridge, the second Bombardment can become the second Ajani cut instead.

## 13. Painter

**Their plan.** Assemble Painter plus Grindstone, with Engineer/Welder tutoring and recurring
artifacts, while six Blasts become universal interaction after Painter. Saga, Fable, Karn, Bridge,
and artifact bullets provide a fair backup [ecp-unfair-current-lists]{7}. Painter's color effect is
static and Grindstone's mill is activated, so Rod stops the kill activation but not Painter or
their upgraded Blasts [ecp-unfair-oracle]{1}.

**Our role and counter-plan.** Kill Welder/Engineer before they untap; land Rod, then keep pressure
on Karn/Fable and mana. Conqueror redundantly stops Grindstone, Welder, Engineer, Karn, Saga's token
activation, and Cauldron activations. Surgical is strongest after Swords/Bombardment/discard puts
Painter, Grindstone, or Engineer in the graveyard; one-for-one removal alone is insufficient
against recursion.

**Mulligan shift.** Keep removal plus pressure or Rod/Conqueror plus colored mana. Ship hands whose
only interaction is discard and whose clock starts on turn three. Basic Plains matters against
their Saga mana-denial lines.

**Therapy names.** Blind **Painter's Servant**; name **Pyroblast** before Rod/Conqueror, **Goblin
Engineer** when they have not developed, or the known combo half after Thoughtseize.

**Board:** **+2 Null Rod, +2 Clarion Conqueror, +2 Surgical Extraction; -3 Voice of Victory, -2
Amped Raptor, -1 Cabal Therapy.** On the draw against a fast Saga/Tomb list, cut both Therapies
instead of the second Raptor. Keep all Swords and Bombardments for the eight recursion creatures
and Painter.

## 14. Oops! All Spells

**Their plan.** Cast an eight-card self-mill creature package from ritual/spirit-guide mana; with no
ordinary lands, Spy mills the library, Narcomoeba/Poxwalker supply bodies, Dread Return produces
Oracle, and Pact protects the line [ecp-unfair-current-lists]{4} [ecp-unfair-oracle]{5}. Force of
Vigor, Leyline of Sanctity, and Thoughtseize attack hate after boarding.

**Our role and counter-plan.** Stop the graveyard and the spell chain, then end the game before they
find Force of Vigor. Leyline is primary; Silence prevents multi-Ritual noncreature chains; Priest
stops free graveyard creatures and the Dread Return target; Surgical can remove Dread Return or
Oracle after discard/mill provides a legal target. Leyline of Sanctity stops our discard aimed at
them but does not stop Surgical, which targets a card.

**Mulligan shift.** Mulligan hardest here: keep Leyline plus pressure or two independent pieces of
turn-one/two interaction. On the draw, Thoughtseize without additional hate is not a keep. A Priest
hand needs mana before they combo; a turn-two Priest may simply be late.

**Therapy names.** Prefer an informed name rather than guessing between **Balustrade Spy** and
**Boggart Trawler**, which are both four-of self-millers. Name **Pact of Negation** before a key
spell, **Force of Vigor** when protecting Leyline, **Lively Dirge** when their mana telegraphs that
setup line, or **Thoughtseize** after board.

**Board:** **+4 Leyline of the Void, +3 Deafening Silence, +2 Containment Priest, +2 Surgical
Extraction; -4 Swords to Plowshares, -3 Voice of Victory, -2 Goblin Bombardment, -2 Ajani.** The
eleven-card transformation is warranted because every incoming card attacks a distinct portion of
the attested kill/protection package; keep all discard and one-drops so the deck still interacts and
clocks.

## Disconfirming analysis

- I tested the tempting claim that Null Rod “turns off” artifact decks against Oracle text. It does
  not stop Mystic Forge's static casting permission, Painter's static color effect, Fleshraker
  triggers, Thoughtcast, or artifact creatures. The plans therefore retain creature removal and a
  clock instead of treating Rod as a hard lock [ecp-unfair-oracle]{1}.
- I tested Containment Priest as generic Aluren hate. Oracle text disconfirms it: Aluren **casts**
  Acererak, while Priest only replaces entry by a creature that was not cast. Priest appears only
  against the attested hybrid's Show and Tell branch [ecp-unfair-oracle]{2}
  [ecp-unfair-oracle]{5}.
- I tested Leyline as the whole Reanimator plan. The current representative's eight-card Show and
  Tell/Stronghold Gambit pivot disconfirms that simplification, which is why Priest and Swords stay
  in the baseline [ecp-unfair-current-lists]{4}.
- I tested the corpus label as sufficient evidence for Dredge. The newest assigned Dredge row is a
  Goryo's/Reanimate list with none of the defining Dredge engine cards. The Dredge section therefore
  uses a list selected by observed Grave-Troll rather than label alone [ecp-unfair-current-lists]{8}.
- I tested overboarding Leyline/Surgical against Golgari. Its current Push/Thoughtseize/Wight/
  Bowmasters/Safekeeper plan remains functional without the graveyard and its sideboard has Force
  of Vigor, so the baseline stops at four Leylines [ecp-unfair-current-lists]{6}.

## Contradictions

| Relationship | Positions | Operational treatment |
|---|---|---|
| `contradicts` | The corpus archetype field calls Albertosd87's July 29 deck Dredge; its observed cards form a Force/Brainstorm Goryo's/Reanimate shell without dredgers or Bridge [ecp-unfair-current-lists]{8}. | Do not attach Dredge boarding to the label alone; require an observed dredger/Narcomoeba/Bridge engine. |
| `qualifies` | The aggregate Aluren core is Aluren/Acererak with Force, cantrips, Veil, Tomb, and Petal [ecp-current-corpus]{7}; the current representative also has a full Show and Tell/Omniscience package [ecp-unfair-current-lists]{6}. | Use the five-card hybrid board only when the alternative-entry package is observed; pure Aluren gets Silence but not Priest. |
| `tension` | The top-24 corpus treats Blue Artifacts as one archetype [ecp-current-corpus]{4}; the current representative is a Force/Emry/Kappa shell [ecp-unfair-current-lists]{3}. | Key on Emry/Force versus nonblue Saga swarm before choosing the Therapy/Voice cuts. |
| `qualifies` | The current Eldrazi representative boards Chalice rather than maindecking it [ecp-unfair-current-lists]{5}; the broader corpus finds Chalice in 88 of 90 lists [ecp-current-corpus]{6}. | Expect Chalice after boarding even when game one does not show it; do not assume its exact starting zone. |

## Revisit if

- The primer is used after the metagame snapshot's **2026-08-17** TTL, or a ban/new release changes
  the artifact-mana, graveyard, or combo engines.
- The registered sideboard changes. Even one flexible removal spell materially alters the large
  transformation plans against Doomsday, Reanimator, Dredge, Painter, and Oops.
- Testing shows that three-mana Clarion Conqueror routinely arrives after Tron, Blue Artifacts, or
  Mystic Forge has already extracted enough value; the play/draw alternatives should then become
  baseline.
- The event is paper/local and expected Aluren, Blue Artifacts, Eldrazi, or Show and Tell variants
  are known. Those umbrella labels conceal the sideboard-relevant branch decisions described above.
- The Dredge classifier is corrected and the corpus refreshed; re-run card-verified representative
  selection rather than preserving the current workaround.

## Acquisition candidates

- The attested MTGO tournament URIs for the Challenge-winning Doomsday list, the card-verified
  Dredge list, and the Oops list are source-grounded candidates for match replay/video or pilot notes
  if those are linked from the event pages [ecp-unfair-current-lists]{2}
  [ecp-unfair-current-lists]{4} [ecp-unfair-current-lists]{8}.
- The current Show and Tell and Reanimator lists' tournament pages are acquisition candidates for
  sideboarded game records that could validate how often their fair/alternative-entry pivots occur
  [ecp-unfair-current-lists]{1} [ecp-unfair-current-lists]{4}.
- The Blue Artifacts umbrella needs a fixed deck-level sample split into Force/Emry, nonblue Saga,
  and Welder branches before one literal swap map can replace the observed-card contingencies
  [ecp-current-corpus]{4} [ecp-unfair-current-lists]{3}.

---
provenance: agent-synthesis
updated: 2026-08-03
---

# Exact-75 pilot brief: Energy Cabal Therapy

## Registered construction and strategic identity

The exact list is 60 cards: 22 lands, 25 creatures, four Swords to Plowshares, four Thoughtseize,
three Cabal Therapy, and two Goblin Bombardment. Its sideboard is four Leyline of the Void, three
Deafening Silence, and two each of Clarion Conqueror, Containment Priest, Null Rod, and Surgical
Extraction.[ecp-exact-list]{1}

{inferred: synthesis} This is a proactive creature-engine deck with a disruptive overlay, not a
pure prison deck and not a conventional removal-heavy midrange deck. Its default winning arc is:

1. establish Guide of Souls, Ocelot Pride, or Ajani;
2. turn subsequent bodies into energy, life, Cats, Warriors, or planeswalker pressure;
3. use discard, Swords, Wasteland, Voice, Squelcher, or Bowmasters to buy the one or two attacks the
   engine needs; and
4. convert temporary or expendable creatures into perfect-information Therapies, Bombardment
   damage, or an Ajani transformation.

The registered 75 has no card-selection spell beyond two surveil lands, no mass removal, no direct
answer to an enchantment, and no spell that destroys an artifact. Its sideboard attacks artifacts
and activated abilities by switching them off, and attacks graveyards by exile.[ecp-exact-list]{2}
{extends} Consequently, opening hands should be evaluated as functional packages, not as collections
of individually powerful cards: the deck is punished more than a cantrip deck for keeping the wrong
half of its draw.

## Card roles

### Engine starters and payoffs

- **Guide of Souls (4):** best general-purpose turn-one engine. Every later creature adds life and
  energy; three energy turns any attacker into a larger flying threat. Guide before Ocelot means the
  Ocelot's entry gains life, enabling Ocelot's end-step Cat immediately.[ecp-scryfall-oracle]{1}
- **Ocelot Pride (4):** one-mana threat, lifegain enabler, and token snowball. It needs life gained
  that turn for the first Cat and ten permanents for token duplication.[ecp-scryfall-oracle]{2}
  {extends} Do not treat ascend as the baseline plan; it is the reward for already developing a wide
  board. Ocelot is still useful before ascend as a cheap first striker, recurring Cat source, and
  sacrifice resource.
- **Ajani, Nacatl Pariah (4):** two bodies for two mana and the cleanest bridge from creatures to a
  planeswalker endgame. Another Cat dying can transform Ajani; that includes Ajani's own token and
  Ocelot Cats.[ecp-scryfall-oracle]{3} {extends} Ajani plus Therapy is therefore discard plus a
  planeswalker, while Ajani plus Bombardment can transform at instant speed.
- **Amped Raptor (4):** two-power first striker plus a guaranteed look at the next nonland. Every
  nonland in this exact main deck has mana value at most two, so the Raptor's own two energy can pay
  for every hit that is otherwise legal to cast.[ecp-exact-list]{3}[ecp-scryfall-oracle]{4}
  {extends} This makes Raptor the deck's velocity card, but not literally fail-proof: Swords needs a
  target, and choosing not to cast a revealed card leaves it exiled. Cast Raptor while a desirable
  target still exists if Swords is a plausible hit.
- **Voice of Victory (3):** both pressure and protection. Each attack creates two temporary
  Warriors, and opponents cannot cast spells during your turn.[ecp-scryfall-oracle]{5} {extends}
  The Warriors remain through combat and can be sacrificed to flash back Therapy in the postcombat
  main phase, or to Bombardment before the end-step sacrifice trigger resolves. Voice should often
  precede the spell or attack that must resolve.

### Disruption and protection

- **Thoughtseize (4):** exact information plus selection. It is the preferred first discard spell
  when Therapy is also available because it supplies the name for Therapy; its two-life loss still
  occurs when Amped Raptor casts it using energy because that loss is in the effect, not the mana
  cost.[ecp-scryfall-oracle]{6}
- **Cabal Therapy (3):** high-variance blind discard, high-ceiling informed discard, and a second
  use of an expendable body. It takes every copy of the chosen nonland card and flashes back by
  sacrificing a creature.[ecp-scryfall-oracle]{7} Flashback is casting the card from the graveyard
  for its alternative cost and exiles it when it leaves the stack.[ecp-comprehensive-rules]{1}
- **Swords to Plowshares (4):** unconditional creature exile at the cost of life to its controller.
  [ecp-scryfall-oracle]{8} {extends} In an aggro mirror, preserve it for the engine creature or
  stabilizer, not merely the first attacker. Against a fast combo deck with few creatures, it is a
  natural sideboard cut.
- **Orcish Bowmasters (3):** flash interaction, a second body, and punishment for extra draws.
  [ecp-scryfall-oracle]{9} {extends} It is strongest when held through the opponent's cantrip window,
  but developing it proactively is correct when the Orc Army, clock, or sacrifice body matters more
  than a speculative draw trigger.
- **Hexing Squelcher (3):** the permission-breaker. It is uncounterable, makes your spells
  uncounterable, and taxes targeted interaction with ward—pay 2 life on itself and the rest of your
  creatures.[ecp-scryfall-oracle]{10} {extends} Lead with it before committing the spell that
  matters. Multiple Squelchers grant multiple ward abilities to the other creatures; each ward
  trigger must be dealt with independently.
- **Goblin Bombardment (2):** sacrifice outlet, reach, combat control, and Ajani enabler. It turns
  Voice's temporary Warriors and threatened creatures into damage.[ecp-scryfall-oracle]{11}
  {extends} When removal is aimed at a creature, cash it in only if the damage, Ajani trigger, or
  Therapy resource is worth more than retaining it if the removal fails.

### Mana as interaction

- **Wasteland (4):** mana denial and utility-land removal, but colorless in a deck whose important
  opening spells require white or black.[ecp-scryfall-oracle]{12} {extends} Treat Wasteland as a
  spell unless the rest of the hand already casts its plan. Avoid a turn-one Wasteland line merely
  because a target exists when it strands Guide, Thoughtseize, or a two-drop.
- **Karakas (2):** white source and protection/reuse for legendary creatures. It can bounce front-
  face Ajani to save or replay it; transformed Ajani is a planeswalker and is not a legal Karakas
  target.[ecp-scryfall-oracle]{13}
- **Elegant Parlor / Shadowy Backstreet:** tapped fixing plus surveil.[ecp-scryfall-oracle]{14}
  {extends} Fetch them on a low-opportunity-cost turn or opponent's end step. Avoid making the
  opening land enter tapped if the matchup can punish a lost first turn.
- **Plains:** the sole basic. {extends} Fetch it when a stable white source matters more than black
  discard or red sequencing; otherwise plan explicitly for opposing Wasteland.

## Sequencing rules of thumb

### Turns one through three

{extends} Use this priority tree, then override it for matchup speed:

1. **Unknown opponent, functional creature curve:** lead Guide. Guide into any creature banks
   energy; Guide into Ocelot gains life and creates the first Cat at end step.
2. **Known or signaled fast combo:** lead Thoughtseize. If the hand contains Therapy too,
   Thoughtseize first converts Therapy from a guess into exact multi-copy discard.
3. **Ocelot without Guide:** lead Ocelot when it can gain life itself safely or another immediate
   lifegain line exists. Otherwise Ajani may be the higher-output turn-two play.
4. **Ajani plus Therapy:** deploy Ajani, then decide whether the Cat token is worth sacrificing now.
   Sacrificing it can transform Ajani, but holding the token may be better against removal or when
   the second Therapy is not yet valuable.
5. **Voice/Squelcher before commitment:** against counterspells, Squelcher first protects all later
   spells; against instant-speed interaction, Voice first shuts off spells during your turn. Voice
   does not prevent abilities.
6. **Raptor with targets:** cast Raptor when a revealed Swords will have a legal, worthwhile target.
   A Raptor cast from anywhere other than hand still grants energy but does not perform the exile-
   and-cast sequence.[ecp-scryfall-oracle]{15}

### Combat and sacrifice discipline

{extends}

- Announce Guide's energy target only after attacks are declared; use flying to bypass a stalled
  board or put counters on an attacker that survives expected combat.
- With Voice, attack before spending a real creature on Therapy when the two mobilized Warriors can
  pay the flashback cost postcombat.
- Against sweepers, do not turn every token into more board unless the clock materially shortens.
  Bank Therapy in the graveyard and Bombardment on the battlefield as recovery/conversion tools.
- Sequence Bombardment pings one at a time. Preserve enough creatures for the actual lethal line,
  and remember Ajani's transform trigger needs another Cat to die, not Ajani itself.
- A creature sacrificed to Therapy pays the cost before the opponent can respond. Sacrifice is not
  destruction.[ecp-comprehensive-rules]{2} {extends} This makes a removal-targeted token or Cat a
  particularly efficient flashback payment when priority permits.

## Cabal Therapy technique

### Information hierarchy

{extends} Choose Therapy names from the highest available information tier:

1. **Revealed current hand:** after Thoughtseize, a prior Therapy, or another reveal, name the
   highest-impact remaining card; prefer a duplicated card when taking both copies matters.
2. **Observed action:** infer from what the opponent fetched, cast, declined to cast, or protected.
   A cantrip that kept cards, an uncracked fetch, or a passed turn changes likely holdings, but mark
   the inference as uncertain.
3. **Archetype plus game state:** name the card that defeats the line you are about to take—not
   automatically the most common card in the archetype.
4. **Truly blind:** avoid spending Therapy unless the body/curve makes the floor acceptable. If it
   must be cast, name the broadly played card most capable of interacting with the next play.

Rules require an Oracle card name, but not a card legal in the format; token names are invalid
unless a card has that name.[ecp-comprehensive-rules]{3}

### Practical name classes

{extends} The matchup specialists should replace these classes with exact names for each opponent:

- **Protect a key spell:** name Force of Will or the opponent's relevant free answer before the
  commitment; after a known blue hand, remove the card that makes the counter live, not reflexively
  Force itself.
- **Break a combo:** name the missing engine, tutor, or payoff indicated by the cards already seen.
  When one card is redundant and another is the bottleneck, name the bottleneck.
- **Protect the board:** name the sweeper or mass-bounce spell before adding more creatures.
- **Win a fair exchange:** name the removal spell likely to answer Guide, Ocelot, Voice, or Ajani.
  If Therapy can take multiples, target the card whose redundancy would otherwise beat one discard.
- **After a cantrip:** update the name; do not assume the hand remains as last revealed. Brainstorm
  can hide cards on top, while a shuffle can destroy that information.

### Flashback valuation

{extends} A flashback is attractive when at least one of these is true: the target hand is known;
the sacrificed creature is temporary, removal-bound, or surplus; the sacrifice transforms Ajani;
or stripping one exact card opens a winning turn. It is unattractive when it sacrifices the only
engine, reduces a lethal attack, or attacks an unknown hand whose relevant cards are highly
redundant. A missed Therapy still reveals the hand, so the first cast can set up a later flashback,
but information alone does not justify losing a central creature.

## Mulligan framework

The rules allow a fresh seven followed by bottoming one card per mulligan taken.[ecp-comprehensive-rules]{4}
{extends} Use that selection aggressively: a coherent six is usually better than a seven whose
spells cannot be sequenced.

### Baseline keep test

Keep an unknown-matchup seven when it satisfies all four:

1. **Mana:** at least one colored source and a credible path to cast the first two turns. One-land
   hands need a one-drop plus meaningful action or selection; Wasteland is not a colored source.
2. **Action:** a turn-one engine or discard spell.
3. **Follow-through:** a second creature, Raptor, Ajani, interaction, or a second land that lets the
   first play develop.
4. **Role balance:** enough pressure to close after disruption, or enough disruption to let the
   pressure arrive. Three discard spells and no clock is not automatically functional; four
   creatures with no second land is not automatically pressure.

### Matchup-adjusted keeps

{extends}

- **Against fast combo:** require turn-one disruption or a very strong postboard prison start.
  Guide plus a fair curve is too slow by itself. A Leyline matchup requires Leyline or a hand whose
  other graveyard interaction is timely; do not keep an otherwise empty hand solely because it has
  Leyline if the opponent can answer it and the hand cannot pressure.
- **Against tempo/Wasteland:** prioritize two functional mana sources or fetch access to Plains.
  One nonbasic plus multiple colors of spells is fragile. A cheap threat plus removal is more
  important than a speculative Wasteland exchange.
- **Against creature decks:** a one-drop engine plus Swords, Bowmasters, or a strong two-drop is the
  model. Discard-only hands without board presence usually fall behind.
- **Against control:** keep resilient, layered pressure. One threat plus several removal spells is
  weak; Ajani, Raptor, Voice, Therapy, and Bombardment make resources persist across answers.
- **On the play:** Thoughtseize and Wasteland improve because they act before the opponent deploys;
  one-land proactive hands become somewhat safer.
- **On the draw:** value Swords/Bowmasters and stable mana more; be skeptical of Wasteland as the
  second 'land' and of Therapy guesses after the opponent has already shaped the hand.

### Example opening hands

These are strategic examples, not probabilistic guarantees. {extends}

- **Keep, unknown:** Marsh Flats, Arid Mesa, Guide, Ocelot, Ajani, Swords, Raptor. Guide on turn one
  gives multiple strong turn-two branches and both colors needed soon.
- **Keep, known combo:** Marsh Flats, Thoughtseize, Therapy, Voice, Amped Raptor, Scrubland,
  Wasteland. Thoughtseize supplies information; Therapy plus clock follows. Fetch sequencing must
  preserve red and white.
- **Keep, fair matchup:** Arid Mesa, Plains, Ocelot, Swords, Bowmasters, Ajani, Bombardment. It has
  early board, interaction, and sacrifice conversion.
- **Borderline one-land keep on play:** Marsh Flats, Guide, Ocelot, Thoughtseize, Swords, Ajani,
  Raptor. It has five live one-mana actions but misses turn two without a land; keep only when the
  matchup rewards the turn-one action and the selected fetch color supports the chosen line.
- **Mulligan:** Wasteland, Karakas, Bowmasters, Squelcher, Bombardment, Therapy, Raptor. It cannot
  cast black or red spells and has no turn-one proactive colored play.
- **Mulligan versus combo:** Plateau, Arid Mesa, Guide, Ocelot, Ajani, Swords, Bombardment. Strong
  fair hand, but no relevant turn-one interaction and too slow against a known fast kill.
- **Mulligan versus tempo:** Badlands, Wasteland, double Voice, Ajani, Swords, Raptor. It lacks white
  on turn one, is vulnerable to losing its only colored land, and cannot curve reliably.
- **Postboard graveyard keep:** Leyline, Marsh Flats, Guide, Ocelot, Thoughtseize, Raptor, Plateau.
  Leyline starts in play after mulligans, while the other six still supply pressure and discard.
  [ecp-comprehensive-rules]{5}

### Bottoming priorities

{extends} On six or five, bottom cards that do not serve the hand's chosen plan: redundant
Wasteland before a needed colored land; the third expensive-in-sequence two-drop before the first;
Swords against known creatureless combo; a second Leyline when one already establishes the effect;
or Bombardment when the hand lacks bodies. Preserve a complete two-turn sequence over raw card
quality.

## Sideboard roles and constraints

The registered 15 supports exact one-for-one swaps while keeping a legal 60-card deck; Constructed
rules permit a sideboard of up to fifteen and a deck of at least sixty.[ecp-wpn-format-rules]{1}
{extends} Every matchup table in the final primer should list equal numbers in and out and should
state play/draw changes separately rather than smuggling conditional extras into an unequal plan.

### Leyline of the Void (4)

Starts on the battlefield only from the opening hand and replaces cards entering the opponent's
graveyard with exile.[ecp-scryfall-oracle]{16} The pregame action happens after mulligans.
[ecp-comprehensive-rules]{6} {extends} Board four when the opening-hand effect is central; partial
Leyline packages sharply reduce the reason to accept mulligans for it. It does not exile your own
graveyard, so your Therapy flashback remains available. However, Leyline can deprive Surgical of
targets because opposing cards never reach the graveyard.

### Surgical Extraction (2)

Targets a nonbasic card already in a graveyard and can be paid for with two life.[ecp-scryfall-oracle]{17}
Its library search may intentionally find fewer matching cards because the library is hidden.
[ecp-comprehensive-rules]{7} {extends} Surgical is tactical rather than blanket hate: pair it with
Thoughtseize, Therapy, Swords, Wasteland, or an opposing spell that naturally reaches the graveyard.
Use it to remove a bottleneck or gain exact hand/deck information, not merely at the first legal
target. With Leyline already active, plan how a target can exist before counting Surgical as live.

### Deafening Silence (3)

Each player is limited to one noncreature spell per turn.[ecp-scryfall-oracle]{18} {extends} The deck
can develop creatures through it, but it also constrains its own Thoughtseize, Therapy, Swords,
Bombardment, and noncreature Raptor hits. Sequence discard or removal before/after Silence with this
limit in mind. Raptor can still cast a creature hit after another noncreature spell; a noncreature
hit may be uncastable if the turn's allowance was already used.

### Containment Priest (2)

Exiles nontoken creatures that would enter without being cast.[ecp-scryfall-oracle]{19} {extends}
It is flash pressure/hate, but it conflicts with Ajani's transform: transformed Ajani returns to
the battlefield without being cast and Priest will exile it. Do not sacrifice a Cat expecting an
Ajani transformation while your Priest remains on the battlefield.

### Null Rod (2)

Stops activated abilities of artifacts.[ecp-scryfall-oracle]{20} {extends} The main deck contains no
artifacts, so this is asymmetric against the registered main 60. It does not stop triggered or
static artifact abilities, and it does not remove the artifact; board it when the opponent's plan
depends on activations, not merely because artifacts are present.

### Clarion Conqueror (2)

Stops activated abilities of artifacts, creatures, and planeswalkers.[ecp-scryfall-oracle]{21}
{extends} It covers more permanent types than Null Rod and supplies a flying clock, but it also
turns off your transformed Ajani's loyalty abilities. It does not stop Wasteland (a land), Goblin
Bombardment (an enchantment), Guide/Ocelot/Voice triggers, or Therapy flashback. When Conqueror and
Ajani are both in the postboard deck, plan to use Ajani as two bodies or delay Conqueror until after
an important loyalty activation.

### What the sideboard cannot repair

{inferred: synthesis} The sideboard has no sweeper, enchantment removal, direct artifact removal,
additional spot removal, or generic answer to a resolved large creature.[ecp-exact-list]{4}
Therefore matchup plans cannot claim a postboard answer that the 75 does not contain. They must
instead use discard before resolution, Swords for creatures, activated-ability locks where
applicable, Wasteland for mana/lands, and a fast clock. This is the primary constraint the final
matchup synthesis must honor.

## Disconfirming analysis

- **“Raptor never misses” was tested against legality, not just mana value.** The exact list confirms
  all nonlands cost one or two, supporting energy sufficiency, but Swords still needs a legal target
  and Deafening Silence can prevent a noncreature hit from being cast. The defensible claim is
  “energy covers every hit,” not “every hit is always castable.”[ecp-exact-list]{5}
  [ecp-scryfall-oracle]{22}
- **“Priest is fully asymmetric” is false.** Oracle text applies to any nontoken creature entering
  uncast, and Ajani transforms by exile/return rather than casting. The sideboard plan must surface
  this internal conflict.[ecp-scryfall-oracle]{23}
- **“Conqueror is a strict Null Rod upgrade” is false.** Conqueror is broader and a creature, but
  it costs more and disables the deck's own planeswalker activations; Null Rod does not.
  [ecp-scryfall-oracle]{24}
- **“More graveyard hate is always additive” is false.** Leyline replaces opposing graveyard entry,
  while Surgical requires a graveyard target. They can coexist, but their marginal effects are not
  automatically additive.[ecp-scryfall-oracle]{25}
- **“Always lead Guide” is disconfirmed by matchup speed.** The card engine supports Guide as the
  general development lead, but the list's discard exists specifically to interact before fast
  opposing plans. The brief therefore gives matchup knowledge authority over the default.
  [ecp-exact-list]{6}
- **Mulligan prescriptions are not source-derived win-rate thresholds.** No attested source provides
  hand-level outcome data for this exact 75. Every keep/mulligan example is marked `extends` and
  should be updated if replay or solver evidence becomes available.

## Contradictions

- **Raptor reliability — `qualifies`:** the exact-list mana-value distribution says its two energy
  pays for every nonland hit,[ecp-exact-list]{7} while Oracle targeting and Deafening Silence text
  show that some hits can still be illegal to cast.[ecp-scryfall-oracle]{26} These claims concern
  different gates (payment versus casting legality), so the latter qualifies rather than
  contradicts the former.
- **Priest alongside Ajani — `tension`:** Priest is desirable where creatures enter without being
  cast, but the same text catches the deck's own Ajani transform.[ecp-scryfall-oracle]{27} Matchup
  plans that board Priest while retaining Ajani must name this sequencing cost.
- **Leyline plus Surgical — `tension`:** Leyline's replacement effect prevents the usual opposing
  graveyard target, while Surgical needs one.[ecp-scryfall-oracle]{28} The pair is not illegal, but
  a six-card graveyard package has diminishing tactical coherence unless targets arise before
  Leyline or through another route.

## Revisit if

- any card in the registered 75 changes;
- Oracle text or Legacy legality changes;
- matchup specialists establish that a particular sideboard card is routinely uncastable or
  counterproductive in the archetypes it was intended to cover;
- hand-level replay data becomes available for mulligan calibration;
- the final primer recommends an unequal in/out count, a sideboard answer absent from the 75, or a
  Therapy name inconsistent with the opponent's current representative list.

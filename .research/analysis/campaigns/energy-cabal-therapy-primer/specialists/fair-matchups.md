---
description: Fair-matchup specialist report for the Energy Cabal Therapy primer
type: research
summary: Exact-75 plans for the prevalent tempo, control, creature, midrange, and Lands matchups.
updated: 2026-08-11
decisions:
  - Preserve the maindeck in fair matchups unless a sideboard card directly attacks a named engine.
  - Treat sideboarding recommendations as exact-75 synthesis, not copied pilot authority.
key_findings:
  - The sideboard is deliberately unfair-matchup-heavy, so several fair matchups require zero swaps.
  - Hexing Squelcher, Voice of Victory, Bowmasters, and basic Plains are the structural anti-tempo package.
  - Lands is the fair-side exception where eight sideboard cards are live.
provenance: agent-synthesis
---

# Fair-matchup report: Energy Cabal Therapy

## Evidence boundary

The registered sideboard contains no generic fair-matchup removal or blasts: it is four Leyline,
three Deafening Silence, and two each of Conqueror, Priest, Null Rod, and Surgical
[ecp-exact-75]{1}. Accordingly, **“no change” is an intentional plan**, not an omission. The exact
swap maps below are `{inferred: adapted}` from representative current configurations and the
registered 75. Lucas Giggs's near-identical Showcase-finalist list supports the matchup roles and
sequencing, but his sideboard had Ending, blasts, and an extra Priest, so his literal swaps do not
transfer [ecp-giggs-guide]{1}.

As of August 3, the relevant high-volume fair field includes Dimir Tempo, Izzet Cutter/Delver, UW
Blink/Azorius Tempo, Boros Ocelot, Lands, Death & Taxes, UWx/Azorius Control, Cradle Control, and
Mardu Ocelot [ecp-mtgdecks-meta]{1}. MTGGoldfish independently places Dimir first and shows recent
August results for the major tempo, Energy, Lands, and control shells [ecp-goldfish-meta]{1}.

## Shared fair-matchup rules

- **Role:** default to resilient go-wide midrange. Trade Swords for the threat that races or scales
  past the board; use discard to clear the one effect that invalidates the next two turns. Do not
  turn into a weak prison deck simply because sideboard cards exist.
- **Mana:** fetch **Plains** early unless black or red is immediately necessary. The successful pilot
  explicitly calls out basic Plains against Wasteland [ecp-giggs-guide]{1}. Keep fetches uncracked
  against Stifle only when doing so does not strand the curve.
- **Anti-blue sequencing:** lead Guide/Ocelot when raw development matters; lead Squelcher when the
  following hand contains multiple creatures and the tempo loss is survivable. Squelcher turns off
  counters for later spells and taxes targeted interaction; Voice forces most interaction into the
  opponent's main phase; Bowmasters punishes cantrips [ecp-giggs-guide]{1}.
- **Therapy:** blind-name only when the matchup and line make one card overwhelmingly important.
  Otherwise Thoughtseize first, observe a cantrip, or cast Therapy after the opponent telegraphs a
  holding pattern. Flashback is strongest when it flips Ajani or sacrifices a token blanked by the
  board. Do not sacrifice the only creature carrying the race merely for speculative information.
- **Mulligans:** one-land hands require a one-drop plus a second-land path; Wasteland is not a colored
  source. Against Wasteland/Daze/Stifle, prefer two colored sources or fetch + basic access. Against
  removal piles, prioritize two engines over a single fast creature. Against creature decks, keep
  Swords or a faster Guide/Ocelot/Ajani engine.

## 1. Dimir Tempo

**Their plan.** Tamiyo, Bowmasters, Nethergoyf/Murktide and sometimes Barrowgoyf establish a cheap
clock while Thoughtseize, Push/Snuff Out, Daze, Force, Flow State, and Wasteland prevent recovery;
Kaito supplies the longer game [ecp-dimir-tempo]{1}. Post-board, Massacre is common enough to play
around [ecp-dimir-tempo]{1}.

**Our counter-plan.** Be the go-wide deck, not the discard deck. Their one-for-ones struggle against
Ocelot tokens, Raptor, Ajani transformation, and Bombardment. The near-identical-list pilot names
exactly that resource mismatch and flags Murktide, Barrowgoyf, and transformed Tamiyo as the cards
that can reverse it [ecp-giggs-guide]{1}. Kill Tamiyo before it transforms when practical; reserve
Swords for Murktide/Barrowgoyf when smaller creatures can be raced. Do not expose every white body
to a post-board Massacre; Bombardment and a transformed Ajani are excellent insurance.

**Mulligan shift.** Keep functional two-land engine hands even if slow. Ship hands whose sole spell
is discard or whose colored mana folds to one Wasteland. Squelcher plus follow-up creatures is a
premium seven.

**Therapy names.** Blind: **Brainstorm** on turn one when no board-specific read exists; **Fatal
Push** when your hand is one key creature; **Force of Will** before Bombardment. Informed: Murktide,
Massacre, Kaito, or the known duplicated removal spell.

**Board:** **+2 Clarion Conqueror; -2 Cabal Therapy.** Conqueror is a threat that switches off Tamiyo,
Clues, and planeswalker activations; Therapy is poor once both players are trading from small hands.
The restriction is symmetric, so sequence Guide activations and an Ajani transformation before it
when practical [ecp-clarion-conqueror]{1}.
On the draw, if their build is unusually low on activated permanents and high on Barrowgoyf, make
**no change** instead—the two retained Therapies can clear Massacre or removal. `{inferred: adapted}`

## 2. Izzet Cutter / Izzet Delver

**Their plan.** Channeler/Delver creates early pressure; Cori-Steel Cutter plus cheap spells floods
the board; Murktide goes over it. Bolt, Daze, Force, Wasteland, Brainstorm/Ponder and Bauble maintain
tempo [ecp-izzet-delver]{1}. Hydroblast and extra removal are common after boarding
[ecp-izzet-delver]{1}.

**Our counter-plan.** Stabilize life total, then make every draw a threat. Swords Murktide or Cutter
unless a Channeler is dealing lethal-sized damage. Bowmasters is best held for a cantrip window when
life permits. Squelcher is the pivot: once it resolves, develop creatures into their stranded
counters. Voice similarly denies end-step Bolt. Fetch Plains; avoid paying unnecessary life to
Thoughtseize.

**Mulligan shift.** A one-drop, colored lands, and Swords is ideal. Ship slow discard-heavy hands and
hands unable to cast white spells through Wasteland. Guide plus Ocelot can race; Ocelot alone on the
draw into their one-drop often cannot.

**Therapy names.** Blind **Lightning Bolt** when protecting Ocelot/Guide or life; **Force of Will**
before Bombardment; **Cori-Steel Cutter** when they have cantripped but not developed. After a Bauble
or cantrip pause, name the removal/counter their line represents.

**Board:** **no change.** Null Rod only suppresses Bauble's activated draw and does not answer
Cutter's triggered engine, so lowering creature/removal density for it is an overboard. If a revealed
list has four Bauble plus additional activated artifacts, **+2 Null Rod; -2 Cabal Therapy** is a
contingent option, preferably on the play. `{inferred: adapted}`

## 3. Azorius Tempo

**Their plan.** Tamiyo, Phelia and Quantum Riddler generate repeated value behind Stifle, Swords,
Daze, Force and Wasteland; some lists finish with Murktide and use Teferi as a pivot
[ecp-fair-archetypes]{1}. Phelia can repeatedly blink value permanents and remove a blocker for a
turn.

**Our counter-plan.** Develop around Stifle and Daze, kill Tamiyo before transformation, and avoid
giving Phelia profitable attacks. Squelcher makes counter-heavy draws embarrassing; Bowmasters
punishes their cantrip density. Bombardment protects value from Swords and breaks stalled combat.
Priest is unusually live because it prevents exiled permanents from returning through Phelia.

**Mulligan shift.** Two colored lands, a one-drop and either Swords/Bowmasters/Squelcher is strong.
Do not keep a fetch-only mana plan with no turn-one play into Stifle.

**Therapy names.** **Swords to Plowshares** when protecting an engine, **Force of Will** before
Bombardment, **Phelia** when their turn-two posture is obvious, and **Wrath of the Skies** only if the
list is known to splash the control package.

**Board:** **+2 Containment Priest, +2 Clarion Conqueror; -3 Cabal Therapy, -1 Thoughtseize.** Priest
switches off Phelia returns; Conqueror switches off Tamiyo, Phelia, and Teferi activations, but also
our Guide and transformed Ajani activations [ecp-clarion-conqueror]{1}. On the draw,
retain the Thoughtseize and cut a second discard only if their build is more control than tempo.
`{inferred: adapted}`

## 4. UW Blink / Yorion value

**Their plan.** Accumulate enters-the-battlefield value and reuse it with Phelia, Flickerwisp,
Ephemerate-style effects, Yorion, and/or Recruiter chains; Solitude and Swords convert that value into
board control. The current aggregator separates UW Blink as 4.40% of its field
[ecp-mtgdecks-meta]{1}.

**Our counter-plan.** Priest attacks the blink return clause, while Conqueror taxes Phelia and
planeswalkers. Establish Bombardment before committing the fourth creature so exile removal cannot
erase all value. Therapy should target the sweeper or blink enabler, not a replaceable creature.

**Mulligan shift.** Keep Bombardment/Ajani value hands; ship pure one-for-one hands. A quick Guide +
Ocelot draw is still valuable because their deck is mana-hungry.

**Therapy names.** **Swords to Plowshares** early; **Solitude** when they preserve five mana cards;
**Wrath of the Skies** after a suspicious non-development turn; **Phelia** when their hand shape is
known.

**Board:** **+2 Containment Priest, +2 Clarion Conqueror; -3 Cabal Therapy, -1 Thoughtseize.** If the
observed build has no blink-return effect, do not bring Priest: use only **+2 Conqueror; -2 Therapy**.
`{inferred: adapted}`

## 5. Azorius / UWx Control

**Their plan.** Trade with Swords and counters, reset the battlefield with Wrath of the Skies, then
pull ahead via Tamiyo, Teferi, Murktide, Mystic Sanctuary, and sometimes The One Ring
[ecp-azorius-control]{1}. The danger is not one removal spell but allowing a sweeper or planeswalker
to convert their temporary parity into inevitability.

**Our counter-plan.** Pressure in waves. Two threats are usually enough; hold the third unless it
adds immediate value. Prioritize Bombardment, transformed Ajani, and Voice. Thoughtseize/Therapy is
good before the pivotal commitment but poor after both hands empty. Wasteland can interrupt Sanctuary
or force a control turn off schedule, but colored development comes first.

**Mulligan shift.** Keep discard plus two independent engines; ship creature-light reactive hands.
Bombardment and Squelcher are premium. Do not mulligan solely for speed.

**Therapy names.** **Wrath of the Skies** before widening; **Force of Will** before Bombardment;
**Swords to Plowshares** when Ajani/Ocelot is the only engine; **Teferi** or **The One Ring** when the
mana/read points there.

**Board:** **+2 Clarion Conqueror; -2 Swords to Plowshares.** Conqueror pressures while switching off
planeswalkers and Tamiyo, at the real cost of disabling our Guide/Ajani activations
[ecp-clarion-conqueror]{1}; two Swords remain for Murktide or other finishers. If the revealed list has six or more
creature threats, cut **-2 Cabal Therapy** instead. `{inferred: adapted}`

## 6. Boros Energy / Boros Ocelot

**Their plan.** Win the same Guide/Ocelot/Ajani/Raptor/Bombardment battlefield while using Thalia,
Sand Scout and Static Prison rather than discard/Bowmasters to gain tempo [ecp-boros-lands-control]{1}.

**Our counter-plan.** We are the slightly more interactive deck. Swords Guide before the lifegain/
energy snowball when possible; otherwise Swords Ajani before a profitable transformation. Bombardment
dominates small-creature combat, so Therapy it away or resolve yours first. Bowmasters is merely a
flash two-for-one here—cast it for board presence instead of waiting for a draw trigger. Wasteland
Lazotep Quarry if doing so does not break your own curve.

**Mulligan shift.** Require board presence: a one-drop/Ajani/Raptor and Swords or Bombardment. Ship
discard-only and Bowmasters-only hands.

**Therapy names.** Blind **Swords to Plowshares** or **Goblin Bombardment** according to your hand;
name **Static Prison** to protect Bombardment/Ajani, or **Amped Raptor** after an Ocelot start.

**Board:** **no change.** Every maindeck category is more relevant than the registered narrow
sideboard. Do not bring Conqueror merely for Ajani/Bombardment activations; it is slower than playing
your own engine. `{inferred: adapted}`

## 7. Mardu Energy mirror

**Their plan.** The current mirror core is effectively identical: Guide, Ocelot, Ajani, Raptor,
Squelcher, Bowmasters, Voice, discard, Swords, and Bombardment [ecp-mardu-mirror]{1}.

**Our counter-plan.** Preserve material and win Bombardment/Ajani exchanges. Thoughtseize is best
used to remove Bombardment or Swords immediately before a transformation. Therapy becomes reliable
after either discard spell reveals the hand. Do not flash Therapy back by sacrificing a meaningful
creature unless it flips Ajani, strips multiple copies, or clears the only answer to a winning line.

**Mulligan shift.** Keep balanced engine/removal hands; reject all-discard hands. On the draw, Swords
or Guide is highly desirable because an unchecked Ocelot compounds quickly.

**Therapy names.** **Swords to Plowshares**, **Goblin Bombardment**, then the revealed duplicate;
**Amped Raptor** is a reasonable blind name after Guide/Ocelot when their hand needs a bridge.

**Board:** **no change.** If the opponent reveals a graveyard recursion transformation, respond to
that observed package rather than pre-boarding Leyline. `{inferred: adapted}`

## 8. Death & Taxes (including BW Yorion)

**Their plan.** Constrain mana and attacks with Wasteland/Port/Thalia, deploy creatures through
Aether Vial, and grind with Stoneforge, Solitude, Recruiter/blink packages, and in BW builds
Overlord of the Balemurk. The current BW Yorion signature cards are Solitude, Stoneforge, and
Overlord [ecp-goldfish-meta]{1}.

**Our counter-plan.** Fetch Plains, use Swords to prevent equipment or blink engines from taking
over, and use Bombardment to invalidate small-creature combat. Null Rod shuts Vial and equipment
activations; Priest stops Vialed creatures and blink/Overlord returns. Remember Null Rod does not
remove already-attached equipment.

**Mulligan shift.** Keep colored lands and board interaction; Wasteland-only hands are traps. A hand
with Null Rod post-board still needs a clock.

**Therapy names.** **Aether Vial** on turn one if their archetype is known; **Swords to Plowshares**
or **Solitude** before committing an engine; **Stoneforge Mystic** when they keep a setup hand;
**Skyclave Apparition** to protect Bombardment.

**Board:** **+2 Null Rod, +2 Containment Priest; -3 Thoughtseize, -1 Cabal Therapy.** On the play
against a Vial-light 60-card mono-white list, use **+2 Null Rod; -2 Thoughtseize** only. Against
Yorion/Phelia/Overlord, retain all four hate cards. `{inferred: adapted}`

## 9. Cradle Control

**Their plan.** Use mana creatures and Gaea's Cradle to jump from a small board into Green Sun's
Zenith/Natural Order/value creatures, with creature tutoring making singleton answers reliable.
MTGDecks places the archetype in the current top twenty [ecp-mtgdecks-meta]{1}.

**Our counter-plan.** Kill the first mana creature when that denies the explosive turn; Wasteland
Cradle before they untap with a wide board. Priest stops creatures entering via Zenith/Order, and
Conqueror slows non-mana activated engines, but neither replaces a clock. Bombardment lets small
tokens police mana creatures.

**Mulligan shift.** Prioritize Swords, Wasteland plus colored mana, and a quick engine. Discard plus
no pressure is not enough.

**Therapy names.** **Green Sun's Zenith** blind; **Natural Order** after fast mana; otherwise name
the payoff revealed by an earlier discard spell.

**Board:** **+2 Containment Priest, +2 Clarion Conqueror; -3 Cabal Therapy, -1 Thoughtseize.** Priest
stops Zenith/Order entries; Conqueror shuts mana-creature activations as well as other artifact,
creature, and planeswalker abilities [ecp-clarion-conqueror]{1}. Sequence your own Guide activations
first, and do not transform Ajani into a Conqueror unless the static lock is worth losing the
planeswalker activations. `{inferred: adapted}`

## 10. Lands

**Their plan.** Exploration/Mox Diamond accelerates a Loam engine, Sphere constrains spell decks,
Depths/Stage creates Marit Lage, and Maze/Tabernacle/Boseiju plus land destruction dismantles creature
and mana development [ecp-lands]{1}.

**Our counter-plan.** This is the one “fair” opponent against which the sideboard transforms
substantially. Leyline turns off Loam; Surgical can remove Loam or a combo land; Null Rod shuts Mox,
Map, Needle, and other activated artifacts. Karakas answers Marit Lage if protected, while Wasteland
must usually be held for Stage/Depths rather than fired at a random mana land. Develop just enough
creatures to pressure without losing the entire board to Tabernacle mana.

**Mulligan shift.** Post-board, a functional hand with Leyline is excellent, but do not keep a
Leyline hand that cannot cast a threat. A hand with Surgical plus discard/Wasteland can substitute.
Karakas, colored mana, and a clock is keepable without hate.

**Therapy names.** **Crop Rotation** first; **Exploration** on turn one when speed matters;
**Life from the Loam** only before Leyline; **Sphere of Resistance** when your hand is one-drops and
they lead Tomb/Mox.

**Board:** **+4 Leyline of the Void, +2 Surgical Extraction, +2 Null Rod; -4 Swords to Plowshares,
-3 Orcish Bowmasters, -1 Voice of Victory.** Karakas—not Swords—is the dependable Marit Lage answer;
Bowmasters has no cantrip prey; Voice has little text. On the draw against a Sphere-heavy list,
retain the boarded-out Voice as a two-drop body and cut one Thoughtseize instead. Never bring
Deafening Silence: Lands can progress through lands and one spell per turn. `{inferred: adapted}`

## 11. Mono-Black Midrange

**Their plan.** Combine discard and efficient black threats with removal and graveyard-derived value;
current August results show the archetype repeatedly posting 5-0 finishes, though the fetched
aggregator page does not establish one stable list [ecp-goldfish-meta]{1}.

**Our counter-plan.** Go wide and avoid trading a premium engine for a generic discard flashback.
Swords the threat that dominates combat or accrues recurring value. Bombardment and Ajani are the
best ways to make their removal inefficient.

**Mulligan shift.** Keep redundant threats and stable mana. Ship single-engine hands that fold to
one Thoughtseize/removal spell.

**Therapy names.** Because the shell is not stable in the fetched evidence, avoid a rote blind name.
After seeing one card, target the duplicated removal spell, sweeper, or top-end engine.

**Board:** **no change** by default. If game one reveals Reanimate/Overlord as a central engine,
**+2 Surgical; -2 Cabal Therapy** is a narrow contingent plan; do not bring four Leylines for incidental
graveyard value. `{inferred: adapted}`

## Disconfirming analysis

- The sideboard's lack of Ending/blasts means the Showcase finalist's attractive fair-matchup swaps
  cannot be reproduced. Searching every registered sideboard card against each opposing engine
  disconfirmed the tempting practice of “boarding something in”: Izzet, Boros, Mardu, and generic
  Mono-Black are better served by the maindeck sixty [ecp-exact-75]{1}.
- Dimir can overturn our card-advantage thesis with Murktide/Barrowgoyf, transformed Tamiyo/Kaito,
  or Massacre. Those cards are all present in the current archetype frequencies
  [ecp-dimir-tempo]{1}; therefore the matchup should not be described as automatically favorable.
- Aggregators disagree materially on archetype shares and labels: MTGDecks reports Dimir 9.51%,
  while MTGGoldfish reports 11.9%; one calls the red tempo deck Izzet Cutter and the other Izzet
  Delver [ecp-mtgdecks-meta]{1} [ecp-goldfish-meta]{1}. The guidance keys off observed cards, not
  the label.
- Null Rod versus Izzet was tested as a hypothesis and rejected for the baseline: stopping Bauble
  is too narrow, and Rod does not stop Cutter's triggered ability. It becomes defensible only when
  additional activated artifacts are observed. `{inferred: rules application}`

## Contradictions

| Relationship | Positions | Operational treatment |
|---|---|---|
| tension | MTGDecks places UW Blink at 4.40% and Azorius Tempo outside its named top twenty, while MTGGoldfish places Azorius Tempo at 4.8% and separately lists Azorius Control [ecp-mtgdecks-meta]{1} [ecp-goldfish-meta]{1}. | Identify Phelia/blink versus Stifle/Daze versus Wrath before boarding. |
| qualifies | Giggs recommends trimming discard for fair-matchup blasts/removal, but the registered sideboard has none [ecp-giggs-guide]{1} [ecp-exact-75]{1}. | Trim discard only for Conqueror/Priest when those cards attack observed engines; otherwise keep sixty. |
| tension | Giggs calls Dimir a good matchup, while the current Dimir page shows post-board Massacre and large threats that can reverse token advantage [ecp-giggs-guide]{1} [ecp-dimir-tempo]{1}. | Treat Energy as structurally advantaged in exchanges, not guaranteed to win; preserve answers and diversify threats. |

## Revisit if

- The registered sideboard changes, especially if blasts, Ending, Meltdown, or extra removal enter.
- A ban or new set changes the prevalence of Dimir, Cutter, UW Blink, or Lands.
- “UW Blink,” “Azorius Tempo,” and “Azorius Control” converge under a stable list; their Priest and
  Swords cuts are currently card-configuration dependent.
- Testing shows Conqueror is too slow against Dimir or Cradle; those are the least source-direct
  swaps.
- The expected Death & Taxes build is known to be Vial-less; Null Rod loses much of its purpose.

## Acquisition candidates

- The Giggs guide links its exact Showcase deck page and is the best fetched lead for match logs or
  pilot video that could validate play/draw changes [ecp-giggs-guide]{1}.
- MTGGoldfish archetype pages link recent August 2026 event lists; acquiring a fixed sample of those
  lists would distinguish UW Blink/Tempo/Control configurations and quantify Massacre, Wrath, Vial,
  and Sphere prevalence [ecp-dimir-tempo]{1} [ecp-goldfish-meta]{1}.
- The MTGGoldfish metagame page names MTGO as the source for recent Challenge decklists; the linked
  event pages are candidates for exact opposing 75s rather than aggregate frequencies
  [ecp-goldfish-meta]{1}.

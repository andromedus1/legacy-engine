---
description: Cross-specialist synthesis supporting the comprehensive Energy Cabal Therapy primer.
type: research
summary: Exact-75 play guidance and balanced sideboard plans for the current Legacy field.
updated: 2026-08-03
provenance: agent-synthesis
decisions:
  - Cover the convergent leading field across project and external snapshots while keying plans to observed cards.
  - Treat exact sideboard maps as synthesized starting configurations, with visible build and play-draw branches.
key_findings:
  - The deck is proactive creature-engine aggro with discard, not a prison deck.
  - Its narrow sideboard warrants intentional no-change plans in several fair matchups.
  - Symmetric hate creates important sequencing costs with Raptor, Ajani, Guide, Leyline, and Surgical.
---

# Energy Cabal Therapy primer — campaign synthesis

## Decision result

The exact list is a 60-card proactive engine shell with 25 creatures, seven discard spells, four
Swords, two Bombardments, and 22 lands; the sideboard is concentrated on graveyards, spell chains,
uncast creature entry, and activated artifacts.[ecp-exact-list]{1} {inferred: cross-synthesis} Its
coherent identity is disruptive aggro: create a fast creature clock, buy turns with hand/mana
interaction, and convert disposable bodies into Therapy or Bombardment value. It should not keep
hate-only hands or dilute the main deck in fair matchups merely to make sideboard changes.

The mixed post-May project snapshot begins Tron, Show and Tell, Izzet Delver, Energy, Dimir Tempo,
and Doomsday and continues through 24 archetypes above 0.9%.[ecp-current-corpus]{2} The player-facing
primer covers that leading field while combining closely related public aliases and branching on
observed engine cards where an umbrella label conceals sideboard-relevant builds.

## Pilot synthesis

Guide into Ocelot converts Ocelot's entry into lifegain and an end-step Cat; Ajani converts Cat
death into a planeswalker; Voice's temporary Warriors can pay Therapy after combat; and Raptor can
pay for every main-deck nonland hit by mana value.[ecp-scryfall-oracle]{1}[ecp-scryfall-oracle]{3}
[ecp-scryfall-oracle]{5}[ecp-exact-list]{3} Casting legality still qualifies Raptor's reliability:
Swords requires a target, and Deafening Silence can prohibit a second noncreature spell.
[ecp-scryfall-oracle]{26}

{inferred: cross-synthesis} Mulligan decisions should test mana, turn-one action, follow-through,
and role balance. Fast-combo hands need immediate interaction plus pressure; tempo hands need stable
colored mana; creature hands need board presence plus removal; control hands need layered engines.
Therapy should follow revealed information whenever possible, then observed action, then the exact
card that defeats the intended line. A blind archetype-default name is reserved for no-read cases.

## Sideboard synthesis

The fair lane independently found that several matchups—especially Izzet, the Energy mirror,
Eldrazi, and generic black midrange—have no honest generic upgrade in this registered sideboard.
[ecp-exact-75]{1} The unfair lane found the opposite: graveyard and spell-combo matchups justify
large transformations, provided a creature clock remains.[ecp-unfair-current-lists]{2}
[ecp-unfair-current-lists]{4}

Four constraints govern the final maps:

1. Priest stops only nontoken creatures entering without being cast, so it catches reanimation and
   a pre-existing Show and Tell line but not Aluren-cast creatures; it also catches this deck's own
   transforming Ajani.[ecp-unfair-oracle]{2}[ecp-scryfall-oracle]{27}
2. Conqueror is symmetric and turns off Guide and transformed Ajani activations.
   [ecp-scryfall-oracle]{21}
3. Leyline can remove the target Surgical needs, making the six-card graveyard package layered but
   tactically non-additive.[ecp-scryfall-oracle]{28}
4. Null Rod and Conqueror stop activated artifact abilities, not static or triggered engines such
   as Forge casting, Painter color-setting, or Fleshraker triggers.[ecp-unfair-oracle]{1}

The complete player-facing artifact is `decks/energy-cabal-therapy-moxfield-primer.md`. It contains
23 matchup sections with the opponent's plan, our counter-plan, Therapy guidance where useful, and
balanced baseline exchanges. Matchups whose representative configurations materially alter the
exchange also carry observed-build or play/draw branches.

## Contradictions

- **Taxonomy — `qualifies`:** the project corpus uses the umbrella Blue Artifacts label,
  [ecp-current-corpus]{4} while its representative current list is specifically a Force/Emry/Kappa
  shell.[ecp-unfair-current-lists]{3} Matchup guidance branches on cards seen rather than extending
  one representative to the entire label.
- **Dredge label — `contradicts`:** a newest corpus row labeled Dredge is actually a Goryo's/
  Reanimate shell without the Dredge engine.[ecp-unfair-current-lists]{8} The guide uses only a
  Grave-Troll-verified representative.
- **Aluren — `qualifies`:** current representatives can include a complete Show and Tell package,
  while pure Aluren casts its loop creatures.[ecp-unfair-current-lists]{6}[ecp-unfair-oracle]{5}
  Priest is therefore conditional on the alternative-entry build.

## Disconfirming analysis

Oracle review disconfirmed the tempting claims that Raptor never misses, Priest is generic Aluren
hate, Leyline alone solves current Reanimator, or Rod shuts down artifact decks completely.
[ecp-scryfall-oracle]{26}[ecp-unfair-oracle]{5}[ecp-unfair-current-lists]{4}
[ecp-unfair-oracle]{1} Representative-list review also disconfirmed using a taxonomy label without
checking cards, most sharply in the mislabeled Dredge row.[ecp-unfair-current-lists]{8}

## Revisit if

- The 75 changes, especially by adding generic fair-matchup interaction.
- A ban, major release, or the 2026-08-17 TTL changes the field.
- Local paper expectations identify a precise Aluren, Blue Artifacts, Show and Tell, or Azorius
  branch.
- Match logs show the three-mana Conqueror plans are consistently too slow on the draw.

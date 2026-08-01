---
source_handle: card-semantics-ir-forge-script
fetched: 2026-07-31
source_url: https://raw.githubusercontent.com/Card-Forge/forge/master/forge-gui/res/cardsfolder/f/force_of_negation.txt
provenance: source-direct
source_class: standard
---

# Forge card script — force_of_negation.txt (Card-Forge/forge)

## Summary

Forge (the open-source MTG rules engine) implements every supported card as a plain-text
script in `res/cardsfolder/` — a per-card capability DSL rather than Java code. The Force of
Negation script demonstrates the shape: an `S:` static line declaring `Mode$ AlternativeCost`
with a typed cost (`Cost$ ExileFromHand<1/Card.Blue+Other>`) and condition
(`Condition$ NotPlayerTurn`), plus an `A:SP$ Counter` effect line with a typed target filter
(`ValidTgts$ Card.nonCreature`) and replacement destination (`Destination$ Exile`). The
takeaway for IR design: a mature project chose *typed effect predicates with parameters*
(effect API name + `Key$ Value` parameters), maintained per card as reviewable text data —
not a natural-language grammar and not per-card general-purpose code. The repository is
licensed GPL-3.0 (attested separately), which permits reading the format as prior art but
makes importing script content into non-GPL code a licensing decision.

## Key passages

> S:Mode$ AlternativeCost | ValidSA$ Spell.Self | EffectZone$ All | Cost$
> ExileFromHand<1/Card.Blue+Other> | Condition$ NotPlayerTurn | Description$ If it's not your
> turn, you may exile a blue card from your hand rather than pay this spell's mana cost.
> — force_of_negation.txt, S: line

> A:SP$ Counter | TargetType$ Spell | TgtPrompt$ Select target noncreature spell | ValidTgts$
> Card.nonCreature | Destination$ Exile | SpellDescription$ Counter target noncreature spell.
> If that spell is countered this way, exile it instead of putting it into its owner's
> graveyard. | StackDescription$ SpellDescription — force_of_negation.txt, A: line

> Name:Force of Negation / ManaCost:1 U U / Types:Instant — force_of_negation.txt, header lines

## Structural metadata

Plain-text card script; line-keyed format (Name/ManaCost/Types/S:/A:/Oracle). The `Oracle:`
line carries the verbatim oracle text alongside the machine representation, keeping script
and source text reviewable together. Format documented in the Card-Forge wiki
("Card scripting API": https://github.com/Card-Forge/forge/wiki/Card-scripting-API).

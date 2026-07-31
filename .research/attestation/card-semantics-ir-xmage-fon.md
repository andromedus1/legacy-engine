---
source_handle: card-semantics-ir-xmage-fon
fetched: 2026-07-31
source_url: https://raw.githubusercontent.com/magefree/mage/master/Mage.Sets/src/mage/cards/f/ForceOfNegation.java
provenance: source-direct
source_class: standard
---

# XMage card implementation — ForceOfNegation.java (magefree/mage)

## Summary

XMage implements each card as a Java class composing reusable ability/effect/cost objects
from its engine library: Force of Negation is built from `AlternativeCostSourceAbility(new
ExileFromHandCost(...), NotMyTurnCondition.instance, ...)` plus a
`CounterTargetWithReplacementEffect(PutCards.EXILED)` with a
`TargetSpell(StaticFilters.FILTER_SPELL_NON_CREATURE)`. The oracle text appears as comments
above each ability, tying code to source text. The design lesson mirrors Forge's: a mature
rules project models card semantics as a *closed library of parameterized capability
components* (named cost types, condition singletons, effect classes, typed target filters)
composed per card — the vocabulary of components is the semantic layer; per-card artifacts
just instantiate it. GitHub's license API reports magefree/mage as MIT (spdx_id "MIT",
license file at Mage repo root LICENSE.txt), so XMage is permissively usable as a
cross-validation reference.

## Key passages

> // If it's not your turn, you may exile a blue card from your hand rather than pay this
> spell's mana cost.
> this.addAbility(new AlternativeCostSourceAbility(
>     new ExileFromHandCost(new TargetCardInHand(filter)), NotMyTurnCondition.instance, ...
> — ForceOfNegation.java, constructor

> // Counter target noncreature spell. If that spell is countered this way, exile it instead
> of putting it into its owner's graveyard.
> this.getSpellAbility().addEffect(new CounterTargetWithReplacementEffect(PutCards.EXILED));
> this.getSpellAbility().addTarget(new TargetSpell(StaticFilters.FILTER_SPELL_NON_CREATURE));
> — ForceOfNegation.java, constructor

> License check: GET https://api.github.com/repos/magefree/mage/license returns "spdx_id":
> "MIT", "html_url": "https://github.com/magefree/mage/blob/master/LICENSE.txt"
> — GitHub license API observation, 2026-07-31

## Structural metadata

Java source file under `Mage.Sets/src/mage/cards/f/`; one class per card extending
`CardImpl`; filter statics declared at class level; oracle text carried as comments adjacent
to the implementing ability composition.

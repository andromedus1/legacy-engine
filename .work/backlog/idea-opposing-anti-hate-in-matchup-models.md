---
id: idea-opposing-anti-hate-in-matchup-models
created: 2026-08-04
tags: [analysis, advisory, sideboard]
---

The sideboard scorer models **our** anti-hate (cards that protect our hate from theirs)
but has no notion that an **opponent's** maindeck card can blank a whole axis of our
deck. That asymmetry hides real matchups.

Concrete live case (2026-08-04). Black Saga Storm is **6.5% of the current Boulder
field** and runs **Veil of Summer at 3.24 average copies in 49 of 59 current-regime
lists**:

> **Veil of Summer** {G} Instant — "Draw a card if an opponent has cast a blue or black
> spell this turn. Spells you control can't be countered this turn. You and permanents
> you control gain hexproof from blue and from black until end of turn."

For one green mana that blanks Thoughtseize, Cabal Therapy, and Orcish Bowmasters'
targeting — the entire black splash that is the *reason* to play Energy Cabal Therapy
over Boros Energy — and draws them a card for doing it. Energy's record against that
archetype is **n=2**, so the interaction is statistically invisible: the engine cannot
see it, and neither can a pilot reading the cells.

What this needs is the mirror of the existing anti-hate axis in `advisory/impact.py`:
an **opposing-blank** relation on the hoser catalog. For a candidate hate/disruption
card, ask whether the modelled opponent's maindeck contains a card that neutralizes its
attack axis at meaningful copy count, and discount `centrality` accordingly (with a
labelled audit line, per the divergence-as-diagnostic pattern — surface the conflict,
never silently rescore).

Starter relations worth cataloguing, all one-sided and high-copy in their homes:

- Veil of Summer → blanks targeted black/blue disruption (discard, Bowmasters ping,
  targeted removal, counterspells) for {G}
- Boseiju, Who Endures → our enchantment/artifact hate
- Force of Vigor → our Leyline/Rest in Peace/Null Rod
- Pact of Negation / Veil → our combo hate generally
- Harbinger of the Seas → symmetric, hits our own nonbasics too (already a known trap
  in the Dimir primer)

Payoff: this is the class of finding that makes a deck look flawless in the data and
lose in the room. It pairs with `feature-camp-floor-observability-banner` — one covers
"the cell is unobserved", this covers "the cell is observed but the mechanism is
invisible".

---
id: idea-granular-effect-tagging
created: 2026-06-22
tags: [tagging, advisory]
---

Improve legacy-engine's decision-making by doing a deep-dive on the card effect tagging we have today and making it more granular — the hypothesis is that finer, more detailed effect tags would give the engine greater nuance (especially around graveyard effects and their interactions) and lead to better-informed advice.

**Two concrete directions the user raised:**

1. **More granular graveyard tagging.** The current tags are too coarse to capture how a card interacts with the graveyard and with other cards. Finer-grained graveyard effect tags would let the engine reason about graveyard synergies/anti-synergies instead of treating "graveyard hate" as a monolith.

2. **Symmetry flag for game-wide effects.** Add a tag indicating whether a game-wide effect is **asymmetric** (affects only the opponent) or **symmetric** (affects everyone, including the controller). This lets the engine catch self-hosing recommendations.

**Motivating example (from the Flow State / Dimir Tempo data dive, 2026-06-22):**
Grafdigger's Cage was treated as a fine sideboard card for Dimir Tempo. But the post-Flow-State version of the archetype now leans on its *own* graveyard — Nethergoyf, plus Flow State's "instant **and** sorcery in your graveyard → draw 2" payoff. Grafdigger's Cage is a *symmetric* graveyard-hate effect, so it hoses the deck's own plan. The real-world data backs this: as Flow State adoption hit ~100%, Cage dropped from ~47% to ~20% sideboard inclusion and graveyard hate shifted toward Nihil Spellbomb. The engine, with today's tagging, lacked the nuance to flag Cage as self-hosing for this deck.

The bet: granular graveyard tags + a symmetry (asymmetric/symmetric) flag would let the engine catch this whole class of mistake.

---
id: idea-archetype-id-trainer
created: 2026-06-15
tags: []
---

A live archetype-ID trainer / "name that deck" coach. The player feeds in the cards
an opponent has played so far during a game; the system predicts the opponent's deck
archetype from that partial card sequence, driven by the engine's existing archetype
knowledge.

Intended use: by the player (Andrew) while playing, to train himself to correctly ID
opponent decks faster and earlier in a game.

Raw notes on possible shape (not binding):
- Progressive prediction — refine the archetype guess as more cards are revealed.
- Training/coaching angle: compare the player's own guess against the model's, surface
  which revealed cards were the strongest signal, reward earlier correct IDs.

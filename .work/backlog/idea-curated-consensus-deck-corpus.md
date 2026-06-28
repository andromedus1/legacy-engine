---
id: idea-curated-consensus-deck-corpus
created: 2026-06-27
tags: [analytics, knowledge, roadmap]
---

**Build out the full set of global consensus (ban-regime-aware) decklists, ordered by
meta share, with a primer for each — then leverage that curated corpus across the
engine's analyses.**

The vision: a maintained library of "the deck" for every meaningful archetype in the
current ban regime, so analyses can run against *actual curated decklists* instead of
only the archetype-level matchup matrix. Gives deep, format-wide understanding and a
much richer substrate for advisory output.

Arcs (raw notes — not a binding decomposition):

- **Generate + curate the lists.** Walk archetypes in descending meta share; for each,
  emit the current-regime consensus list via the existing `generate consensus` (already
  ban-regime-aware) and curate/sanity-check it. Tier by sample (some archetypes will be
  speculative — flag, don't fake). Keep them regime-aware and refresh when the regime
  rolls.
- **Write a primer per deck.** Same shape as the Dimir Tempo / Doomsday Tempo primers
  (`decks/*-moxfield-primer.md`): gameplan, card choices, matchup + sideboard guide,
  mulligan/play tips, honesty gates. This is the curated-knowledge layer.
- **Leverage the corpus in analyses.** Today the matchup matrix is archetype-level and
  positioning runs on archetype rows. With curated lists we could: doctor any user deck
  against the real consensus list (not just copy-count modes), run list-level positioning,
  reason about specific card interactions across the field, and ground advisory text in
  actual cards. Possibly feed the corpus back as a knowledge index the engine/agents read.
- **Ban / unban speculation.** With curated lists + the field model, speculate on what
  banning or unbanning a given card would do — which decks weaken/disappear, which rise,
  how the field re-shapes. Connects to the existing `report speculate` (pre-data forecast)
  and `report affectedness` (which bans drove an archetype's valid_since); this would
  extend that to forward-looking "what if X were banned/unbanned" across the whole field.

Why it matters: turns the engine from archetype-share + matchup-matrix reasoning into a
deck-aware system with curated ground truth — the foundation for everything from deck
doctoring to meta forecasting. Pairs with the honesty discipline in the methodology memory
(every consensus list carries its sample tier + regime currency).

Related: the curated-knowledge / live-meta ideas already parked (idea-live-meta-knowledge-system,
idea-user-profile-memory), and the consensus generator + affectedness/speculate tooling
that already exist.

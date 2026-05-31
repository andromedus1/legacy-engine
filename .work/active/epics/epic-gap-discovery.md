---
id: epic-gap-discovery
kind: epic
stage: drafting
tags: [generation, discovery]
parent: null
depends_on: [epic-deck-generation]
release_binding: null
gate_origin: null
created: 2026-05-31
updated: 2026-05-31
---

# Gap Discovery (deck generation mode 3)

## Brief

The deferred **mode 3** of the Deck Generation pillar (split out of `epic-deck-generation`, which shipped
consensus + export + field-tuning). Two halves:

- **Archetype-gaps** — surface archetypes with high positioning `S` (well-positioned vs the field) but low
  meta-share: under-explored shells the field is sleeping on. Consumes `advisory/positioning` + `metashare`.
- **Card-gaps / adjacent-card discovery** — let the tuner consider cards the deck does NOT already run:
  role/color/CMC/synergy-**adjacent** candidates that are under- or un-played in this shell but have proven
  value. This turns "tuning" (bounded to the archetype's observed pool) toward "discovery" — the
  differentiator. Promoted from `idea-tuning-adjacent-card-discovery` (2026-05-30).

**What this session unblocked:** the per-card×matchup win-rate extension (`analytics/card_value`,
`compute_card_winrates`) shipped in `epic-deck-generation`, removing the hard data blocker the original idea
cited. Adjacent candidates can now be scored by **cross-archetype** per-card value (a card proven vs threat M
in *other* decks → transfer it here), confidence-gated. The remaining unknowns are an **adjacency model**
(what makes a card a candidate) and **validating exploratory candidates** (where the eventual
`epic-goldfish-simulation` pillar adds a confidence layer — not a hard blocker for a confidence-gated v1).

## Why `[needs-brief]`
The adjacency model is a genuine research question (card-similarity / deckbuilding-recommender prior art +
how to transfer per-card value across archetype contexts + confidence-gating exploratory picks). Write the
brief before `/epic-design`. Brief topic queued: **card-level adjacency & discovery for deck tuning**.

## Anticipated child features (sketch — realized at /epic-design after the brief)
- `archetype-gap-finder` — high-S / low-share surfacing (positioning × metashare).
- `card-adjacency-model` — role/color/CMC/synergy adjacency over the card pool (heuristic first;
  embedding/co-occurrence later) grounded in existing card tags + `card_value`.
- `discovery-tuning` — extend `generation/tuning` candidate pool to gate-clearing cross-field-valued adjacent
  cards (confidence-gated; bounded v1 needs no goldfish).
- (later) `goldfish-validated-candidates` — once `epic-goldfish-simulation` exists, validate exploratory picks.

## Foundation references
- `docs/briefs/deck-generation-and-moxfield.md` §2.2 (mode 3 card-gaps).
- `epic-deck-generation` (the shipped consensus/export/tuning + per-card-value + maindeck-aware sideboard it
  builds on), `epic-goldfish-simulation` (later validation layer).
- Related backlog/notes: this epic supersedes `idea-tuning-adjacent-card-discovery`.

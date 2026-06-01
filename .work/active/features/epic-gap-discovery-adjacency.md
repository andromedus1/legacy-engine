---
id: epic-gap-discovery-adjacency
kind: feature
stage: drafting
tags: [generation, discovery]
parent: epic-gap-discovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Card-Adjacency Model (candidate nomination)

## Brief

The nomination engine for card-level discovery: given a shell `D` (archetype `A`, color
identity `C(D)`), produce the set of cards the deck does **not** already run but that are
plausible swap-in candidates. Per the brief's v1 recommendation, a card `X` is a candidate
when ALL hold: (1) not already in `D`; (2) color-legal (`X.colors ⊆ C(D)`, front-face colors
via the layout-aware card rows); (3) role-relevant (`_card_roles(X)` intersects the roles the
shell's flexible slots want); (4) within the shell's flexible-slot CMC band. Survivors are
then **ranked by decklist co-occurrence lift** — PMI of `X` against the archetype's locked
core over the corpus (`deck_cards`, 63k decks), the auditable heuristic analogue of card2vec.

Delivered as a new `src/legacy_engine/generation/discovery.py` module, kept deliberately
**out of `tuning.py`** (tuning stays the proven-swap engine; discovery composes alongside it).
It reuses, does not rebuild: `advisory/whattoplay._card_roles` (role classifier),
`card_tags` (staple roles + mana-base tags), `models/card.Card` colors/cmc/type_line, and a
`deck_cards` co-occurrence query (mirroring `generation/consensus.card_frequencies`). All
corpus stats use the tuner's window (latest ban regime).

Does NOT cover value scoring or confidence-gating of candidates — this feature only nominates
and ranks by adjacency/co-occurrence. The evidence layer (cross-archetype per-card value
transfer + the honest confidence gate + the CLI surface) is `epic-gap-discovery-discovery-tuning`,
which consumes this feature's candidate list.

## Epic context

- Parent epic: `epic-gap-discovery`
- Position in epic: foundation feature — `epic-gap-discovery-discovery-tuning` depends on the
  candidate-nomination types/output this feature defines.

## Inherited design decisions

- **Module placement = new `generation/discovery.py`**, separate from `tuning.py`.
- **Adjacency v1 = role-match ∩ color-legal ∩ CMC-band, RANKED by decklist co-occurrence (PMI)** —
  embeddings (card2vec / oracle-text sentence-transformers) are a documented later upgrade,
  not a v1 dependency.
- **Reuse `_card_roles`** as the single role source (already feeds whattoplay/sideboard).
- **Windowing**: corpus co-occurrence uses the tuner's latest-ban-regime window; thread the
  same `since/until` and reuse one `CardWinRates`/frequency aggregate where the sibling needs it
  (per `fix-tuning-sideboard-winrate-reuse`).
- **Edge cases (from brief §Implementation Notes)**: candidate already in the sideboard (not
  maindeck) is still a valid discovery for the 60; multi-face → front-face rows; colorless
  always color-legal; no role match → excluded (no basis); never-paired cards (PMI undefined) →
  exclude, do not impute.

## Research briefs

- `docs/briefs/card-adjacency-and-discovery.md` §0 (reuse inventory), §1 (the adjacency model —
  the four gating conditions + the PMI rank).

## Foundation references

- `src/legacy_engine/advisory/whattoplay.py` — `_card_roles(card)` (oracle-text role classifier).
- `src/legacy_engine/card_tags.py` — `staple_role`, `mana_base_tags`.
- `src/legacy_engine/models/card.py` — `Card.colors`, `Card.cmc`, `Card.type_line` (layout-aware).
- `src/legacy_engine/generation/consensus.py` — `card_frequencies` + `_latest_regime_window`
  (the corpus query + windowing pattern to mirror for co-occurrence).

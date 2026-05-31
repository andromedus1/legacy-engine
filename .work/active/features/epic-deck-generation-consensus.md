---
id: epic-deck-generation-consensus
kind: feature
stage: drafting
tags: [generation]
parent: epic-deck-generation
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Consensus baseline deck generation

## Brief

Generate a faithful "what wins now" decklist for an archetype by aggregating the field: for each card,
inclusion-% across that archetype's decks in the target window × its modal count, greedily filling 60
maindeck + 15 sideboard. This is generation **mode 1** (the floor, pure data aggregation over existing
analytics — no advisory heuristics, so it ships independently of the tuning feature). Establishes the
net-new `src/legacy_engine/generation/` module seam and the `generate` CLI group that the tuning feature
extends.

The known mode-1 limitation must be handled here: modal-count greedy fill can over/undershoot 60 and
double-list flex cards across main/side — the generator **reconciles to a legal, exactly-60 maindeck +
≤15 sideboard, de-duped list**, validated via `ingestion/banlist.validate_deck` against the as-of-date ban
snapshot. Generates against the windowed latest ban-regime by default (overridable).

Does NOT cover field-tuning (mode 2) or gap-discovery (mode 3, deferred from this epic).

## Epic context
- Parent epic: `epic-deck-generation`
- Position in epic: foundation feature — establishes `generation/` + the `generate` CLI group; the
  field-tuning feature depends on it.

## Inherited design decisions
From the parent epic `## Design decisions` (fixed inputs):
- **Module seam**: net-new `src/legacy_engine/generation/` composing `analytics/` (`metashare` + `deck_cards`
  aggregates) + `ingestion/banlist`; CLI under a `generate` group.
- **Field default**: windowed latest ban-regime (reuse `trends` regime windowing); user-overridable.
- **Legality**: always `validate_deck` against the as-of-date ban snapshot; output must be exactly-60 + de-duped.
- Pure, offline, reproducible — zero network calls.

## Research briefs
- `docs/briefs/deck-generation-and-moxfield.md` §2.1–2.2 (mode 1), §2.4 (data-quality realities).
- `docs/briefs/advisory-methods.md` — the layers consumed.

## Foundation references
- `docs/ARCHITECTURE.md` — the deferred `generation/` seam.
- `src/legacy_engine/analytics/metashare.py`, `deck_cards` aggregates; `src/legacy_engine/ingestion/banlist.py`.

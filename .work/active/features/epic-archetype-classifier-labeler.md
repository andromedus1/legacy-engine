---
id: epic-archetype-classifier-labeler
kind: feature
stage: drafting
tags: [archetype]
parent: epic-archetype-classifier
depends_on: [epic-archetype-classifier-matcher]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Labeler + `legacy label` CLI

## Brief
Orchestrate end-to-end labeling: read each deck from DuckDB (`decks` + `deck_cards`), resolve card
names to `Card`s via the Scryfall index, compute deck colors, `classify` against the loaded ruleset,
and persist the resulting archetype label into `decks.archetype` (the column foundations left NULL).
Wire the `legacy label` CLI. Conflict/Unknown labels are written raw. Idempotent (re-labeling
overwrites). Does NOT compute meta-share/matchups (analytics epic) — it only populates the archetype
column those will read.

## Epic context
- Parent epic: `epic-archetype-classifier`. The integration feature — ties rules-loader + matcher + the foundations card/store layers into `legacy label`.

## Inherited design decisions
- Conflict/Unknown written raw to `decks.archetype`.
- Reuse foundations: ScryfallClient index for name→Card, `compute_deck_colors`, the DuckDB store.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/parent.md` — the end-to-end pipeline (resolve → colors → classify → persist).
- `docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md` — name→Card resolution + the color helper.

## Foundation references
- `docs/ARCHITECTURE.md` — `archetype/labeler.py`; the `legacy label` CLI; `decks.archetype` column.

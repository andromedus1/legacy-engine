---
id: epic-foundations-card-data-card-model-scryfall
kind: feature
stage: drafting
tags: [ingestion]
parent: epic-foundations-card-data
depends_on: [epic-foundations-card-data-package-skeleton]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Card Model & Scryfall Ingestion

## Brief

The typed `Card` Pydantic model and the Scryfall ingestion that produces it. Port edh-engine's
`ingestion/scryfall.py` (~214 lines — verified to contain `download_bulk_data`, `load_card_index`,
`_batch_lookup`, `normalize_name`, `resolve_card_pool`) and adapt it for Legacy: download the
`oracle_cards` bulk, index the **whole** oracle pool by name + each split/DFC/adventure face name
(O(1) name→card, the classifier's hot path), with the `/cards/collection` batch fallback. Resolve raw
Scryfall JSON into the canonical `Card` model.

The `Card` model carries identity (name, mana_cost, cmc, type_line, layout, card_faces), the raw color
inputs the classifier needs (`colors`, `produced_mana`), and `legalities.legacy` — but legality is
authoritatively validated against the ban-list blacklist (sibling feature), not this field. Derived
Legacy fields (deck-color helper, is_free_spell, staple_role, mana-base tags) are layered in the
`card-derivations` sibling. Does NOT include the DuckDB cards table (that's `duckdb-store`) or the
ban-list.

## Epic context
- Parent epic: `epic-foundations-card-data`
- Position in epic: produces the `Card` model + in-memory name index that `card-derivations`, `duckdb-store`, and (later) the archetype classifier all consume.

## Inherited design decisions
- **Card model = typed Pydantic** (canonical representation; resolve raw JSON → Card).
- **Card storage = both** — this feature owns the in-memory name index (primary resolution path); the DuckDB `cards` table is materialized by the `duckdb-store` sibling.
- **Scryfall ADR = extend, don't fork** edh-engine's scryfall.py; index the whole pool, resolve on demand (no fixed `card_pool.json` subset).

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md` — the exact fields, the whole-pool indexing, split/DFC/adventure face handling, oracle_cards bulk, batch fallback, the Card model shape.
- `docs/briefs/legacy-foundations.md` — the deck-as-data card model.

## Foundation references
- `docs/ARCHITECTURE.md` — `ingestion/scryfall.py`, `models/Card`.
- edh-engine port source: `/Users/<user>/dev/edh-engine/src/edh_engine/ingestion/scryfall.py`.

## Decomposition risks
- **Card model scope creep** — model only the fields the contract brief names (identity, colors, produced_mana, type_line, layout, card_faces, legalities), not all of Scryfall. Resist over-modeling.

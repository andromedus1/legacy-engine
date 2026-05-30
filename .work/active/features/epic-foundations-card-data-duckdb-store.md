---
id: epic-foundations-card-data-duckdb-store
kind: feature
stage: drafting
tags: [ingestion]
parent: epic-foundations-card-data
depends_on: [epic-foundations-card-data-card-model-scryfall]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# DuckDB Analytical Store

## Brief

Stand up the embedded DuckDB analytical store (`data/legacy.duckdb`) and its access layer — the
rebuildable derived cache that analytics/ and advisory/ will query. This feature scaffolds the schema
(the `cards` table now; the tournament-data tables — tournaments, decks, deck_cards, rounds,
standings, archetype_labels — declared as the schema the next epic fills), materializes the `cards`
table from the resolved card index, and establishes the store access pattern (connection management,
load/upsert helpers, and the **rebuildable-from-raw guarantee**: deleting the DB loses no source data
since raw JSON + pinned SHAs are the source of truth).

Decided storage shape: in-memory name index remains the hot-path card lookup; this `cards` table
serves relational joins (`deck_cards ↔ cards` for color/type queries in analytics). Does NOT load
tournament data (that's the tournament-ingestion epic) — it only defines the schema and proves the
cards round-trip.

## Epic context
- Parent epic: `epic-foundations-card-data`
- Position in epic: consumer of `card-model-scryfall` (needs the Card shape for the cards-table schema); parallelizable with `card-derivations`. Establishes the **DuckDB access pattern** every later analytics/advisory query inherits.

## Inherited design decisions
- **Storage = DuckDB** (confirmed): embedded, column-oriented, rebuildable derived cache over raw-JSON source of truth. Keeps the "no server" property.
- **Card storage = both** — this feature owns the materialized `cards` table; the in-memory index lives in `card-model-scryfall`.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — the DuckDB tables the analytics layer needs (rounds/standings for matchups), mirror-and-decouple, rebuildable cache.
- `docs/ARCHITECTURE.md` — the storage decision + data-flow (raw JSON → DuckDB), the DuckDB table list.

## Foundation references
- `docs/ARCHITECTURE.md` — `ingestion/store.py`, the `data/legacy.duckdb` schema, the storage open-question disposition.
- `docs/PRINCIPLES.md` — reproducibility (raw is source of truth; DuckDB derived/rebuildable).

## Decomposition risks
- **Schema-now-vs-later** — declaring tournament-data tables this feature doesn't populate risks drift with the tournament-ingestion epic. Mitigate: define only the `cards` table fully now; sketch the others as forward-declared DDL the next epic owns and may revise.

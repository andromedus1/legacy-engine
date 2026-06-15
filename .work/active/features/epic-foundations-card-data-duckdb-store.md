---
id: epic-foundations-card-data-duckdb-store
kind: feature
stage: done
tags: [ingestion]
parent: epic-foundations-card-data
depends_on: [epic-foundations-card-data-card-model-scryfall]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
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

## Architectural choice (autopilot, judgment)
Module at `src/legacy_engine/ingestion/store.py` (per ARCHITECTURE.md). Define ONLY the `cards` table
fully now; do NOT forward-declare the tournament tables (avoids drift — the tournament-ingestion epic
owns their exact shape). Store list fields (`colors`, `produced_mana`) as compact WUBRG-joined strings
(join-friendly, e.g. `"UB"`) rather than DuckDB LIST, since analytics joins key on type/color presence.
`name` is the primary key; `INSERT OR REPLACE` makes `load_cards` idempotent. A thin functional API
(connect / init_schema / load_cards / fetch_card / rebuild) — the SQL access pattern the analytics and
advisory epics inherit. Rebuildable: `rebuild` drops + recreates from the in-memory index, raw bulk
remains source of truth.

## Implementation Units

### Unit 1: `src/legacy_engine/ingestion/store.py`
```python
CARDS_DDL = """CREATE TABLE IF NOT EXISTS cards (
    name VARCHAR PRIMARY KEY, mana_cost VARCHAR, cmc DOUBLE, type_line VARCHAR,
    colors VARCHAR, produced_mana VARCHAR, oracle_text VARCHAR, layout VARCHAR, is_land BOOLEAN
)"""

def connect(path: Path | str = DUCKDB_PATH) -> duckdb.DuckDBPyConnection: ...  # mkdir parent unless :memory:
def init_schema(con) -> None: ...                 # idempotent CREATE TABLE IF NOT EXISTS
def load_cards(con, cards: Iterable[Card]) -> int: ...  # INSERT OR REPLACE; returns count
def fetch_card(con, name) -> dict | None: ...     # SELECT by name
def rebuild(con) -> None: ...                     # DROP + recreate cards
```
**Acceptance**: `init_schema` is idempotent; `load_cards` inserts and is idempotent on `name` (re-load → no dup, fields updated); `fetch_card` returns the row; `rebuild` clears; list fields stored as joined strings (`"UB"`).

### Unit 2: Wire `seed cards` to materialize the cards table
After building the index, `init_schema` + `load_cards` over the resolved pool so the DuckDB `cards`
table is populated alongside the in-memory index (the dual-storage decision).
**Acceptance**: `seed cards` reports both the indexed name count and the rows loaded into DuckDB.

## Testing
- `tests/test_store.py` — use a temp DuckDB file (or `:memory:`): schema idempotency; `load_cards` insert + idempotent re-load (count stable, fields updated); `fetch_card` hit/miss; `rebuild` empties; list→string round-trip. Deterministic, no network.

## Implementation notes
- **Files created**: `src/legacy_engine/ingestion/store.py` (connect/init_schema/load_cards/fetch_card/rebuild + `CARDS_DDL`); updated `cli.py` `seed cards` to materialize the DuckDB `cards` table after building the index.
- **Tests added**: `tests/test_store.py` (in-memory DuckDB) — full suite **70 passing in 0.50s**.
- **Discrepancies from design**: none. Only the `cards` table is defined; tournament tables deferred to the tournament-ingestion epic (per the decomposition risk). List fields stored as WUBRG-joined strings; `INSERT OR REPLACE` keyed on `name` gives idempotent loads.
- **Adjacent issues parked**: none.

## Review (2026-05-29)
**Verdict**: Approve. **Blockers/Important**: none.
**Nits**: `connect()` returns a live connection the caller must close (tests use try/finally and `seed cards` does too); a context-manager wrapper could be added later for ergonomics. The cards table is the only schema — analytics/tournament tables arrive with their epics (intentional, drift-avoiding).
**Notes**: Establishes the DuckDB SQL access pattern for analytics/advisory. Rebuildable from raw (raw bulk is source of truth). 70 tests green.

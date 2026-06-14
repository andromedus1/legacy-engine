---
description: How to own a DuckDB table while keeping raw JSON as the source of truth. Read before adding a new persisted data domain (new table + new JSON source).
type: pattern
kind: planning
updated: 2026-06-13
summary: |
  Raw JSON files on disk are the source of truth; DuckDB tables are rebuildable derived caches.
  Every data domain that follows this split implements: (1) a JSON SSOT read/write module, (2)
  a DuckDB schema DDL, (3) a drop→schema→reload rebuild function that makes the table
  idempotently re-creatable from the JSON files alone. Deleting the .duckdb file loses no data.
decisions:
  - "Raw JSON is the source of truth: precious, user-authored or mirrored, git-friendly, hand-editable."
  - "DuckDB tables are derived: always rebuildable from the JSON SSOT without loss. Deleting data/legacy.duckdb loses nothing."
  - "Each domain owns exactly: one JSON SSOT path (constant in config.py), one DDL string, one init_*_schema, one load_* (idempotent INSERT OR REPLACE), and one rebuild_* (DROP + init + load)."
  - "rebuild_* is the clean-slate path (seed / first-run / corruption recovery). load_* is the incremental/idempotent path (refresh / re-run)."
  - "The rebuild function is intentionally destructive — it drops the table first — because DuckDB INSERT OR REPLACE cannot update column structure; only a full rebuild achieves schema migration."
---

# Pattern: JSON SSOT + Rebuildable DuckDB Table

Every data domain in legacy-engine follows the same split: raw JSON files on disk are the
source of truth; DuckDB tables are rebuildable derived caches purpose-built for SQL joins.

## The Split

```
data/<domain>/          ← JSON SSOT (precious; git-friendly; never auto-deleted)
  e.g. collection/inventory.json
       collection/decks/<id>.json
       scryfall/oracle_cards.json
       scryfall/default_cards.json

data/legacy.duckdb      ← derived cache (rebuildable; can be deleted without data loss)
  tables: cards, card_prices, tournaments, decks, deck_cards, rounds, standings,
          inventory_entries, user_decks, deck_versions, deck_version_cards
```

## The Four Functions per Domain

```python
# 1. Schema DDL (module-level constant)
CARDS_DDL = """CREATE TABLE IF NOT EXISTS cards (name TEXT PRIMARY KEY, ...)"""

# 2. init_*_schema — idempotent: CREATE TABLE IF NOT EXISTS
def init_schema(con):
    con.execute(CARDS_DDL)

# 3. load_* — idempotent INSERT OR REPLACE
def load_cards(con, cards: Iterable[Card]) -> int:
    con.executemany("INSERT OR REPLACE INTO cards (...) VALUES (...)", rows)
    return len(rows)

# 4. rebuild_* — clean-slate DROP + init + load
def rebuild(con):
    """Drop and recreate the cards table (raw JSON remains the source of truth)."""
    con.execute("DROP TABLE IF EXISTS cards")
    init_schema(con)
    # Caller invokes load_cards(...) next
```

## Three Canonical Instances

### 1. `ingestion/store.py` — tournament corpus tables (cards, card_prices)

- JSON SSOT: `data/scryfall/oracle_cards.json` (oracle bulk) and `data/scryfall/default_cards.json` (prices bulk)
- Rebuild: `rebuild(con)` (cards, line 318) and `rebuild_prices(con)` (card_prices, line 378)
- Load: `load_cards(con, cards)` and `load_prices(con, printings)`
- Incremental path: `load_cards_diff` for non-destructive release-aware refresh

### 2. `collection/store.py` — personal collection tables (inventory_entries, user_decks, deck_versions, deck_version_cards)

- JSON SSOT: `data/collection/inventory.json` and `data/collection/decks/<id>.json` (via `collection/persist.py`)
- Rebuild: `rebuild_collection(con)` (collection/store.py:202) — drops all four tables, recreates schema, reloads from JSON
- Load: `load_inventory(con, inventory)` / `upsert_user_deck(con, deck)`
- The `collection/persist.py` module owns the JSON read/write layer; `collection/store.py` owns the DuckDB layer

### 3. `ingestion/store.py` — tournament event tables (tournaments, decks, deck_cards, rounds, standings)

- JSON SSOT: `data/cache/**/*.json` (fbettega mirror)
- Load: `load_tournament(con, tr)` — idempotent per tournament (deletes child rows then re-inserts)
- No explicit full rebuild function: `rebuild(con)` recreates the base schema; `seed cache` re-ingests all events

## When to Add a New Domain

Follow this checklist:
1. Add a `data/<domain>/` path constant to `config.py`.
2. Write a `<domain>/persist.py` (or extend an existing one) for JSON read/write.
3. Add a `DDL` constant + `init_*_schema(con)` to the relevant `*store.py`.
4. Write `load_*(con, ...)` with `INSERT OR REPLACE` on the natural key.
5. Write `rebuild_*(con)` as `DROP TABLE IF EXISTS <t> → init → (caller calls load)`.
6. Add a `seed <domain>` and/or `collection rebuild` CLI command that calls `rebuild_*` + `load_*`.

## Common Violations

- Using `INSERT OR IGNORE` when `INSERT OR REPLACE` is needed — stale rows persist invisibly.
- Storing computed/derived values in the JSON SSOT — JSON is for raw inputs only; derived
  values belong in DuckDB (or in the Python computation layer).
- Not implementing `rebuild_*` — makes the table non-rebuildable and ties the schema to its
  creation-time DDL forever.
- Calling `rebuild_*` in the hot path (e.g. on every `advise` command) — `rebuild` is for
  `seed` and recovery only; analytics use `init_*_schema` (idempotent no-op when table exists).

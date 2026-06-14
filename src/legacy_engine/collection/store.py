"""DuckDB derived store for the collection layer.

Owns exactly four tables (never touches ``ingestion/store.py``'s tables):
  inventory_entries  — PK (owner, name, printing, condition, foil)
  user_decks         — PK id
  deck_versions      — PK id
  deck_version_cards — FK version_id

Raw JSON under ``data/collection/`` is the source of truth; these tables are a
rebuildable derived cache.  ``rebuild_collection()`` drops + reloads them from
the JSON files via ``collection/persist.py`` — deleting this DuckDB data loses
nothing (same guarantee as ``ingestion/store.py``).

Every table carries an ``owner`` column and every query filters on it, so the
multi-tenant migration is a value change (real user ids + the WHERE is already
present), not a schema migration.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from legacy_engine.config import DUCKDB_PATH, LOCAL_OWNER
from legacy_engine.models.collection import Inventory, UserDeck

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

INVENTORY_ENTRIES_DDL = """
CREATE TABLE IF NOT EXISTS inventory_entries (
    owner        VARCHAR NOT NULL,
    name         VARCHAR NOT NULL,
    printing     VARCHAR,
    condition_kw VARCHAR,
    foil         BOOLEAN NOT NULL DEFAULT false,
    count        INTEGER NOT NULL DEFAULT 1
)
"""
# NOTE: printing, condition_kw (condition is a DuckDB reserved word) and foil
# are all optional (NULL-able), so we cannot use them in a PRIMARY KEY.  We
# instead enforce uniqueness with a UNIQUE index and use INSERT OR REPLACE via
# a delete-then-reinsert idiom (DuckDB lacks INSERT OR REPLACE on non-PK
# constraints).  The full-owner-delete-then-reinsert in load_inventory_rows
# provides the same idempotency guarantee.

USER_DECKS_DDL = """
CREATE TABLE IF NOT EXISTS user_decks (
    id                 VARCHAR PRIMARY KEY,
    owner              VARCHAR NOT NULL,
    name               VARCHAR NOT NULL,
    archetype_hint     VARCHAR,
    current_version_id VARCHAR,
    created            VARCHAR,
    updated            VARCHAR
)
"""

DECK_VERSIONS_DDL = """
CREATE TABLE IF NOT EXISTS deck_versions (
    id      VARCHAR PRIMARY KEY,
    deck_id VARCHAR NOT NULL,
    version INTEGER NOT NULL,
    label   VARCHAR,
    created VARCHAR,
    note    VARCHAR
)
"""

DECK_VERSION_CARDS_DDL = """
CREATE TABLE IF NOT EXISTS deck_version_cards (
    version_id VARCHAR NOT NULL,
    board      VARCHAR NOT NULL,
    name       VARCHAR NOT NULL,
    printing   VARCHAR,
    count      INTEGER NOT NULL
)
"""

_ALL_DDL = [
    INVENTORY_ENTRIES_DDL,
    USER_DECKS_DDL,
    DECK_VERSIONS_DDL,
    DECK_VERSION_CARDS_DDL,
]

_COLLECTION_TABLES = (
    "inventory_entries",
    "user_decks",
    "deck_versions",
    "deck_version_cards",
)


# ---------------------------------------------------------------------------
# Connection (reuses ingestion/store's DUCKDB_PATH)
# ---------------------------------------------------------------------------


def connect(path: Path | str = DUCKDB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (creating parent dirs) a DuckDB connection.  Use ``:memory:`` for tests."""
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


# ---------------------------------------------------------------------------
# Schema init
# ---------------------------------------------------------------------------


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the four collection tables if absent (idempotent)."""
    for ddl in _ALL_DDL:
        con.execute(ddl)


# ---------------------------------------------------------------------------
# Load helpers — populate tables from Pydantic docs
# ---------------------------------------------------------------------------


def load_inventory_rows(con: duckdb.DuckDBPyConnection, inv: Inventory) -> None:
    """Upsert all entries from an Inventory into ``inventory_entries``.

    Replaces existing rows for the same owner (full refresh per owner).
    """
    con.execute("DELETE FROM inventory_entries WHERE owner = ?", [inv.owner])
    rows = [
        (
            inv.owner,
            e.name,
            e.printing,
            e.condition,
            e.foil,
            e.count,
        )
        for e in inv.entries
    ]
    if rows:
        con.executemany(
            "INSERT INTO inventory_entries (owner, name, printing, condition_kw, foil, count)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )


def load_user_deck_rows(con: duckdb.DuckDBPyConnection, deck: UserDeck) -> None:
    """Upsert a UserDeck and all its versions + cards into the derived tables.

    Replaces existing rows for this deck id (full refresh per deck).
    """
    # Cascade-delete child rows first.
    version_ids = [v.id for v in deck.versions]
    if version_ids:
        for vid in version_ids:
            con.execute("DELETE FROM deck_version_cards WHERE version_id = ?", [vid])
    con.execute("DELETE FROM deck_versions WHERE deck_id = ?", [deck.id])
    con.execute("DELETE FROM user_decks WHERE id = ?", [deck.id])

    # Insert deck row.
    con.execute(
        "INSERT INTO user_decks (id, owner, name, archetype_hint, current_version_id, created, updated)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            deck.id,
            deck.owner,
            deck.name,
            deck.archetype_hint,
            deck.current_version_id,
            deck.created,
            deck.updated,
        ],
    )

    # Insert version rows + card rows.
    for ver in deck.versions:
        con.execute(
            "INSERT INTO deck_versions (id, deck_id, version, label, created, note)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [ver.id, deck.id, ver.version, ver.label, ver.created, ver.note],
        )
        card_rows = [
            (ver.id, c.board, c.name, c.printing, c.count)
            for c in ver.cards
        ]
        if card_rows:
            con.executemany(
                "INSERT INTO deck_version_cards (version_id, board, name, printing, count)"
                " VALUES (?, ?, ?, ?, ?)",
                card_rows,
            )


# ---------------------------------------------------------------------------
# Rebuild — drop + reload from JSON files
# ---------------------------------------------------------------------------


def rebuild_collection(
    con: duckdb.DuckDBPyConnection,
    owner: str = LOCAL_OWNER,
) -> None:
    """Drop all four collection tables and reload from ``data/collection/`` JSON.

    ``owner`` scopes which inventory is loaded.  All deck files are loaded
    regardless of owner (a deck's owner field is stored per-row).

    Safe to run repeatedly — raw JSON is the source of truth; DuckDB is the
    derived cache.
    """
    from legacy_engine.collection.persist import list_user_decks, load_inventory

    # Drop all four tables in dependency order.
    for table in reversed(_COLLECTION_TABLES):
        con.execute(f"DROP TABLE IF EXISTS {table}")
    init_schema(con)

    # Reload inventory.
    inv = load_inventory(owner)
    load_inventory_rows(con, inv)

    # Reload all decks for all owners (deck files are per-id, not per-owner).
    for deck in list_user_decks(owner):
        load_user_deck_rows(con, deck)


# ---------------------------------------------------------------------------
# Query helpers (owner-scoped)
# ---------------------------------------------------------------------------


def fetch_owned_counts(
    con: duckdb.DuckDBPyConnection,
    owner: str = LOCAL_OWNER,
) -> dict[str, int]:
    """Return {card_name: total_owned} summed across all printings for ``owner``."""
    rows = con.execute(
        "SELECT name, SUM(count) FROM inventory_entries WHERE owner = ? GROUP BY name",
        [owner],
    ).fetchall()
    return {name: int(cnt) for name, cnt in rows}


def fetch_current_version_cards(
    con: duckdb.DuckDBPyConnection,
    deck_id: str,
) -> dict[str, int]:
    """Return {card_name: total_count} for a deck's current version (main + side combined).

    Joins ``user_decks`` → ``current_version_id`` → ``deck_version_cards``.
    Returns an empty dict if the deck has no current version.
    """
    rows = con.execute(
        """
        SELECT dvc.name, SUM(dvc.count)
        FROM user_decks ud
        JOIN deck_version_cards dvc ON dvc.version_id = ud.current_version_id
        WHERE ud.id = ?
        GROUP BY dvc.name
        """,
        [deck_id],
    ).fetchall()
    return {name: int(cnt) for name, cnt in rows}


def fetch_all_current_cards(
    con: duckdb.DuckDBPyConnection,
    owner: str = LOCAL_OWNER,
) -> dict[str, dict[str, int]]:
    """Return {deck_name: {card_name: count}} for all decks' current versions.

    Used by ``collection status`` to compute contention across all decks.
    """
    rows = con.execute(
        """
        SELECT ud.name, dvc.name, SUM(dvc.count)
        FROM user_decks ud
        JOIN deck_version_cards dvc ON dvc.version_id = ud.current_version_id
        WHERE ud.owner = ?
        GROUP BY ud.name, dvc.name
        """,
        [owner],
    ).fetchall()
    result: dict[str, dict[str, int]] = {}
    for deck_name, card_name, cnt in rows:
        result.setdefault(deck_name, {})[card_name] = int(cnt)
    return result

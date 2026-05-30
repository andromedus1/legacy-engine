"""DuckDB analytical store — the rebuildable derived cache over raw-JSON source of truth.

This feature defines the ``cards`` table (the card dimension). The tournament-data tables
(tournaments, decks, deck_cards, rounds, standings, archetype_labels) are owned by the
tournament-ingestion epic and intentionally NOT declared here, to avoid schema drift.

A thin functional API establishes the SQL access pattern the analytics and advisory layers inherit.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import duckdb

from legacy_engine.config import DUCKDB_PATH
from legacy_engine.models.card import Card

CARDS_DDL = """
CREATE TABLE IF NOT EXISTS cards (
    name VARCHAR PRIMARY KEY,
    mana_cost VARCHAR,
    cmc DOUBLE,
    type_line VARCHAR,
    colors VARCHAR,
    produced_mana VARCHAR,
    oracle_text VARCHAR,
    layout VARCHAR,
    is_land BOOLEAN
)
"""


def connect(path: Path | str = DUCKDB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (creating parent dirs) a DuckDB connection. Use ":memory:" for tests."""
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the analytical schema if absent (idempotent)."""
    con.execute(CARDS_DDL)


def load_cards(con: duckdb.DuckDBPyConnection, cards: Iterable[Card]) -> int:
    """Insert/replace cards into the cards table. Idempotent on ``name``. Returns the count loaded."""
    init_schema(con)
    rows = [
        (
            c.name,
            c.mana_cost,
            c.cmc,
            c.type_line,
            "".join(c.colors),
            "".join(c.produced_mana),
            c.oracle_text,
            c.layout,
            c.is_land,
        )
        for c in cards
    ]
    if rows:
        con.executemany("INSERT OR REPLACE INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    return len(rows)


def fetch_card(con: duckdb.DuckDBPyConnection, name: str) -> dict | None:
    """Fetch one card row as a dict, or None if absent."""
    cur = con.execute("SELECT * FROM cards WHERE name = ?", [name])
    row = cur.fetchone()
    if row is None:
        return None
    columns = [d[0] for d in cur.description]
    return dict(zip(columns, row))


def rebuild(con: duckdb.DuckDBPyConnection) -> None:
    """Drop and recreate the cards table (raw JSON remains the source of truth)."""
    con.execute("DROP TABLE IF EXISTS cards")
    init_schema(con)

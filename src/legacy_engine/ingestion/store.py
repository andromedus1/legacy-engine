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
from legacy_engine.models.tournament import TournamentResult

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
    is_land BOOLEAN,
    power VARCHAR,
    toughness VARCHAR
)
"""

# Tournament-data tables (the matchup/meta-share fact layer). `archetype` on decks is NULL until the
# archetype-classifier epic labels them.
TOURNAMENT_DDL = [
    """CREATE TABLE IF NOT EXISTS tournaments (
        id VARCHAR PRIMARY KEY, name VARCHAR, date VARCHAR, uri VARCHAR,
        format VARCHAR, source VARCHAR, provenance VARCHAR
    )""",
    """CREATE TABLE IF NOT EXISTS decks (
        tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, result VARCHAR, archetype VARCHAR,
        PRIMARY KEY (tournament_id, deck_idx)
    )""",
    """CREATE TABLE IF NOT EXISTS deck_cards (
        tournament_id VARCHAR, deck_idx INTEGER, board VARCHAR, name VARCHAR, count INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS rounds (
        tournament_id VARCHAR, match_idx INTEGER, player1 VARCHAR, player2 VARCHAR, result VARCHAR
    )""",
    """CREATE TABLE IF NOT EXISTS standings (
        tournament_id VARCHAR, rank INTEGER, player VARCHAR, points INTEGER,
        wins INTEGER, losses INTEGER, draws INTEGER
    )""",
]


def connect(path: Path | str = DUCKDB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (creating parent dirs) a DuckDB connection. Use ":memory:" for tests."""
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the analytical schema if absent (idempotent)."""
    con.execute(CARDS_DDL)
    for ddl in TOURNAMENT_DDL:
        con.execute(ddl)


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
            c.power,
            c.toughness,
        )
        for c in cards
    ]
    if rows:
        con.executemany("INSERT OR REPLACE INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
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


def tournament_id(tr: TournamentResult) -> str:
    """Stable id for a tournament — its Uri if present, else source:name:date."""
    return tr.uri or f"{tr.source}:{tr.name}:{tr.date}"


def load_tournament(con: duckdb.DuckDBPyConnection, tr: TournamentResult) -> str:
    """Load a parsed tournament into the fact tables. Idempotent per tournament (full refresh)."""
    init_schema(con)
    tid = tournament_id(tr)

    con.execute(
        "INSERT OR REPLACE INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
        [tid, tr.name, tr.date, tr.uri, tr.format, tr.source, tr.provenance],
    )
    # Idempotent refresh: clear this tournament's child rows, then re-insert.
    for table in ("decks", "deck_cards", "rounds", "standings"):
        con.execute(f"DELETE FROM {table} WHERE tournament_id = ?", [tid])

    deck_rows = []
    card_rows = []
    for idx, deck in enumerate(tr.decks):
        deck_rows.append((tid, idx, deck.player, deck.result, None))  # archetype NULL until labeled
        for cc in deck.mainboard:
            card_rows.append((tid, idx, "main", cc.name, cc.count))
        for cc in deck.sideboard:
            card_rows.append((tid, idx, "side", cc.name, cc.count))
    if deck_rows:
        con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?)", deck_rows)
    if card_rows:
        con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", card_rows)

    round_rows = [(tid, i, m.player1, m.player2, m.result) for i, m in enumerate(tr.rounds)]
    if round_rows:
        con.executemany("INSERT INTO rounds VALUES (?, ?, ?, ?, ?)", round_rows)

    standing_rows = [
        (tid, s.rank, s.player, s.points, s.wins, s.losses, s.draws) for s in tr.standings
    ]
    if standing_rows:
        con.executemany("INSERT INTO standings VALUES (?, ?, ?, ?, ?, ?, ?)", standing_rows)

    return tid

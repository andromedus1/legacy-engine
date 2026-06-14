"""DuckDB analytical store — the rebuildable derived cache over raw-JSON source of truth.

This feature defines the ``cards`` table (the card dimension). The tournament-data tables
(tournaments, decks, deck_cards, rounds, standings, archetype_labels) are owned by the
tournament-ingestion epic and intentionally NOT declared here, to avoid schema drift.

A thin functional API establishes the SQL access pattern the analytics and advisory layers inherit.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from legacy_engine.ingestion.prices import PrintingPrice

from legacy_engine.config import DUCKDB_PATH
from legacy_engine.models.card import Card
from legacy_engine.models.tournament import TournamentResult

# ── card_prices DDL ────────────────────────────────────────────────────────────────────────────────
# Separate from the ``cards`` table: prices live at printing cardinality (set + collector number),
# refresh on a daily cadence, and are an optional/gated signal.  The ``cards`` table is the
# oracle dimension (one row per playable name); folding per-printing prices into it would break
# its primary key.
CARD_PRICES_DDL = """
CREATE TABLE IF NOT EXISTS card_prices (
    scryfall_id      VARCHAR PRIMARY KEY,
    name             VARCHAR NOT NULL,
    set_code         VARCHAR,
    set_name         VARCHAR,
    collector_number VARCHAR,
    usd              DOUBLE,
    usd_foil         DOUBLE,
    usd_etched       DOUBLE,
    eur              DOUBLE,
    promo            BOOLEAN,
    is_paper         BOOLEAN,
    price_date       VARCHAR
)
"""

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
        variant VARCHAR,
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

# Derived identity table — populated by analytics.players.identity.materialize_player_aliases.
# Declared here so init_schema always creates the empty table in a fresh DB.
PLAYER_ALIASES_DDL = """\
CREATE TABLE IF NOT EXISTS player_aliases (
    handle_norm VARCHAR PRIMARY KEY,
    player_id   VARCHAR NOT NULL
)\
"""


def connect(path: Path | str = DUCKDB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (creating parent dirs) a DuckDB connection. Use ":memory:" for tests."""
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the analytical schema if absent (idempotent).

    Also runs ALTER TABLE migrations so an EXISTING cards table (created before
    the power/toughness columns were added) gains those columns without data loss.
    DuckDB supports ``ADD COLUMN IF NOT EXISTS`` natively, making these idempotent.
    """
    con.execute(CARDS_DDL)
    # Migration: add power/toughness to tables created with the old 9-column schema.
    con.execute("ALTER TABLE cards ADD COLUMN IF NOT EXISTS power VARCHAR")
    con.execute("ALTER TABLE cards ADD COLUMN IF NOT EXISTS toughness VARCHAR")
    for ddl in TOURNAMENT_DDL:
        con.execute(ddl)
    # Migration: add variant column (sub-archetype tag, NULL until labeler resolves it).
    # Idempotent — ADD COLUMN IF NOT EXISTS is a no-op on tables that already carry it.
    con.execute("ALTER TABLE decks ADD COLUMN IF NOT EXISTS variant VARCHAR")
    # Derived identity table — data populated by materialize_player_aliases; empty until then.
    con.execute(PLAYER_ALIASES_DDL)


# Multi-face layout classes — determine how a face name inherits attributes.
#   FRONT-cast (you cast the front; the back is reached by transform/flip in play, never paid for):
#     a face row gets THAT face's own colors (you commit only to the front's colors to cast it).
#   BOTH-castable (you may cast either face from hand, or both): color identity = UNION of faces, and
#     the card is land-capable if ANY face is a land (modal-DFC lands are run as flex lands).
_FRONT_CAST_LAYOUTS = frozenset({"transform", "flip", "meld"})
_BOTH_CASTABLE_LAYOUTS = frozenset({"modal_dfc", "split", "adventure", "aftermath"})
# Non-gameplay objects (art cards, tokens, emblems, etc.). Their faces must NOT generate
# face aliases — an "art_series" card shares the real card's face name and would otherwise
# shadow the genuine front face (e.g. the Tamiyo, Inquisitive Student art card colliding with
# the real transform card).
_NON_GAMEPLAY_LAYOUTS = frozenset(
    {"art_series", "token", "double_faced_token", "emblem", "planar", "scheme", "vanguard"}
)


def _union_colors(c: Card) -> list[str]:
    """Color identity = union of the combined card's colors and every face's colors."""
    s = set(c.colors)
    for f in c.card_faces:
        s.update(f.get("colors") or [])
    return sorted(s)


def load_cards(con: duckdb.DuckDBPyConnection, cards: Iterable[Card]) -> int:
    """Insert/replace cards into the cards table. Idempotent on ``name``. Returns the count of cards loaded.

    Multi-face cards (transform DFC / flip / adventure / split / modal-DFC) carry a combined ``A // B`` name
    in the Scryfall oracle pool, but decklists reference a single face (``Brazen Borrower``,
    ``Tamiyo, Inquisitive Student``). Each face name is ALSO inserted as an alias row, **layout-aware** so the
    front face you actually cast carries the right attributes rather than a blended blob:

    - **type_line / cmc / mana_cost / power / toughness**: the FACE's own values (the front face is what you
      cast; for adventure, the creature face is the permanent).
    - **colors**: front-cast layouts (transform/flip/meld) use the face's own colors (you only pay the front to
      cast it; the back is reached in play). Both-castable layouts (modal-DFC/split/adventure/aftermath) use
      the UNION color identity (either/both faces are castable, so the deck commits to all their colors).
    - **is_land**: the face's own land-ness, EXCEPT both-castable cards are land-capable if ANY face is a land
      (a modal-DFC land counts toward the mana base under its front-face name).

    The combined ``A // B`` row also gets the union color identity (so it is never empty-colored). Alias rows
    use INSERT OR IGNORE after the full-name rows, so a genuine standalone card sharing a face name always wins.
    """
    init_schema(con)
    cards = list(cards)
    _COLS = (
        "(name, mana_cost, cmc, type_line, colors, produced_mana, oracle_text, layout, is_land, power, toughness)"
    )
    _VALUES = "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

    def _tuple(name, mana_cost, cmc, type_line, colors, produced, oracle, layout, is_land, power, tough):
        return (name, mana_cost, cmc, type_line, "".join(colors), "".join(produced),
                oracle, layout, is_land, power, tough)

    # Full-name rows: combined card keeps its attrs but gets the UNION color identity (fixes the
    # empty-colors-on-DFC case where Scryfall's top-level `colors` is absent for multi-face cards).
    full_rows = [
        _tuple(c.name, c.mana_cost, c.cmc, c.type_line,
               _union_colors(c) if c.card_faces else c.colors,
               c.produced_mana, c.oracle_text, c.layout, c.is_land, c.power, c.toughness)
        for c in cards
    ]
    if full_rows:
        con.executemany(f"INSERT OR REPLACE INTO cards {_COLS} {_VALUES}", full_rows)

    # Layout-aware face-alias rows.
    alias_rows: list[tuple] = []
    for c in cards:
        if " // " not in c.name or not c.card_faces or c.layout in _NON_GAMEPLAY_LAYOUTS:
            continue
        both_castable = c.layout in _BOTH_CASTABLE_LAYOUTS
        union = _union_colors(c)
        any_face_land = c.is_land or any("Land" in (f.get("type_line") or "") for f in c.card_faces)
        # produced_mana: union across faces (a modal-DFC land produces under its front-face name).
        produced = sorted({*c.produced_mana, *(m for f in c.card_faces for m in (f.get("produced_mana") or []))})
        for f in c.card_faces:
            fname = (f.get("name") or "").strip()
            if not fname or fname == c.name:
                continue
            ftype = f.get("type_line") or c.type_line
            face_is_land = ("Land" in ftype) or (both_castable and any_face_land)
            fcolors = union if both_castable else (f.get("colors") or [])
            alias_rows.append(_tuple(
                fname, f.get("mana_cost") or c.mana_cost, f.get("cmc", c.cmc), ftype,
                fcolors, produced, f.get("oracle_text") or c.oracle_text, c.layout,
                face_is_land, f.get("power"), f.get("toughness"),
            ))
    if alias_rows:
        con.executemany(f"INSERT OR IGNORE INTO cards {_COLS} {_VALUES}", alias_rows)

    return len(full_rows)


def fetch_card(con: duckdb.DuckDBPyConnection, name: str) -> dict | None:
    """Fetch one card row as a dict, or None if absent."""
    cur = con.execute("SELECT * FROM cards WHERE name = ?", [name])
    row = cur.fetchone()
    if row is None:
        return None
    columns = [d[0] for d in cur.description]
    return dict(zip(columns, row))


def load_card(con: duckdb.DuckDBPyConnection, name: str) -> Card | None:
    """Resolve a card name to a fully reconstructed ``Card``, or ``None`` if absent.

    SSOT for the cards-table round-trip: undoes the joined-string serialization of
    ``colors`` / ``produced_mana`` that ``load_cards`` applies (``"".join(c.colors)``),
    splitting them back into single-character lists. ``power``/``toughness`` are stored
    as plain VARCHAR (or NULL) and pass through unchanged. Mirrors the reconstruction
    currently inlined in ``advisory.whattoplay._load_deck_cards`` — that caller can adopt
    this helper later.
    """
    row = fetch_card(con, name)
    if row is None:
        return None
    colors_raw = row.get("colors") or ""
    produced_raw = row.get("produced_mana") or ""
    row["colors"] = list(colors_raw) if colors_raw else []
    row["produced_mana"] = list(produced_raw) if produced_raw else []
    return Card.model_validate(row)


def rebuild(con: duckdb.DuckDBPyConnection) -> None:
    """Drop and recreate the cards table (raw JSON remains the source of truth)."""
    con.execute("DROP TABLE IF EXISTS cards")
    init_schema(con)


# ── card_prices table helpers ──────────────────────────────────────────────────────────────────────


def init_prices_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the card_prices table if absent (idempotent).

    Intentionally separate from ``init_schema`` so the cards/oracle path stays byte-identical
    when prices have never been seeded (gated-additive-augmentation: the no-price corpus behaves
    exactly as today).
    """
    con.execute(CARD_PRICES_DDL)


def load_prices(con: duckdb.DuckDBPyConnection, printings: "Iterable[PrintingPrice]") -> int:
    """Insert/replace per-printing price rows into card_prices. Idempotent on scryfall_id.

    Args:
        con: DuckDB connection (card_prices table must exist — call init_prices_schema first).
        printings: Iterable of ``PrintingPrice`` dataclass instances.

    Returns:
        Number of rows loaded (not counting idempotent skips).
    """
    rows = [
        (
            pp.scryfall_id,
            pp.name,
            pp.set_code,
            pp.set_name,
            pp.collector_number,
            pp.usd,
            pp.usd_foil,
            pp.usd_etched,
            pp.eur,
            pp.promo,
            pp.is_paper,
            pp.price_date,
        )
        for pp in printings
    ]
    if not rows:
        return 0
    con.executemany(
        """
        INSERT OR REPLACE INTO card_prices
        (scryfall_id, name, set_code, set_name, collector_number,
         usd, usd_foil, usd_etched, eur, promo, is_paper, price_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def rebuild_prices(con: duckdb.DuckDBPyConnection) -> None:
    """Drop and recreate card_prices (the raw default_cards.json mirror is the source of truth)."""
    con.execute("DROP TABLE IF EXISTS card_prices")
    init_prices_schema(con)


def tournament_id(tr: TournamentResult) -> str:
    """Stable id for a tournament — its Uri if present, else a content-derived fallback.

    For URI-bearing events the URI is the id (unchanged).
    For no-URI events (e.g. paper tournaments without a canonical URL), a deterministic 8-char
    SHA-1 digest of the sorted player-name set is appended so two events sharing the same
    source/name/date but with different player pools get distinct ids, while re-ingesting the
    same event always produces the same id (preserves load_tournament idempotency).
    """
    if tr.uri:
        return tr.uri
    players = "|".join(sorted(d.player for d in tr.decks))
    digest = hashlib.sha1(players.encode()).hexdigest()[:8]
    return f"{tr.source}:{tr.name}:{tr.date}:{digest}"


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
        # archetype + variant both NULL until the labeler runs.
        deck_rows.append((tid, idx, deck.player, deck.result, None, None))
        for cc in deck.mainboard:
            card_rows.append((tid, idx, "main", cc.name, cc.count))
        for cc in deck.sideboard:
            card_rows.append((tid, idx, "side", cc.name, cc.count))
    if deck_rows:
        con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", deck_rows)
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

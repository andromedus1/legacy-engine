"""DuckDB analytical store — the rebuildable derived cache over raw-JSON source of truth.

This feature defines the ``cards`` table (the card dimension). The tournament-data tables
(tournaments, decks, deck_cards, rounds, standings, archetype_labels) are owned by the
tournament-ingestion epic and intentionally NOT declared here, to avoid schema drift.

A thin functional API establishes the SQL access pattern the analytics and advisory layers inherit.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from legacy_engine.ingestion.prices import PrintingPrice

from legacy_engine.config import DUCKDB_PATH
from legacy_engine.models.card import Card, CardAliasManifest, PrintedCardAlias
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

# Derived state — the keyed-reload ledger tracks which cache files have already been ingested
# (by content hash), so an unchanged event on a re-refresh is skipped rather than reloaded and
# wiping archetype/variant labels. An empty ledger means "nothing recorded yet" and forces a full
# ingest (never a false "unchanged"), so a fresh/pre-feature DB degrades safely.
INGEST_LEDGER_DDL = """\
CREATE TABLE IF NOT EXISTS ingest_ledger (
    path          VARCHAR PRIMARY KEY,
    content_hash  VARCHAR NOT NULL,
    tournament_id VARCHAR NOT NULL,
    ingested_at   VARCHAR NOT NULL
)\
"""

CARD_NAME_ALIASES_DDL = """\
CREATE TABLE IF NOT EXISTS card_name_aliases (
    normalized_alias VARCHAR NOT NULL,
    canonical_name VARCHAR NOT NULL,
    printed_name VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    sample_scryfall_id VARCHAR NOT NULL,
    source_updated_at VARCHAR NOT NULL,
    PRIMARY KEY (normalized_alias, canonical_name, language)
)\
"""

CARD_ALIAS_MANIFEST_DDL = """\
CREATE TABLE IF NOT EXISTS card_alias_manifest (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    source_updated_at VARCHAR NOT NULL,
    built_at VARCHAR NOT NULL,
    release_codes VARCHAR NOT NULL,
    alias_count INTEGER NOT NULL,
    ambiguous_key_count INTEGER NOT NULL
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
    # Derived state — empty ledger ⇒ full ingest; existing DBs gain this table on next init.
    con.execute(INGEST_LEDGER_DDL)


def init_card_alias_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the rebuildable localized-name alias cache and its manifest."""
    con.execute(CARD_NAME_ALIASES_DDL)
    con.execute(CARD_ALIAS_MANIFEST_DDL)


def rebuild_card_aliases(
    con: duckdb.DuckDBPyConnection,
    aliases: Iterable[PrintedCardAlias],
    *,
    manifest: CardAliasManifest,
) -> CardAliasManifest:
    """Atomically replace the derived alias snapshot, preserving every canonical collision."""
    deduped: dict[tuple[str, str, str], PrintedCardAlias] = {}
    for alias in aliases:
        missing = [
            field for field in (
                "printed_name", "normalized_alias", "canonical_name", "language", "scryfall_id"
            ) if not getattr(alias, field)
        ]
        if missing:
            raise ValueError(
                "card alias candidate missing required provenance: " + ", ".join(missing)
            )
        key = (alias.normalized_alias, alias.canonical_name, alias.language)
        current = deduped.get(key)
        if current is None or (alias.scryfall_id, alias.printed_name) < (
            current.scryfall_id,
            current.printed_name,
        ):
            deduped[key] = alias
    if not deduped:
        raise ValueError("refusing to replace card aliases with an empty candidate snapshot")
    previous = load_card_alias_manifest(con)
    if previous is not None and len(deduped) * 2 < previous.alias_count:
        raise ValueError(
            "refusing implausibly incomplete card-alias snapshot: "
            f"{len(deduped)} candidates vs {previous.alias_count} last-good aliases"
        )
    canonical_by_key: dict[str, set[str]] = {}
    for alias in deduped.values():
        canonical_by_key.setdefault(alias.normalized_alias, set()).add(alias.canonical_name)
    effective = manifest.model_copy(update={
        "alias_count": len(deduped),
        "ambiguous_key_count": sum(len(names) > 1 for names in canonical_by_key.values()),
        "release_codes": tuple(sorted(set(manifest.release_codes))),
    })

    con.execute("BEGIN TRANSACTION")
    try:
        init_card_alias_schema(con)
        con.execute("DELETE FROM card_name_aliases")
        con.execute("DELETE FROM card_alias_manifest")
        if deduped:
            con.executemany(
                """INSERT INTO card_name_aliases VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (
                        alias.normalized_alias,
                        alias.canonical_name,
                        alias.printed_name,
                        alias.language,
                        alias.scryfall_id,
                        effective.source_updated_at,
                    )
                    for alias in sorted(
                        deduped.values(),
                        key=lambda item: (
                            item.normalized_alias,
                            item.canonical_name,
                            item.language,
                        ),
                    )
                ],
            )
        con.execute(
            "INSERT INTO card_alias_manifest VALUES (TRUE, ?, ?, ?, ?, ?)",
            [
                effective.source_updated_at,
                effective.built_at.isoformat(),
                ",".join(effective.release_codes),
                effective.alias_count,
                effective.ambiguous_key_count,
            ],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return effective


def load_card_alias_manifest(
    con: duckdb.DuckDBPyConnection,
) -> CardAliasManifest | None:
    init_card_alias_schema(con)
    row = con.execute(
        """SELECT source_updated_at, built_at, release_codes, alias_count,
                  ambiguous_key_count FROM card_alias_manifest WHERE singleton = TRUE"""
    ).fetchone()
    if row is None:
        return None
    return CardAliasManifest(
        source_updated_at=row[0],
        built_at=row[1],
        release_codes=tuple(code for code in row[2].split(",") if code),
        alias_count=row[3],
        ambiguous_key_count=row[4],
    )


def fetch_card_alias_candidates(
    con: duckdb.DuckDBPyConnection,
    observed_name: str,
) -> tuple[PrintedCardAlias, ...]:
    from legacy_engine.ingestion.scryfall import normalize_alias_key

    init_card_alias_schema(con)
    rows = con.execute(
        """SELECT printed_name, normalized_alias, canonical_name, language,
                  sample_scryfall_id
           FROM card_name_aliases WHERE normalized_alias = ?
           ORDER BY canonical_name, language, printed_name""",
        [normalize_alias_key(observed_name)],
    ).fetchall()
    return tuple(
        PrintedCardAlias(
            printed_name=row[0],
            normalized_alias=row[1],
            canonical_name=row[2],
            language=row[3],
            scryfall_id=row[4],
        )
        for row in rows
    )


def alias_snapshot_needs_refresh(
    manifest: CardAliasManifest | None,
    recent_release_codes: Iterable[str],
) -> bool:
    if manifest is None:
        return True
    return not set(recent_release_codes).issubset(manifest.release_codes)


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


def existing_card_names(con: duckdb.DuckDBPyConnection) -> set[str]:
    """Return the set of card names currently in the cards table.

    Returns an empty set when the table does not yet exist (fresh DB), so callers
    can call this before init_schema without raising.
    """
    try:
        rows = con.execute("SELECT name FROM cards").fetchall()
    except Exception:
        return set()
    return {row[0] for row in rows}


@dataclass(frozen=True)
class IngestDiff:
    """Result of a diff-producing ingest run.

    ``new_names``: card names present in the incoming bulk but absent from the table
    before this load. The authoritative "new cards" signal — robust to how Scryfall's
    bulk changed (new set, Secret Lair drop, oracle erratum adding a face alias).

    ``total_after``: total number of full-name card rows in the table after the load.

    ``scryfall_updated_at``: the bulk file's ``updated_at`` provenance string (from
    metadata.json), or None if unavailable. Round-tripped for auditability.
    """

    new_names: tuple[str, ...]
    total_after: int
    scryfall_updated_at: str | None


def load_cards_diff(
    con: duckdb.DuckDBPyConnection,
    cards: Iterable[Card],
    *,
    scryfall_updated_at: str | None = None,
) -> IngestDiff:
    """INSERT OR REPLACE all cards (idempotent, identical to load_cards) and capture the diff.

    Captures the set of card names present before the load, calls load_cards, then
    computes the set difference to yield newly-ingested names. Non-destructive: the
    cards table is NOT dropped — this is the incremental, diff-aware path. The full
    rebuild path (drop + reload) remains ``rebuild`` + ``load_cards``.

    Args:
        con: DuckDB connection (cards table created if absent).
        cards: Iterable of Card objects to ingest (the full current bulk).
        scryfall_updated_at: Provenance string from the Scryfall bulk metadata.json;
            persisted in the returned IngestDiff for auditability.

    Returns:
        IngestDiff with new_names (sorted tuple), total_after, and scryfall_updated_at.
    """
    cards_list = list(cards)
    before = existing_card_names(con)
    load_cards(con, cards_list)
    # Count all rows (includes face aliases stored by INSERT OR IGNORE); total_after
    # is an approximate deck-count signal, not the exact playable-name count.
    total_after = con.execute("SELECT count(*) FROM cards").fetchone()[0]
    after_names = existing_card_names(con)
    new = tuple(sorted(after_names - before))
    return IngestDiff(
        new_names=new,
        total_after=total_after,
        scryfall_updated_at=scryfall_updated_at,
    )


def persist_ingest_diff(diff: IngestDiff, path: "Path | None" = None) -> None:
    """Write an IngestDiff to a small JSON file for cross-run hand-off.

    Serialises new_names (sorted list), total_after, scryfall_updated_at, and a
    persisted_at timestamp (UTC ISO). Overwrites any previous file — only the latest
    diff is kept (the hand-off is "what just changed", not a full history).

    Follows the constants-only-config path convention: path defaults to
    ``INGEST_DIFF_PATH`` from config, but callers may override for testing.
    """
    import json
    from datetime import datetime, timezone
    from pathlib import Path as _Path

    if path is None:
        from legacy_engine.config import INGEST_DIFF_PATH
        path = INGEST_DIFF_PATH

    path = _Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "new_names": list(diff.new_names),
        "total_after": diff.total_after,
        "scryfall_updated_at": diff.scryfall_updated_at,
        "persisted_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2))


def load_ingest_diff(path: "Path | None" = None) -> "IngestDiff | None":
    """Read the persisted IngestDiff from disk, or return None if the file is absent.

    Degrades gracefully: callers should treat None as "no diff recorded yet — run
    `refresh cards`" and fall back to whatever proxy they used before.
    """
    import json
    from pathlib import Path as _Path

    if path is None:
        from legacy_engine.config import INGEST_DIFF_PATH
        path = INGEST_DIFF_PATH

    path = _Path(path)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
        return IngestDiff(
            new_names=tuple(data.get("new_names", [])),
            total_after=int(data.get("total_after", 0)),
            scryfall_updated_at=data.get("scryfall_updated_at"),
        )
    except Exception:
        return None


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
    # Incremental variant assignments are keyed by tournament + deck index. A changed cache
    # payload can reuse an index for a different deck/archetype, so stale assignments must not
    # survive the fact-row replacement. The table is created lazily by the discovery path.
    try:
        con.execute(
            "DELETE FROM variant_incremental_assignments WHERE tournament_id = ?", [tid]
        )
    except duckdb.CatalogException:
        pass

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

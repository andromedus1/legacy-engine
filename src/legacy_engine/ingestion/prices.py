"""Per-printing card pricing — query layer over the ``card_prices`` table.

This module owns the public price interface consumed by the acquisition advisor and any other
feature that needs trustworthy per-printing prices.  It never makes network calls; it reads
from the locally mirrored ``card_prices`` table populated by ``seed prices``.

Key honesty contract:
- ``price_quote`` never returns a silent 0 for an unpriced card.  When all paper printings have
  ``usd: null``, the returned ``PriceQuote`` carries ``all_null=True`` — the caller sees an
  explicit "we have no paper price" signal, not an imputed zero.
- ``deck_cost`` carries an ``unpriced`` list of names with no paper price.  It never silently
  drops a card from the budget sum; the caller sees exactly what is and isn't priced.
- ``stale=True`` is set when the price data is older than ``PRICE_STALE_DAYS`` (configurable).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    import duckdb

from legacy_engine.config import PRICE_OVERRIDE_PATH, PRICE_STALE_DAYS

logger = logging.getLogger(__name__)

# Layout classes that are non-gameplay objects — skip these when building price rows.
# Mirrors store._NON_GAMEPLAY_LAYOUTS so the price table never ingests tokens/emblems/etc.
_NON_GAMEPLAY_LAYOUTS = frozenset(
    {"art_series", "token", "double_faced_token", "emblem", "planar", "scheme", "vanguard"}
)


# ── Data records ──────────────────────────────────────────────────────────────────────────────────


@dataclass
class PrintingPrice:
    """One printing's price row — the unit returned by the query helpers."""

    scryfall_id: str
    name: str
    set_code: str | None
    set_name: str | None
    collector_number: str | None
    usd: float | None
    usd_foil: float | None
    usd_etched: float | None
    eur: float | None
    promo: bool
    is_paper: bool
    price_date: str | None  # bulk updated_at; used for staleness

    @property
    def cheapest_usd(self) -> float | None:
        """Cheapest playable USD price for this printing.

        Prefers nonfoil (``usd``); falls back to foil or etched only when no nonfoil price
        exists.  Returns None when all three are null.
        """
        if self.usd is not None:
            return self.usd
        if self.usd_foil is not None:
            return self.usd_foil
        if self.usd_etched is not None:
            return self.usd_etched
        return None


@dataclass
class PriceQuote:
    """The confidence-carrying price record for one card name.

    Attributes:
        name: The card name (normalized; joins to ``cards.name``).
        cheapest_usd: The cheapest USD price across all paper printings, or None when
            ``all_null`` is True.
        cheapest_printing: The ``PrintingPrice`` row that produced ``cheapest_usd``.
        n_priced_printings: Number of paper printings with a non-null USD price.
        all_null: True when every paper printing of this card has ``usd: null``.  The caller
            must treat this as "no paper price available", not as "$0".
        stale: True when the price data is older than ``PRICE_STALE_DAYS``.
        source: Human-readable source label (e.g. "scryfall/default_cards" or "override").
    """

    name: str
    cheapest_usd: float | None
    cheapest_printing: PrintingPrice | None
    n_priced_printings: int
    all_null: bool
    stale: bool
    source: str


@dataclass
class DeckCostLine:
    """One line in a deck cost breakdown."""

    name: str
    count: int
    unit_price: float | None  # None when all_null
    line_total: float | None  # unit_price * count, or None
    quote: PriceQuote


@dataclass
class DeckCost:
    """Deck cost with full honesty: explicit unpriced list, never silently dropped.

    Attributes:
        total_usd: Sum of ``line_total`` for all cards with a price.  Does NOT include
            any imputed value for unpriced cards — the caller sees the real sum.
        lines: One ``DeckCostLine`` per unique card name in the deck.
        unpriced: Names with ``all_null=True`` — excluded from ``total_usd``.
    """

    total_usd: float
    lines: list[DeckCostLine]
    unpriced: list[str]


# ── Raw → PrintingPrice conversion (shared with scryfall.iter_price_rows) ────────────────────────


def _raw_to_printing_price(raw: dict) -> PrintingPrice | None:
    """Convert a raw Scryfall default_cards object to a PrintingPrice, or None to skip.

    Skipped cases:
    - Non-gameplay layouts (tokens, art-series, emblems, etc.)
    - Cards not available in paper (``games`` list does not include "paper")

    The ``is_paper`` flag is set here; downstream queries filter on it so MTGO-only
    printings (like the Vintage Masters Underground Sea with only MTGO tix) are excluded.
    """
    layout = raw.get("layout", "")
    if layout in _NON_GAMEPLAY_LAYOUTS:
        return None

    games = raw.get("games") or []
    is_paper = "paper" in games

    prices = raw.get("prices") or {}
    usd_raw = prices.get("usd")
    usd_foil_raw = prices.get("usd_foil")
    usd_etched_raw = prices.get("usd_etched")
    eur_raw = prices.get("eur")

    def _f(v: str | None) -> float | None:
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    # Detect promo / Secret-Lair printings so the advisor can prefer non-promo.
    promo = bool(raw.get("promo", False))
    set_type = raw.get("set_type", "")
    # Secret Lair drops have set_type "memorabilia" in Scryfall; treat those as promo.
    if set_type in ("memorabilia",):
        promo = True

    name = raw.get("name") or ""
    if not name:
        return None

    return PrintingPrice(
        scryfall_id=raw.get("id", ""),
        name=name,
        set_code=raw.get("set"),
        set_name=raw.get("set_name"),
        collector_number=raw.get("collector_number"),
        usd=_f(usd_raw),
        usd_foil=_f(usd_foil_raw),
        usd_etched=_f(usd_etched_raw),
        eur=_f(eur_raw),
        promo=promo,
        is_paper=is_paper,
        price_date=raw.get("_price_date"),  # injected by iter_price_rows from metadata
    )


# ── Optional override layer ───────────────────────────────────────────────────────────────────────


def _load_overrides(path: Path | None = None) -> dict[str, dict]:
    """Load the optional curated override file, or return {} when absent.

    Override format::

        { "<card name>": {"usd": <float>, "note": "...", "as_of": "YYYY-MM-DD"} }

    The override file is intentionally absent by default (data-driven-over-hand-curated,
    global rule #12).  It is the documented escape hatch for cards Scryfall genuinely cannot
    price (some reserved-list unlisted items).
    """
    p = path or PRICE_OVERRIDE_PATH
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as exc:
        logger.warning("Failed to load price overrides from %s: %s", p, exc)
        return {}


# ── Staleness helper ──────────────────────────────────────────────────────────────────────────────


def _is_stale(price_date: str | None, today: date | None = None) -> bool:
    """Return True when ``price_date`` is older than ``PRICE_STALE_DAYS`` from ``today``."""
    if price_date is None:
        return False  # unknown date → not flagged stale (can't determine)
    if today is None:
        today = date.today()
    try:
        pd = date.fromisoformat(price_date[:10])  # handles "2026-06-13T…" timestamps
        return (today - pd).days > PRICE_STALE_DAYS
    except (ValueError, TypeError):
        return False


# ── Query layer ───────────────────────────────────────────────────────────────────────────────────


def cheapest_printing(con: duckdb.DuckDBPyConnection, name: str) -> PrintingPrice | None:
    """Return the cheapest paper printing of ``name`` by non-null USD price.

    Algorithm:
    1. Filter to ``is_paper=True`` rows for ``name``.
    2. Pick the minimum over ``usd`` (nonfoil); if no nonfoil price exists, fall back to
       ``usd_foil`` then ``usd_etched``.
    3. Return the full ``PrintingPrice`` row so the advisor can tell the user *which*
       printing to buy.

    Returns ``None`` when the card has no rows in ``card_prices``.
    Returns the cheapest row even when all prices are null (caller checks
    ``cheapest_printing.cheapest_usd``).
    """
    # Try nonfoil first.
    row = con.execute(
        """
        SELECT scryfall_id, name, set_code, set_name, collector_number,
               usd, usd_foil, usd_etched, eur, promo, is_paper, price_date
        FROM card_prices
        WHERE name = ? AND is_paper = TRUE AND usd IS NOT NULL
        ORDER BY usd ASC
        LIMIT 1
        """,
        [name],
    ).fetchone()

    if row is None:
        # No nonfoil price: try foil.
        row = con.execute(
            """
            SELECT scryfall_id, name, set_code, set_name, collector_number,
                   usd, usd_foil, usd_etched, eur, promo, is_paper, price_date
            FROM card_prices
            WHERE name = ? AND is_paper = TRUE AND usd_foil IS NOT NULL
            ORDER BY usd_foil ASC
            LIMIT 1
            """,
            [name],
        ).fetchone()

    if row is None:
        # No foil either: try etched.
        row = con.execute(
            """
            SELECT scryfall_id, name, set_code, set_name, collector_number,
                   usd, usd_foil, usd_etched, eur, promo, is_paper, price_date
            FROM card_prices
            WHERE name = ? AND is_paper = TRUE AND usd_etched IS NOT NULL
            ORDER BY usd_etched ASC
            LIMIT 1
            """,
            [name],
        ).fetchone()

    if row is None:
        # All-null: return any paper row so caller gets identity info.
        row = con.execute(
            """
            SELECT scryfall_id, name, set_code, set_name, collector_number,
                   usd, usd_foil, usd_etched, eur, promo, is_paper, price_date
            FROM card_prices
            WHERE name = ? AND is_paper = TRUE
            LIMIT 1
            """,
            [name],
        ).fetchone()

    if row is None:
        return None

    return PrintingPrice(
        scryfall_id=row[0],
        name=row[1],
        set_code=row[2],
        set_name=row[3],
        collector_number=row[4],
        usd=row[5],
        usd_foil=row[6],
        usd_etched=row[7],
        eur=row[8],
        promo=bool(row[9]),
        is_paper=bool(row[10]),
        price_date=row[11],
    )


def price_quote(
    con: duckdb.DuckDBPyConnection,
    name: str,
    *,
    override_path: Path | None = None,
    today: date | None = None,
) -> PriceQuote:
    """Return a ``PriceQuote`` for ``name`` — the honesty-carrying price record.

    Never returns a silent 0.  ``all_null=True`` is the explicit signal that we have no
    paper USD price.  The override layer is applied only when Scryfall yields all-null,
    keeping the data-driven-over-hand-curated invariant.

    Args:
        con: DuckDB connection with ``card_prices`` populated.
        name: Card name (normalized).
        override_path: Override the default ``PRICE_OVERRIDE_PATH`` (for tests).
        today: Override wall-clock date (for deterministic staleness tests).
    """
    cp = cheapest_printing(con, name)

    # Count priced paper printings.
    n_priced_row = con.execute(
        "SELECT count(*) FROM card_prices WHERE name = ? AND is_paper = TRUE AND usd IS NOT NULL",
        [name],
    ).fetchone()
    n_priced = int(n_priced_row[0]) if n_priced_row else 0

    # Determine staleness from the cheapest printing's price_date.
    price_date = cp.price_date if cp is not None else None
    stale = _is_stale(price_date, today)

    # Check for all-null.
    if cp is None or cp.cheapest_usd is None:
        # Try override.
        overrides = _load_overrides(override_path)
        ov = overrides.get(name)
        if ov and ov.get("usd") is not None:
            try:
                ov_usd = float(ov["usd"])
            except (ValueError, TypeError):
                ov_usd = None
            if ov_usd is not None:
                # Build a synthetic PrintingPrice from the override entry.
                ov_pp = PrintingPrice(
                    scryfall_id="override",
                    name=name,
                    set_code=None,
                    set_name=None,
                    collector_number=None,
                    usd=ov_usd,
                    usd_foil=None,
                    usd_etched=None,
                    eur=None,
                    promo=False,
                    is_paper=True,
                    price_date=ov.get("as_of"),
                )
                return PriceQuote(
                    name=name,
                    cheapest_usd=ov_usd,
                    cheapest_printing=ov_pp,
                    n_priced_printings=n_priced,
                    all_null=False,
                    stale=_is_stale(ov.get("as_of"), today),
                    source="override",
                )
        return PriceQuote(
            name=name,
            cheapest_usd=None,
            cheapest_printing=cp,
            n_priced_printings=n_priced,
            all_null=True,
            stale=stale,
            source="scryfall/default_cards",
        )

    return PriceQuote(
        name=name,
        cheapest_usd=cp.cheapest_usd,
        cheapest_printing=cp,
        n_priced_printings=n_priced,
        all_null=False,
        stale=stale,
        source="scryfall/default_cards",
    )


def printing_prices(
    con: duckdb.DuckDBPyConnection, name: str
) -> list[PrintingPrice]:
    """Return every paper printing of ``name`` with a price, sorted cheapest first.

    Used by the advisor to show the full spread (e.g. the $1.50 NPH Dismember vs $33 SL).
    Returns only rows with at least one non-null USD price (nonfoil, foil, or etched).
    """
    rows = con.execute(
        """
        SELECT scryfall_id, name, set_code, set_name, collector_number,
               usd, usd_foil, usd_etched, eur, promo, is_paper, price_date
        FROM card_prices
        WHERE name = ? AND is_paper = TRUE
          AND (usd IS NOT NULL OR usd_foil IS NOT NULL OR usd_etched IS NOT NULL)
        ORDER BY COALESCE(usd, usd_foil, usd_etched) ASC
        """,
        [name],
    ).fetchall()
    return [
        PrintingPrice(
            scryfall_id=r[0],
            name=r[1],
            set_code=r[2],
            set_name=r[3],
            collector_number=r[4],
            usd=r[5],
            usd_foil=r[6],
            usd_etched=r[7],
            eur=r[8],
            promo=bool(r[9]),
            is_paper=bool(r[10]),
            price_date=r[11],
        )
        for r in rows
    ]


def deck_cost(
    con: duckdb.DuckDBPyConnection,
    card_counts: Mapping[str, int],
    *,
    override_path: Path | None = None,
    today: date | None = None,
) -> DeckCost:
    """Compute the total USD cost of a deck with full honesty.

    Sums cheapest_usd × count for every priced card.  Cards with ``all_null`` quotes
    are listed in ``unpriced`` and excluded from ``total_usd`` — they are never silently
    dropped (the caller sees them and can surface a warning).

    Args:
        con: DuckDB connection with ``card_prices`` populated.
        card_counts: Mapping of card name → copy count (e.g. ``{"Brainstorm": 4}``).
        override_path: Override the default ``PRICE_OVERRIDE_PATH`` (for tests).
        today: Override wall-clock date (for deterministic staleness tests).
    """
    lines: list[DeckCostLine] = []
    unpriced: list[str] = []
    total = 0.0

    for name, count in card_counts.items():
        q = price_quote(con, name, override_path=override_path, today=today)
        if q.all_null:
            unpriced.append(name)
            lines.append(DeckCostLine(name=name, count=count, unit_price=None, line_total=None, quote=q))
        else:
            assert q.cheapest_usd is not None
            lt = q.cheapest_usd * count
            total += lt
            lines.append(DeckCostLine(name=name, count=count, unit_price=q.cheapest_usd, line_total=lt, quote=q))

    return DeckCost(total_usd=total, lines=lines, unpriced=unpriced)

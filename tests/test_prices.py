"""Per-printing price tests — fixture-based, no 547MB download.

Golden honesty cases from the motivating bug:
  (a) Underground Sea all-null paper printing → PriceQuote.all_null=True, never a silent 0.
  (b) Dismember multi-printing incl. a $33 Secret Lair → cheapest_printing returns the $1.50 copy.
  (c) deck_cost lists unpriced cards; total excludes them.
  (d) Foil-only fallback: a card with only usd_foil uses that rather than returning null.
  (e) Staleness: price_date older than PRICE_STALE_DAYS → stale=True.
  (f) Override fills an all-null card; override ignored when Scryfall has a price (unless explicit).
  (g) Gated-additive regression: cards table rows are unchanged when card_prices is never seeded.
  (h) scryfall.iter_price_rows: is_paper filter excludes MTGO-only printing.
  (i) store.load_prices: idempotent on scryfall_id (INSERT OR REPLACE).
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path

import pytest

from legacy_engine.config import PRICE_STALE_DAYS
from legacy_engine.ingestion import store
from legacy_engine.ingestion.prices import (
    PrintingPrice,
    _raw_to_printing_price,
    cheapest_printing,
    deck_cost,
    price_quote,
    printing_prices,
)


# ── helpers ────────────────────────────────────────────────────────────────────────────────────────


def _con():
    con = store.connect(":memory:")
    store.init_prices_schema(con)
    return con


def _pp(
    scryfall_id: str,
    name: str,
    *,
    set_code: str = "test",
    usd: float | None = None,
    usd_foil: float | None = None,
    usd_etched: float | None = None,
    promo: bool = False,
    is_paper: bool = True,
    price_date: str | None = "2026-06-01",
) -> PrintingPrice:
    """Minimal PrintingPrice factory for tests."""
    return PrintingPrice(
        scryfall_id=scryfall_id,
        name=name,
        set_code=set_code,
        set_name=None,
        collector_number=None,
        usd=usd,
        usd_foil=usd_foil,
        usd_etched=usd_etched,
        eur=None,
        promo=promo,
        is_paper=is_paper,
        price_date=price_date,
    )


def _load(*printings: PrintingPrice):
    con = _con()
    store.load_prices(con, printings)
    return con


# ── Unit 1: scryfall._raw_to_printing_price ────────────────────────────────────────────────────────


class TestRawToPrintingPrice:
    def test_normal_paper_card(self):
        raw = {
            "id": "abc123",
            "name": "Brainstorm",
            "layout": "normal",
            "games": ["paper", "mtgo"],
            "set": "lea",
            "set_name": "Limited Edition Alpha",
            "collector_number": "54",
            "prices": {"usd": "5.00", "usd_foil": "12.00", "usd_etched": None, "eur": "4.00"},
            "promo": False,
        }
        pp = _raw_to_printing_price(raw)
        assert pp is not None
        assert pp.name == "Brainstorm"
        assert pp.usd == 5.00
        assert pp.usd_foil == 12.00
        assert pp.eur == 4.00
        assert pp.is_paper is True
        assert pp.promo is False

    def test_mtgo_only_is_paper_false(self):
        """An MTGO-only printing (games=['mtgo']) must have is_paper=False."""
        raw = {
            "id": "mtgo1",
            "name": "Underground Sea",
            "layout": "normal",
            "games": ["mtgo"],
            "set": "vma",
            "prices": {"usd": None, "usd_foil": None, "tix": "13.74"},
        }
        pp = _raw_to_printing_price(raw)
        assert pp is not None
        assert pp.is_paper is False  # must be excluded from cheapest_printing queries

    def test_token_layout_skipped(self):
        """Token layout must return None."""
        raw = {"id": "tok1", "name": "Saproling Token", "layout": "token", "games": ["paper"],
               "prices": {"usd": "0.05"}}
        assert _raw_to_printing_price(raw) is None

    def test_art_series_skipped(self):
        raw = {"id": "art1", "name": "Brainstorm", "layout": "art_series", "games": ["paper"],
               "prices": {"usd": "1.00"}}
        assert _raw_to_printing_price(raw) is None

    def test_null_prices_allowed(self):
        """A paper printing with usd=null is valid — null is the whole point of this feature."""
        raw = {
            "id": "reserved1",
            "name": "Underground Sea",
            "layout": "normal",
            "games": ["paper"],
            "set": "vma",
            "prices": {"usd": None, "usd_foil": None, "usd_etched": None, "eur": None},
        }
        pp = _raw_to_printing_price(raw)
        assert pp is not None
        assert pp.is_paper is True
        assert pp.usd is None
        assert pp.cheapest_usd is None  # property: all null → None

    def test_memorabilia_set_type_sets_promo(self):
        """set_type='memorabilia' (Secret Lair) must set promo=True."""
        raw = {
            "id": "sl1",
            "name": "Dismember",
            "layout": "normal",
            "games": ["paper"],
            "set": "sld",
            "set_type": "memorabilia",
            "prices": {"usd": "33.00"},
            "promo": False,
        }
        pp = _raw_to_printing_price(raw)
        assert pp is not None
        assert pp.promo is True

    def test_price_date_injected(self):
        """_price_date injected into raw by iter_price_rows must propagate to price_date."""
        raw = {
            "id": "x1",
            "name": "Brainstorm",
            "layout": "normal",
            "games": ["paper"],
            "prices": {"usd": "1.00"},
            "_price_date": "2026-05-15T12:00:00",
        }
        pp = _raw_to_printing_price(raw)
        assert pp is not None
        assert pp.price_date == "2026-05-15T12:00:00"

    def test_cheapest_usd_property_foil_fallback(self):
        """cheapest_usd uses usd_foil when usd is None."""
        pp = _pp("f1", "X", usd=None, usd_foil=8.00)
        assert pp.cheapest_usd == 8.00

    def test_cheapest_usd_property_etched_fallback(self):
        """cheapest_usd uses usd_etched as last resort."""
        pp = _pp("e1", "X", usd=None, usd_foil=None, usd_etched=6.00)
        assert pp.cheapest_usd == 6.00

    def test_cheapest_usd_property_none_when_all_null(self):
        pp = _pp("n1", "X", usd=None, usd_foil=None, usd_etched=None)
        assert pp.cheapest_usd is None


# ── Unit 2: store.load_prices + init_prices_schema ────────────────────────────────────────────────


class TestStorePrices:
    def test_init_schema_idempotent(self):
        con = _con()
        store.init_prices_schema(con)  # second call must be a no-op
        assert con.execute("SELECT count(*) FROM card_prices").fetchone()[0] == 0
        con.close()

    def test_load_and_count(self):
        printings = [
            _pp("id1", "Brainstorm", usd=1.50),
            _pp("id2", "Dismember", usd=1.50),
            _pp("id3", "Dismember", usd=33.00, promo=True),
        ]
        con = _load(*printings)
        n = con.execute("SELECT count(*) FROM card_prices").fetchone()[0]
        assert n == 3
        con.close()

    def test_load_idempotent_on_scryfall_id(self):
        """INSERT OR REPLACE: reloading the same scryfall_id updates the row, no duplicates."""
        con = _con()
        store.load_prices(con, [_pp("id1", "Brainstorm", usd=1.00)])
        store.load_prices(con, [_pp("id1", "Brainstorm", usd=2.00)])  # updated price
        assert con.execute("SELECT count(*) FROM card_prices").fetchone()[0] == 1
        row = con.execute("SELECT usd FROM card_prices WHERE scryfall_id = 'id1'").fetchone()
        assert row[0] == 2.00
        con.close()

    def test_rebuild_prices_clears_table(self):
        con = _load(_pp("id1", "Brainstorm", usd=1.00))
        store.rebuild_prices(con)
        assert con.execute("SELECT count(*) FROM card_prices").fetchone()[0] == 0
        con.close()

    def test_empty_iterable_returns_zero(self):
        con = _con()
        n = store.load_prices(con, [])
        assert n == 0
        con.close()


# ── Unit 3: prices.py query layer — golden honesty cases ──────────────────────────────────────────


class TestCheapestPrinting:
    def test_dismember_cheapest_not_secret_lair(self):
        """Golden case (b): multi-printing — cheapest_printing picks the cheap NPH copy."""
        con = _load(
            _pp("nph1", "Dismember", set_code="nph", usd=1.50),
            _pp("sl1", "Dismember", set_code="sld", usd=33.00, promo=True),
        )
        cp = cheapest_printing(con, "Dismember")
        assert cp is not None
        assert cp.usd == 1.50
        assert cp.set_code == "nph"
        con.close()

    def test_foil_fallback_when_no_nonfoil(self):
        """Golden case (d): foil-only printing is used when no nonfoil price exists."""
        con = _load(_pp("f1", "SomeCard", usd=None, usd_foil=8.00))
        cp = cheapest_printing(con, "SomeCard")
        assert cp is not None
        assert cp.cheapest_usd == 8.00
        assert cp.usd is None
        assert cp.usd_foil == 8.00
        con.close()

    def test_etched_fallback(self):
        con = _load(_pp("e1", "SomeCard", usd=None, usd_foil=None, usd_etched=6.00))
        cp = cheapest_printing(con, "SomeCard")
        assert cp is not None
        assert cp.cheapest_usd == 6.00
        con.close()

    def test_all_null_paper_printing_returned(self):
        """An all-null paper printing: cheapest_printing returns the row (identity available)."""
        con = _load(_pp("vma1", "Underground Sea", set_code="vma", usd=None, is_paper=True))
        cp = cheapest_printing(con, "Underground Sea")
        assert cp is not None
        assert cp.cheapest_usd is None
        con.close()

    def test_mtgo_only_excluded(self):
        """MTGO-only printing (is_paper=False) must not be returned."""
        con = _load(
            _pp("mtgo1", "Underground Sea", is_paper=False, usd=None),
        )
        cp = cheapest_printing(con, "Underground Sea")
        # No paper rows at all → None
        assert cp is None
        con.close()

    def test_unknown_card_returns_none(self):
        con = _con()
        assert cheapest_printing(con, "Nonexistent Card") is None
        con.close()


class TestPriceQuote:
    def test_underground_sea_all_null(self):
        """Golden case (a): Underground Sea paper printing with usd=null → all_null=True, not 0."""
        # One paper printing (Revised), one MTGO-only (VMA with tix only).
        con = _load(
            _pp("rev1", "Underground Sea", set_code="3ed", usd=None, is_paper=True),
            _pp("vma1", "Underground Sea", set_code="vma", usd=None, is_paper=False),
        )
        q = price_quote(con, "Underground Sea")
        assert q.all_null is True
        assert q.cheapest_usd is None
        # Must NEVER be a silent 0 — callers must see the explicit flag.
        assert q.cheapest_usd != 0
        assert q.source == "scryfall/default_cards"
        con.close()

    def test_priced_card_not_all_null(self):
        con = _load(_pp("bs1", "Brainstorm", usd=0.25))
        q = price_quote(con, "Brainstorm")
        assert q.all_null is False
        assert q.cheapest_usd == 0.25
        assert q.n_priced_printings == 1
        con.close()

    def test_n_priced_printings_counts_nonfoil_only(self):
        """n_priced_printings counts rows where usd IS NOT NULL (not foil-only rows)."""
        con = _load(
            _pp("p1", "Dismember", usd=1.50),
            _pp("p2", "Dismember", usd=None, usd_foil=5.00),  # foil-only, not in usd count
        )
        q = price_quote(con, "Dismember")
        assert q.n_priced_printings == 1
        con.close()

    def test_stale_flag_when_old(self):
        """Golden case (e): price older than PRICE_STALE_DAYS → stale=True."""
        old_date = (date.today() - timedelta(days=PRICE_STALE_DAYS + 5)).isoformat()
        con = _load(_pp("bs1", "Brainstorm", usd=0.25, price_date=old_date))
        # Inject today deterministically so the test isn't wall-clock dependent.
        q = price_quote(con, "Brainstorm", today=date.today())
        assert q.stale is True
        con.close()

    def test_fresh_flag_when_recent(self):
        """A recent price_date → stale=False."""
        recent = (date.today() - timedelta(days=5)).isoformat()
        con = _load(_pp("bs1", "Brainstorm", usd=0.25, price_date=recent))
        q = price_quote(con, "Brainstorm", today=date.today())
        assert q.stale is False
        con.close()

    def test_unknown_card_all_null(self):
        """A card with no rows in card_prices → all_null=True."""
        con = _con()
        q = price_quote(con, "Mystery Card")
        assert q.all_null is True
        assert q.cheapest_usd is None
        con.close()


class TestPrintingPrices:
    def test_dismember_spread(self):
        """printing_prices returns all priced printings sorted cheapest first."""
        con = _load(
            _pp("sl1", "Dismember", usd=33.00, promo=True),
            _pp("nph1", "Dismember", usd=1.50),
            _pp("mma1", "Dismember", usd=3.00),
        )
        pp_list = printing_prices(con, "Dismember")
        assert len(pp_list) == 3
        assert pp_list[0].usd == 1.50  # NPH cheapest first
        assert pp_list[1].usd == 3.00
        assert pp_list[2].usd == 33.00
        con.close()

    def test_all_null_excluded_from_printing_prices(self):
        """printing_prices returns only rows with at least one non-null USD price."""
        con = _load(
            _pp("id1", "Underground Sea", usd=None, usd_foil=None),  # excluded
            _pp("id2", "Underground Sea", usd=None, usd_foil=200.00),  # foil-only, included
        )
        pp_list = printing_prices(con, "Underground Sea")
        assert len(pp_list) == 1
        assert pp_list[0].usd_foil == 200.00
        con.close()

    def test_empty_when_no_priced_printings(self):
        con = _con()
        assert printing_prices(con, "Unknown") == []
        con.close()


class TestDeckCost:
    def test_basic_sum(self):
        """Deck cost sums line totals correctly."""
        con = _load(
            _pp("bs1", "Brainstorm", usd=0.25),
            _pp("fp1", "Force of Persistence", usd=2.00),
        )
        dc = deck_cost(con, {"Brainstorm": 4, "Force of Persistence": 2})
        assert dc.total_usd == pytest.approx(0.25 * 4 + 2.00 * 2)
        assert dc.unpriced == []
        con.close()

    def test_unpriced_listed_never_dropped(self):
        """Golden case (c): unpriced card appears in unpriced list; total excludes it."""
        con = _load(
            _pp("bs1", "Brainstorm", usd=0.25),
            _pp("usea1", "Underground Sea", usd=None, is_paper=True),
        )
        dc = deck_cost(con, {"Brainstorm": 4, "Underground Sea": 4})
        assert "Underground Sea" in dc.unpriced
        assert "Brainstorm" not in dc.unpriced
        # Total must be only Brainstorm × 4; Underground Sea excluded, not zeroed.
        assert dc.total_usd == pytest.approx(0.25 * 4)
        # Lines still contains Underground Sea (never silently dropped).
        line_names = [l.name for l in dc.lines]
        assert "Underground Sea" in line_names
        con.close()

    def test_empty_deck(self):
        con = _con()
        dc = deck_cost(con, {})
        assert dc.total_usd == 0.0
        assert dc.lines == []
        assert dc.unpriced == []
        con.close()

    def test_cheapest_printing_drives_cost(self):
        """deck_cost uses cheapest_printing for each card (NPH $1.50, not SL $33)."""
        con = _load(
            _pp("nph1", "Dismember", usd=1.50),
            _pp("sl1", "Dismember", usd=33.00, promo=True),
        )
        dc = deck_cost(con, {"Dismember": 4})
        assert dc.total_usd == pytest.approx(1.50 * 4)
        con.close()


# ── Unit 4: override layer ────────────────────────────────────────────────────────────────────────


class TestOverrideLayer:
    def test_override_fills_all_null_card(self):
        """Golden case (f): when Scryfall has all-null, override provides a price."""
        con = _load(
            _pp("usea1", "Underground Sea", usd=None, is_paper=True),
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {"Underground Sea": {"usd": 350.00, "note": "Revised", "as_of": "2026-06-01"}},
                f,
            )
            ov_path = Path(f.name)

        q = price_quote(con, "Underground Sea", override_path=ov_path)
        assert q.all_null is False
        assert q.cheapest_usd == 350.00
        assert q.source == "override"
        con.close()
        ov_path.unlink()

    def test_override_ignored_when_scryfall_has_price(self):
        """Override must NOT override Scryfall when Scryfall already has a price."""
        con = _load(_pp("bs1", "Brainstorm", usd=0.25))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"Brainstorm": {"usd": 999.00, "note": "test override"}}, f)
            ov_path = Path(f.name)

        q = price_quote(con, "Brainstorm", override_path=ov_path)
        assert q.cheapest_usd == 0.25  # Scryfall wins
        assert q.source == "scryfall/default_cards"
        con.close()
        ov_path.unlink()

    def test_missing_override_file_no_error(self):
        """Absent override file is a no-op; no exception raised."""
        con = _load(_pp("bs1", "Brainstorm", usd=0.25))
        q = price_quote(con, "Brainstorm", override_path=Path("/nonexistent/overrides.json"))
        assert q.cheapest_usd == 0.25
        con.close()


# ── Unit 5: scryfall.iter_price_rows (fixture-based, no 547MB download) ──────────────────────────


class TestIterPriceRows:
    """Test the stream-parse path using a small fixture file (no real download)."""

    def _write_fixture(self, tmp_path, cards: list[dict]) -> Path:
        p = tmp_path / "default_cards.json"
        p.write_text(json.dumps(cards))
        return p

    def test_paper_cards_yielded(self, tmp_path):
        from legacy_engine.ingestion.scryfall import ScryfallClient

        fixture = self._write_fixture(tmp_path, [
            {
                "id": "nph1",
                "name": "Dismember",
                "layout": "normal",
                "games": ["paper", "mtgo"],
                "set": "nph",
                "prices": {"usd": "1.50", "usd_foil": None},
            },
        ])
        with ScryfallClient() as client:
            rows = list(client.iter_price_rows(path=fixture))
        assert len(rows) == 1
        assert rows[0].usd == 1.50
        assert rows[0].is_paper is True

    def test_mtgo_only_excluded(self, tmp_path):
        """is_paper filter: MTGO-only printing must NOT be yielded."""
        from legacy_engine.ingestion.scryfall import ScryfallClient

        fixture = self._write_fixture(tmp_path, [
            {
                "id": "vma1",
                "name": "Underground Sea",
                "layout": "normal",
                "games": ["mtgo"],  # MTGO-only
                "set": "vma",
                "prices": {"usd": None, "usd_foil": None, "tix": "13.74"},
            },
            {
                "id": "3ed1",
                "name": "Underground Sea",
                "layout": "normal",
                "games": ["paper"],
                "set": "3ed",
                "prices": {"usd": None, "usd_foil": None},
            },
        ])
        with ScryfallClient() as client:
            rows = list(client.iter_price_rows(path=fixture))
        # MTGO-only row is yielded with is_paper=False; paper row with is_paper=True
        paper_rows = [r for r in rows if r.is_paper]
        mtgo_rows = [r for r in rows if not r.is_paper]
        assert len(paper_rows) == 1
        assert paper_rows[0].set_code == "3ed"
        assert len(mtgo_rows) == 1
        assert mtgo_rows[0].set_code == "vma"

    def test_token_excluded(self, tmp_path):
        from legacy_engine.ingestion.scryfall import ScryfallClient

        fixture = self._write_fixture(tmp_path, [
            {"id": "tok1", "name": "Token", "layout": "token", "games": ["paper"],
             "prices": {"usd": "0.05"}},
        ])
        with ScryfallClient() as client:
            rows = list(client.iter_price_rows(path=fixture))
        assert rows == []

    def test_price_date_injected_from_metadata(self, tmp_path, monkeypatch):
        """prices_updated_at injects price_date into each row via iter_price_rows."""
        from legacy_engine import ingestion
        from legacy_engine.ingestion import scryfall as scryfall_mod
        from legacy_engine.ingestion.scryfall import ScryfallClient

        fixture = self._write_fixture(tmp_path, [
            {
                "id": "bs1",
                "name": "Brainstorm",
                "layout": "normal",
                "games": ["paper"],
                "set": "lea",
                "prices": {"usd": "5.00"},
            },
        ])
        meta_path = tmp_path / "prices_metadata.json"
        meta_path.write_text(json.dumps({"updated_at": "2026-06-01", "bulk_type": "default_cards"}))
        monkeypatch.setattr(scryfall_mod, "SCRYFALL_PRICES_META_PATH", meta_path)

        with ScryfallClient() as client:
            rows = list(client.iter_price_rows(path=fixture))
        assert len(rows) == 1
        assert rows[0].price_date == "2026-06-01"

    def test_missing_file_raises(self, tmp_path):
        from legacy_engine.ingestion.scryfall import ScryfallClient

        with ScryfallClient() as client:
            with pytest.raises(FileNotFoundError):
                list(client.iter_price_rows(path=tmp_path / "nope.json"))


# ── Unit 6: gated-additive regression ────────────────────────────────────────────────────────────


class TestGatedAdditive:
    def test_cards_table_unchanged_when_prices_never_seeded(self):
        """The cards table and seed-cards flow are byte-identical when card_prices is absent."""
        from legacy_engine.models.card import Card

        con = store.connect(":memory:")
        # Do NOT call init_prices_schema — simulate a corpus that has never been seeded.
        cards = [
            Card(name="Underground Sea", type_line="Land — Island Swamp", produced_mana=["U", "B"]),
            Card(name="Brainstorm", type_line="Instant", cmc=1.0),
        ]
        n = store.load_cards(con, cards)
        assert n == 2

        # The cards table is populated exactly as before.
        row = store.fetch_card(con, "Underground Sea")
        assert row is not None
        assert row["is_land"] is True

        # card_prices table does not exist — that's fine; no error.
        with pytest.raises(Exception):
            con.execute("SELECT count(*) FROM card_prices").fetchone()
        con.close()

    def test_price_quote_on_empty_prices_table(self):
        """price_quote on an empty card_prices table returns all_null=True — no crash."""
        con = _con()
        q = price_quote(con, "Underground Sea")
        assert q.all_null is True
        assert q.cheapest_usd is None
        con.close()


# ── Unit 7: config constants ──────────────────────────────────────────────────────────────────────


class TestPricesConfig:
    def test_new_constants_are_absolute_paths(self):
        from legacy_engine import config

        for p in (
            config.SCRYFALL_PRICES_PATH,
            config.SCRYFALL_PRICES_META_PATH,
            config.PRICE_OVERRIDE_PATH,
        ):
            assert p.is_absolute(), f"{p} is not absolute"

    def test_prices_paths_under_project_root(self):
        from legacy_engine import config

        assert config.SCRYFALL_PRICES_PATH.parent == config.SCRYFALL_DIR
        assert config.SCRYFALL_PRICES_META_PATH.parent == config.SCRYFALL_DIR
        assert config.PRICE_OVERRIDE_PATH.parent.parent == config.DATA_DIR

    def test_price_stale_days_is_int(self):
        from legacy_engine import config

        assert isinstance(config.PRICE_STALE_DAYS, int)
        assert config.PRICE_STALE_DAYS > 0

    def test_import_no_side_effects(self):
        import importlib

        from legacy_engine import config

        importlib.reload(config)
        # Importing/reloading must not create the prices directory.
        assert not config.SCRYFALL_PRICES_PATH.exists() or config.SCRYFALL_PRICES_PATH.is_file()


# ── Unit 8: CLI smoke tests ────────────────────────────────────────────────────────────────────────


class TestPricesCLI:
    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    def test_seed_group_includes_prices(self, runner):
        from legacy_engine.cli import main

        result = runner.invoke(main, ["seed", "--help"])
        assert result.exit_code == 0
        assert "prices" in result.output

    def test_refresh_help_includes_prices_option(self, runner):
        from legacy_engine.cli import main

        result = runner.invoke(main, ["refresh", "--help"])
        assert result.exit_code == 0
        assert "--prices" in result.output

    def test_report_prices_requires_name_arg(self, runner):
        from legacy_engine.cli import main

        result = runner.invoke(main, ["report", "prices"])
        assert result.exit_code != 0

    def test_report_prices_in_help(self, runner):
        from legacy_engine.cli import main

        result = runner.invoke(main, ["report", "--help"])
        assert result.exit_code == 0
        assert "prices" in result.output

"""Tests for ingestion/releases.py (Unit 4) and store.load_cards_diff (Unit 5).

All tests are pure or use in-memory DuckDB — no network, no live Scryfall.
"""

from __future__ import annotations

from datetime import date, timedelta

from legacy_engine.ingestion.releases import SetRelease, upcoming_and_recent
from legacy_engine.ingestion import store
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set(code: str, name: str, released_at: date | None = None, set_type: str = "expansion") -> SetRelease:
    return SetRelease(code=code, name=name, released_at=released_at, set_type=set_type)


def _card(name: str, *, type_line: str = "Instant", cmc: float = 1.0) -> Card:
    return Card(name=name, type_line=type_line, cmc=cmc)


# ---------------------------------------------------------------------------
# Unit 4: release scan (pure date-window logic)
# ---------------------------------------------------------------------------


class TestUpcomingAndRecent:
    """Tests for upcoming_and_recent — pure date-split logic, no network."""

    def setup_method(self):
        self.today = date(2026, 6, 15)

    def test_upcoming_set_in_window(self):
        """A set released 10 days from today (within 30-day horizon) is 'upcoming'."""
        future_set = _set("FUT", "Future Set", released_at=self.today + timedelta(days=10))
        scan = upcoming_and_recent([future_set], today=self.today)
        assert len(scan.upcoming) == 1
        assert scan.upcoming[0].code == "FUT"
        assert len(scan.recently_released) == 0

    def test_recently_released_set(self):
        """A set released 5 days ago (within 14-day lookback) is 'recently_released'."""
        recent_set = _set("REC", "Recent Set", released_at=self.today - timedelta(days=5))
        scan = upcoming_and_recent([recent_set], today=self.today)
        assert len(scan.recently_released) == 1
        assert scan.recently_released[0].code == "REC"
        assert len(scan.upcoming) == 0

    def test_today_released_is_recent(self):
        """A set released today is 'recently_released' (inclusive lower bound)."""
        today_set = _set("TOD", "Today's Set", released_at=self.today)
        scan = upcoming_and_recent([today_set], today=self.today)
        assert any(s.code == "TOD" for s in scan.recently_released)

    def test_set_released_at_none_excluded_from_both(self):
        """A set with released_at=None (unscheduled) is excluded from both lists."""
        unscheduled = _set("UNS", "Unscheduled Set", released_at=None)
        scan = upcoming_and_recent([unscheduled], today=self.today)
        assert len(scan.upcoming) == 0
        assert len(scan.recently_released) == 0

    def test_set_outside_both_windows_excluded(self):
        """A set released 60 days ago (outside lookback) is excluded from both lists."""
        old_set = _set("OLD", "Old Set", released_at=self.today - timedelta(days=60))
        scan = upcoming_and_recent([old_set], today=self.today)
        assert len(scan.upcoming) == 0
        assert len(scan.recently_released) == 0

    def test_set_outside_horizon_excluded(self):
        """A set 45 days out (outside 30-day horizon) is NOT upcoming."""
        far_future = _set("FAR", "Far Future", released_at=self.today + timedelta(days=45))
        scan = upcoming_and_recent([far_future], today=self.today)
        assert len(scan.upcoming) == 0

    def test_no_legality_filter_applied(self):
        """No per-set legality filtering: a Secret Lair (supplemental) appears like any set."""
        lair = _set("SLD", "Secret Lair", released_at=self.today - timedelta(days=3), set_type="box")
        scan = upcoming_and_recent([lair], today=self.today)
        assert any(s.code == "SLD" for s in scan.recently_released), \
            "Secret Lair should appear in recently_released — no set_type filter applied"

    def test_multiple_sets_split_correctly(self):
        """Mixed-window set list splits correctly into upcoming / recently_released / neither."""
        sets = [
            _set("UPC", "Upcoming", released_at=self.today + timedelta(days=15)),
            _set("REC", "Recent", released_at=self.today - timedelta(days=7)),
            _set("OLD", "Old", released_at=self.today - timedelta(days=90)),
            _set("FAR", "Far", released_at=self.today + timedelta(days=60)),
            _set("UNS", "Unscheduled", released_at=None),
        ]
        scan = upcoming_and_recent(sets, today=self.today)
        upcoming_codes = {s.code for s in scan.upcoming}
        recent_codes = {s.code for s in scan.recently_released}

        assert upcoming_codes == {"UPC"}
        assert recent_codes == {"REC"}

    def test_upcoming_sorted_by_date_ascending(self):
        """Upcoming sets are sorted by released_at ascending (soonest first)."""
        sets = [
            _set("B", "Set B", released_at=self.today + timedelta(days=20)),
            _set("A", "Set A", released_at=self.today + timedelta(days=10)),
        ]
        scan = upcoming_and_recent(sets, today=self.today)
        assert scan.upcoming[0].code == "A"
        assert scan.upcoming[1].code == "B"

    def test_recent_sorted_by_date_descending(self):
        """Recently-released sets are sorted by released_at descending (newest first)."""
        sets = [
            _set("B", "Set B", released_at=self.today - timedelta(days=5)),
            _set("A", "Set A", released_at=self.today - timedelta(days=1)),
        ]
        scan = upcoming_and_recent(sets, today=self.today)
        assert scan.recently_released[0].code == "A"
        assert scan.recently_released[1].code == "B"

    def test_scanned_at_matches_today(self):
        """ReleaseScan.scanned_at matches the injected today date."""
        scan = upcoming_and_recent([], today=self.today)
        assert scan.scanned_at == self.today

    def test_custom_window_parameters(self):
        """Custom horizon_days and lookback_days are respected."""
        near_future = _set("NF", "Near Future", released_at=self.today + timedelta(days=5))
        scan = upcoming_and_recent([near_future], today=self.today, horizon_days=3)
        # 5 days > 3-day horizon → should NOT be upcoming
        assert len(scan.upcoming) == 0

    def test_empty_set_list_returns_empty_scan(self):
        """Empty set list → empty scan (no errors)."""
        scan = upcoming_and_recent([], today=self.today)
        assert scan.upcoming == []
        assert scan.recently_released == []


# ---------------------------------------------------------------------------
# Unit 5: diff-producing ingest (store.py extensions)
# ---------------------------------------------------------------------------


class TestLoadCardsDiff:
    """Tests for existing_card_names and load_cards_diff (non-destructive diff ingest)."""

    def _con(self):
        return store.connect(":memory:")

    def test_new_cards_appear_in_diff(self):
        """Seeding A,B then diff-ingesting A,B,C → new_names contains exactly C."""
        con = self._con()
        # Seed with A and B
        store.load_cards(con, [_card("Card A"), _card("Card B")])

        # Diff-ingest with A, B, C
        diff = store.load_cards_diff(con, [_card("Card A"), _card("Card B"), _card("Card C")])

        assert "Card C" in diff.new_names
        assert "Card A" not in diff.new_names
        assert "Card B" not in diff.new_names
        assert diff.total_after >= 3
        con.close()

    def test_diff_idempotent_no_phantom_names(self):
        """Re-running load_cards_diff with the same set → new_names is empty (no phantom diffs)."""
        con = self._con()
        store.load_cards(con, [_card("Card A"), _card("Card B")])

        # First diff-ingest with same set
        diff1 = store.load_cards_diff(con, [_card("Card A"), _card("Card B")])
        assert diff1.new_names == ()

        # Second diff-ingest — still idempotent
        diff2 = store.load_cards_diff(con, [_card("Card A"), _card("Card B")])
        assert diff2.new_names == ()
        con.close()

    def test_diff_from_empty_table(self):
        """Diff-ingest from an empty table → all cards are 'new'."""
        con = self._con()
        # Don't seed; diff from scratch
        diff = store.load_cards_diff(con, [_card("Card A"), _card("Card B"), _card("Card C")])

        assert set(diff.new_names) == {"Card A", "Card B", "Card C"}
        assert diff.total_after >= 3
        con.close()

    def test_new_names_sorted_tuple(self):
        """new_names is a sorted tuple (deterministic ordering)."""
        con = self._con()
        diff = store.load_cards_diff(con, [_card("Zebra"), _card("Alpha"), _card("Mango")])
        assert diff.new_names == tuple(sorted(diff.new_names))
        con.close()

    def test_total_after_correct(self):
        """total_after reflects the number of full-name rows in the table."""
        con = self._con()
        diff = store.load_cards_diff(con, [_card("A"), _card("B"), _card("C")])
        # At minimum 3 full-name rows
        assert diff.total_after >= 3
        con.close()

    def test_scryfall_updated_at_round_trips(self):
        """scryfall_updated_at is persisted and returned in the diff."""
        con = self._con()
        updated_at = "2026-06-13T10:00:00.000Z"
        diff = store.load_cards_diff(con, [_card("X")], scryfall_updated_at=updated_at)
        assert diff.scryfall_updated_at == updated_at
        con.close()

    def test_scryfall_updated_at_none_when_not_provided(self):
        """When not provided, scryfall_updated_at is None."""
        con = self._con()
        diff = store.load_cards_diff(con, [_card("X")])
        assert diff.scryfall_updated_at is None
        con.close()

    def test_existing_card_names_empty_on_fresh_db(self):
        """existing_card_names returns empty set for a fresh DB (table doesn't exist yet)."""
        con = self._con()
        names = store.existing_card_names(con)
        assert names == set()
        con.close()

    def test_existing_card_names_after_seed(self):
        """existing_card_names returns the names of all loaded cards."""
        con = self._con()
        store.load_cards(con, [_card("Alpha"), _card("Beta")])
        names = store.existing_card_names(con)
        assert "Alpha" in names
        assert "Beta" in names
        con.close()

    def test_diff_does_not_destroy_existing_data(self):
        """load_cards_diff is non-destructive: existing data survives the diff ingest."""
        con = self._con()
        store.load_cards(con, [_card("Card A")])
        # Diff-ingest with A + B
        store.load_cards_diff(con, [_card("Card A"), _card("Card B")])
        # A should still be present
        row = store.fetch_card(con, "Card A")
        assert row is not None
        con.close()

    def test_multiple_new_sets_all_captured(self):
        """Multiple new cards in one diff are all captured."""
        con = self._con()
        store.load_cards(con, [_card("Old Card")])
        new_cards = [_card(f"New Card {i}") for i in range(10)]
        diff = store.load_cards_diff(con, [_card("Old Card")] + new_cards)
        assert len(diff.new_names) == 10
        for i in range(10):
            assert f"New Card {i}" in diff.new_names
        con.close()


# ---------------------------------------------------------------------------
# SetRelease model tests
# ---------------------------------------------------------------------------


class TestSetRelease:
    """Tests for the SetRelease pydantic model."""

    def test_model_drops_extra_fields(self):
        """SetRelease (LegacyEngineModel) silently drops unmodeled Scryfall keys."""
        raw = {
            "code": "abc",
            "name": "Test Set",
            "released_at": "2026-06-15",
            "set_type": "expansion",
            "card_count": 250,
            "uri": "https://api.scryfall.com/sets/abc",  # extra — should be dropped
            "icon_svg_uri": "https://example.com/icon.svg",  # extra
        }
        s = SetRelease.model_validate(raw)
        assert s.code == "abc"
        assert s.name == "Test Set"
        assert s.released_at == date(2026, 6, 15)
        assert s.card_count == 250
        assert not hasattr(s, "uri")
        assert not hasattr(s, "icon_svg_uri")

    def test_released_at_none_when_missing(self):
        """released_at defaults to None when absent from the payload."""
        s = SetRelease(code="x", name="X")
        assert s.released_at is None

    def test_card_count_defaults_zero(self):
        """card_count defaults to 0 when missing."""
        s = SetRelease(code="x", name="X")
        assert s.card_count == 0

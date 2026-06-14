"""Tests for collection/allocation.py — pure buildability/contention/free-binder.

All tests use hand-built dicts (objective-search-split pattern): no DB, no FS.
"""

from __future__ import annotations

import pytest

from legacy_engine.collection.allocation import (
    BuildabilityReport,
    ContentionEntry,
    aggregate_owned,
    buildability,
    contention,
    free_binder,
)
from legacy_engine.models.collection import InventoryEntry


# ---------------------------------------------------------------------------
# buildability
# ---------------------------------------------------------------------------


class TestBuildability:
    def test_buildable_when_enough(self):
        owned = {"Brainstorm": 4, "Force of Will": 4, "Island": 10}
        main = {"Brainstorm": 4, "Force of Will": 4, "Island": 10}
        side = {}
        r = buildability(main, side, owned, deck_name="Test")
        assert r.buildable is True
        assert r.missing == {}

    def test_missing_when_insufficient(self):
        owned = {"Brainstorm": 2, "Force of Will": 4}
        main = {"Brainstorm": 4, "Force of Will": 4}
        side = {}
        r = buildability(main, side, owned)
        assert r.buildable is False
        assert r.missing == {"Brainstorm": 2}

    def test_missing_from_sideboard(self):
        owned = {"Surgical Extraction": 1}
        main = {}
        side = {"Surgical Extraction": 3}
        r = buildability(main, side, owned)
        assert r.buildable is False
        assert r.missing == {"Surgical Extraction": 2}

    def test_not_owned_at_all(self):
        owned = {}
        main = {"Brainstorm": 4}
        r = buildability(main, {}, owned)
        assert r.buildable is False
        assert r.missing == {"Brainstorm": 4}

    def test_combined_main_plus_side(self):
        """A card that appears in both main and side: combined count checked."""
        owned = {"Ponder": 4}
        main = {"Ponder": 3}
        side = {"Ponder": 1}
        r = buildability(main, side, owned)
        assert r.buildable is True

    def test_combined_over_limit(self):
        owned = {"Ponder": 3}
        main = {"Ponder": 3}
        side = {"Ponder": 1}
        r = buildability(main, side, owned)
        assert r.buildable is False
        assert r.missing["Ponder"] == 1

    def test_deck_name_carried(self):
        r = buildability({"X": 1}, {}, {"X": 1}, deck_name="My Deck")
        assert r.deck_name == "My Deck"

    def test_empty_deck_is_buildable(self):
        r = buildability({}, {}, {})
        assert r.buildable is True
        assert r.missing == {}


# ---------------------------------------------------------------------------
# free_binder
# ---------------------------------------------------------------------------


class TestFreeBinder:
    def test_all_free_when_none_allocated(self):
        owned = {"Brainstorm": 4, "Force of Will": 4}
        result = free_binder(owned, {})
        assert result == {"Brainstorm": 4, "Force of Will": 4}

    def test_reduces_by_allocated(self):
        owned = {"Brainstorm": 4}
        allocated = {"Brainstorm": 3}
        result = free_binder(owned, allocated)
        assert result == {"Brainstorm": 1}

    def test_over_committed_floors_at_zero(self):
        owned = {"Brainstorm": 2}
        allocated = {"Brainstorm": 5}
        result = free_binder(owned, allocated)
        assert result == {"Brainstorm": 0}

    def test_cards_not_in_owned_excluded(self):
        """free_binder only reports cards from owned_counts."""
        owned = {"Brainstorm": 4}
        allocated = {"Force of Will": 2}  # not in owned
        result = free_binder(owned, allocated)
        assert "Force of Will" not in result
        assert result == {"Brainstorm": 4}

    def test_empty_inputs(self):
        assert free_binder({}, {}) == {}


# ---------------------------------------------------------------------------
# contention
# ---------------------------------------------------------------------------


class TestContention:
    def test_no_contention_when_enough(self):
        per_deck = {
            "Deck A": {"Brainstorm": 4},
            "Deck B": {"Force of Will": 4},
        }
        owned = {"Brainstorm": 4, "Force of Will": 4}
        result = contention(per_deck, owned)
        assert result == []

    def test_contention_when_over_committed(self):
        per_deck = {
            "Deck A": {"Brainstorm": 4},
            "Deck B": {"Brainstorm": 4},
        }
        owned = {"Brainstorm": 4}
        result = contention(per_deck, owned)
        assert len(result) == 1
        entry = result[0]
        assert entry.name == "Brainstorm"
        assert entry.owned == 4
        assert entry.total_claimed == 8
        assert entry.shortfall == 4
        assert sorted(entry.decks_claiming) == ["Deck A", "Deck B"]

    def test_sorted_by_shortfall_desc(self):
        per_deck = {
            "Deck A": {"X": 4, "Y": 2},
            "Deck B": {"X": 4, "Y": 2},
        }
        owned = {"X": 2, "Y": 2}
        result = contention(per_deck, owned)
        # X shortfall = 6, Y shortfall = 2 → X first
        assert result[0].name == "X"
        assert result[1].name == "Y"

    def test_only_over_committed_reported(self):
        per_deck = {
            "Deck A": {"A": 2, "B": 4},
            "Deck B": {"A": 2},
        }
        owned = {"A": 4, "B": 4}  # A exactly covered (4 claimed, 4 owned), B over (4 claimed, 4 owned)
        result = contention(per_deck, owned)
        names = [e.name for e in result]
        # A: claimed=4, owned=4 → no contention
        # B: claimed=4 from Deck A, owned=4 → no contention
        assert names == []

    def test_empty_decks(self):
        assert contention({}, {"Brainstorm": 4}) == []


# ---------------------------------------------------------------------------
# aggregate_owned
# ---------------------------------------------------------------------------


class TestAggregateOwned:
    def test_name_only(self):
        entries = [
            InventoryEntry(name="Dismember", count=2, printing="mh3:62"),
            InventoryEntry(name="Dismember", count=1, printing="mm2:80"),
            InventoryEntry(name="Brainstorm", count=4),
        ]
        assert aggregate_owned(entries, name="Dismember") == 3
        assert aggregate_owned(entries, name="Brainstorm") == 4

    def test_printing_filter(self):
        entries = [
            InventoryEntry(name="Dismember", count=2, printing="mh3:62"),
            InventoryEntry(name="Dismember", count=1, printing="mm2:80"),
        ]
        assert aggregate_owned(entries, name="Dismember", printing="mh3:62") == 2
        assert aggregate_owned(entries, name="Dismember", printing="mm2:80") == 1

    def test_missing_card(self):
        assert aggregate_owned([], name="Brainstorm") == 0

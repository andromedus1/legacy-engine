"""Tests for printing/condition-aware allocation (Story 2).

Pure-layer table tests — no DB, no filesystem.  Covers:
  - PhysicalKey identity and equality
  - inventory_to_physical / deck_to_physical builders
  - free_binder_physical: printing-granular free counts
  - contention_physical: printing-specific overlap reporting
  - Name-level fallback: existing buildability/free_binder/contention unchanged
  - Mixed presence: inventory with some entries having printing and some not

All tests follow the objective-search-split pattern: hand-built input dicts,
pure function output, no side effects.
"""

from __future__ import annotations

import pytest

from legacy_engine.collection.allocation import (
    ContentionEntry,
    PhysicalKey,
    aggregate_owned,
    buildability,
    contention,
    contention_physical,
    deck_to_physical,
    free_binder,
    free_binder_physical,
    inventory_to_physical,
)
from legacy_engine.models.collection import DeckCardRef, InventoryEntry


# ---------------------------------------------------------------------------
# PhysicalKey — identity / equality
# ---------------------------------------------------------------------------


class TestPhysicalKey:
    def test_default_fields(self):
        k = PhysicalKey(name="Dismember")
        assert k.printing is None
        assert k.condition is None
        assert k.foil is False

    def test_full_identity(self):
        k1 = PhysicalKey("Dismember", "mh3:62", "NM", True)
        k2 = PhysicalKey("Dismember", "mh3:62", "NM", True)
        assert k1 == k2

    def test_different_printing_not_equal(self):
        k1 = PhysicalKey("Dismember", "mh3:62")
        k2 = PhysicalKey("Dismember", "nph:62")
        assert k1 != k2

    def test_different_foil_not_equal(self):
        k1 = PhysicalKey("Brainstorm", foil=False)
        k2 = PhysicalKey("Brainstorm", foil=True)
        assert k1 != k2

    def test_usable_as_dict_key(self):
        d: dict[PhysicalKey, int] = {}
        k = PhysicalKey("Force of Will", "all:62", "LP", False)
        d[k] = 4
        assert d[k] == 4


# ---------------------------------------------------------------------------
# inventory_to_physical
# ---------------------------------------------------------------------------


class TestInventoryToPhysical:
    def test_single_entry(self):
        entries = [InventoryEntry(name="Dismember", count=2, printing="mh3:62")]
        result = inventory_to_physical(entries)
        key = PhysicalKey("Dismember", "mh3:62", None, False)
        assert result[key] == 2

    def test_two_printings_separate_keys(self):
        entries = [
            InventoryEntry(name="Dismember", count=2, printing="mh3:62"),
            InventoryEntry(name="Dismember", count=1, printing="nph:62"),
        ]
        result = inventory_to_physical(entries)
        assert result[PhysicalKey("Dismember", "mh3:62")] == 2
        assert result[PhysicalKey("Dismember", "nph:62")] == 1

    def test_no_printing_key_has_none(self):
        entries = [InventoryEntry(name="Brainstorm", count=4)]
        result = inventory_to_physical(entries)
        assert result[PhysicalKey("Brainstorm", None, None, False)] == 4

    def test_foil_and_nonfoil_separate(self):
        entries = [
            InventoryEntry(name="Brainstorm", count=2, foil=False),
            InventoryEntry(name="Brainstorm", count=1, foil=True),
        ]
        result = inventory_to_physical(entries)
        assert result[PhysicalKey("Brainstorm", None, None, False)] == 2
        assert result[PhysicalKey("Brainstorm", None, None, True)] == 1

    def test_condition_separates_keys(self):
        entries = [
            InventoryEntry(name="Force of Will", count=2, condition="NM"),
            InventoryEntry(name="Force of Will", count=1, condition="LP"),
        ]
        result = inventory_to_physical(entries)
        assert result[PhysicalKey("Force of Will", None, "NM", False)] == 2
        assert result[PhysicalKey("Force of Will", None, "LP", False)] == 1

    def test_same_bucket_aggregates(self):
        # Two entries with identical identity — should sum.
        entries = [
            InventoryEntry(name="Island", count=4, printing="lea:288"),
            InventoryEntry(name="Island", count=2, printing="lea:288"),
        ]
        result = inventory_to_physical(entries)
        assert result[PhysicalKey("Island", "lea:288")] == 6

    def test_empty_returns_empty(self):
        assert inventory_to_physical([]) == {}


# ---------------------------------------------------------------------------
# deck_to_physical
# ---------------------------------------------------------------------------


class TestDeckToPhysical:
    def test_unpinned_card_has_none_printing(self):
        cards = [DeckCardRef(name="Brainstorm", count=4, board="main")]
        result = deck_to_physical(cards)
        assert result[PhysicalKey("Brainstorm", None, None, False)] == 4

    def test_pinned_printing_preserved(self):
        cards = [DeckCardRef(name="Dismember", count=2, board="main", printing="nph:62")]
        result = deck_to_physical(cards)
        assert result[PhysicalKey("Dismember", "nph:62", None, False)] == 2

    def test_main_and_side_combined(self):
        cards = [
            DeckCardRef(name="Force of Will", count=4, board="main"),
            DeckCardRef(name="Force of Will", count=1, board="side"),
        ]
        # deck_to_physical combines both boards in one call.
        result = deck_to_physical(cards)
        assert result[PhysicalKey("Force of Will")] == 5

    def test_empty_returns_empty(self):
        assert deck_to_physical([]) == {}


# ---------------------------------------------------------------------------
# free_binder_physical
# ---------------------------------------------------------------------------


class TestFreeBinderPhysical:
    def test_all_free_when_nothing_allocated(self):
        owned = {
            PhysicalKey("Dismember", "mh3:62"): 2,
            PhysicalKey("Dismember", "nph:62"): 1,
        }
        result = free_binder_physical(owned, {})
        assert result[PhysicalKey("Dismember", "mh3:62")] == 2
        assert result[PhysicalKey("Dismember", "nph:62")] == 1

    def test_reduces_only_matching_printing(self):
        owned = {
            PhysicalKey("Dismember", "mh3:62"): 2,  # $33 copy
            PhysicalKey("Dismember", "nph:62"): 1,  # $2 copy
        }
        # Deck allocates 1x of the nph copy.
        allocated = {PhysicalKey("Dismember", "nph:62"): 1}
        result = free_binder_physical(owned, allocated)
        assert result[PhysicalKey("Dismember", "mh3:62")] == 2  # untouched
        assert result[PhysicalKey("Dismember", "nph:62")] == 0  # fully allocated

    def test_over_committed_floors_at_zero(self):
        owned = {PhysicalKey("Brainstorm", "lea:62"): 1}
        allocated = {PhysicalKey("Brainstorm", "lea:62"): 5}
        result = free_binder_physical(owned, allocated)
        assert result[PhysicalKey("Brainstorm", "lea:62")] == 0

    def test_unowned_key_not_in_result(self):
        owned = {PhysicalKey("Island"): 10}
        allocated = {PhysicalKey("Force of Will"): 4}  # not in owned
        result = free_binder_physical(owned, allocated)
        assert PhysicalKey("Force of Will") not in result

    def test_foil_and_nonfoil_tracked_independently(self):
        owned = {
            PhysicalKey("Brainstorm", None, None, False): 4,
            PhysicalKey("Brainstorm", None, None, True): 1,
        }
        allocated = {PhysicalKey("Brainstorm", None, None, False): 2}
        result = free_binder_physical(owned, allocated)
        assert result[PhysicalKey("Brainstorm", None, None, False)] == 2
        assert result[PhysicalKey("Brainstorm", None, None, True)] == 1


# ---------------------------------------------------------------------------
# contention_physical
# ---------------------------------------------------------------------------


class TestContentionPhysical:
    def test_no_contention_different_printings(self):
        """Two decks using different printings of the same card — no contention."""
        owned = {
            PhysicalKey("Dismember", "mh3:62"): 1,
            PhysicalKey("Dismember", "nph:62"): 1,
        }
        per_deck = {
            "Deck A": {PhysicalKey("Dismember", "mh3:62"): 1},
            "Deck B": {PhysicalKey("Dismember", "nph:62"): 1},
        }
        result = contention_physical(per_deck, owned)
        assert result == []

    def test_contention_same_printing(self):
        """Two decks both claim the same printing copy."""
        owned = {PhysicalKey("Dismember", "nph:62"): 1}
        per_deck = {
            "Deck A": {PhysicalKey("Dismember", "nph:62"): 1},
            "Deck B": {PhysicalKey("Dismember", "nph:62"): 1},
        }
        result = contention_physical(per_deck, owned)
        assert len(result) == 1
        entry = result[0]
        assert entry.name == "Dismember"
        assert entry.physical_key == PhysicalKey("Dismember", "nph:62")
        assert entry.owned == 1
        assert entry.total_claimed == 2
        assert entry.shortfall == 1
        assert sorted(entry.decks_claiming) == ["Deck A", "Deck B"]

    def test_contention_entry_has_physical_key(self):
        """physical_key is always set by contention_physical."""
        owned = {PhysicalKey("Force of Will", "all:62", "NM", False): 4}
        per_deck = {
            "Deck A": {PhysicalKey("Force of Will", "all:62", "NM", False): 4},
            "Deck B": {PhysicalKey("Force of Will", "all:62", "NM", False): 4},
        }
        result = contention_physical(per_deck, owned)
        assert len(result) == 1
        assert result[0].physical_key is not None
        assert result[0].physical_key.printing == "all:62"

    def test_contention_foil_vs_nonfoil_separate(self):
        """Foil copy contested separately from non-foil."""
        owned = {
            PhysicalKey("Brainstorm", None, None, False): 4,
            PhysicalKey("Brainstorm", None, None, True): 1,
        }
        # Both decks claim the foil copy.
        per_deck = {
            "Deck A": {PhysicalKey("Brainstorm", None, None, True): 1},
            "Deck B": {PhysicalKey("Brainstorm", None, None, True): 1},
        }
        result = contention_physical(per_deck, owned)
        assert len(result) == 1
        assert result[0].physical_key == PhysicalKey("Brainstorm", None, None, True)
        assert result[0].shortfall == 1

    def test_contention_sorted_by_shortfall_desc(self):
        owned = {
            PhysicalKey("X", "s1"): 1,
            PhysicalKey("Y", "s1"): 2,
        }
        per_deck = {
            "Deck A": {PhysicalKey("X", "s1"): 3, PhysicalKey("Y", "s1"): 3},
            "Deck B": {PhysicalKey("X", "s1"): 3, PhysicalKey("Y", "s1"): 3},
        }
        result = contention_physical(per_deck, owned)
        # X shortfall = 5, Y shortfall = 4 → X first
        assert result[0].name == "X"
        assert result[1].name == "Y"

    def test_empty_decks(self):
        assert contention_physical({}, {}) == []


# ---------------------------------------------------------------------------
# Mixed presence: some entries printing-present, some not
# ---------------------------------------------------------------------------


class TestMixedPresence:
    def test_printing_absent_entry_gets_none_key(self):
        """Entries without printing resolve to PhysicalKey with printing=None."""
        entries = [
            InventoryEntry(name="Brainstorm", count=4),           # no printing
            InventoryEntry(name="Dismember", count=1, printing="nph:62"),
        ]
        result = inventory_to_physical(entries)
        assert PhysicalKey("Brainstorm", None, None, False) in result
        assert PhysicalKey("Dismember", "nph:62", None, False) in result

    def test_free_binder_physical_mixed_keys(self):
        """Entries without printing and with printing coexist correctly."""
        owned = {
            PhysicalKey("Brainstorm"): 4,           # printing=None
            PhysicalKey("Dismember", "nph:62"): 2,
            PhysicalKey("Dismember", "mh3:62"): 1,
        }
        allocated = {
            PhysicalKey("Brainstorm"): 2,
            PhysicalKey("Dismember", "nph:62"): 2,
        }
        result = free_binder_physical(owned, allocated)
        assert result[PhysicalKey("Brainstorm")] == 2
        assert result[PhysicalKey("Dismember", "nph:62")] == 0
        assert result[PhysicalKey("Dismember", "mh3:62")] == 1  # untouched

    def test_contention_physical_no_cross_printing_bleed(self):
        """A deck claiming printing=None does not count against a mh3:62 copy."""
        owned = {
            PhysicalKey("Dismember"): 1,          # unspecified printing
            PhysicalKey("Dismember", "mh3:62"): 1,
        }
        per_deck = {
            "Deck A": {PhysicalKey("Dismember"): 1},
            "Deck B": {PhysicalKey("Dismember"): 1},
        }
        result = contention_physical(per_deck, owned)
        # Only the None-printing key is contested; mh3:62 key is untouched.
        contested = [e for e in result if e.physical_key == PhysicalKey("Dismember")]
        assert len(contested) == 1
        assert contested[0].shortfall == 1


# ---------------------------------------------------------------------------
# Regression: name-level functions completely unchanged
# ---------------------------------------------------------------------------


class TestNameLevelFunctionsUnchanged:
    """Prove that the existing name-level functions produce identical results."""

    def test_buildability_unchanged(self):
        owned = {"Brainstorm": 4, "Force of Will": 4}
        main = {"Brainstorm": 4, "Force of Will": 4}
        r = buildability(main, {}, owned)
        assert r.buildable is True
        assert r.missing == {}

    def test_free_binder_unchanged(self):
        owned = {"Brainstorm": 4}
        allocated = {"Brainstorm": 2}
        result = free_binder(owned, allocated)
        assert result == {"Brainstorm": 2}

    def test_contention_physical_key_none_for_name_level(self):
        """Name-level ContentionEntry.physical_key is None (not set by contention())."""
        per_deck = {
            "Deck A": {"Brainstorm": 4},
            "Deck B": {"Brainstorm": 4},
        }
        owned = {"Brainstorm": 4}
        result = contention(per_deck, owned)
        assert len(result) == 1
        assert result[0].physical_key is None

    def test_aggregate_owned_unchanged(self):
        entries = [
            InventoryEntry(name="Dismember", count=2, printing="mh3:62"),
            InventoryEntry(name="Dismember", count=1, printing="nph:62"),
        ]
        assert aggregate_owned(entries, name="Dismember") == 3
        assert aggregate_owned(entries, name="Dismember", printing="mh3:62") == 2

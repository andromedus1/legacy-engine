"""Tests for models/collection.py — model invariants, versioning, owner threading.

Pure tests (no DB, no filesystem).  Uses factory fixtures returning closures
per the pytest-factory-fixtures pattern.
"""

from __future__ import annotations

import pytest

from legacy_engine.models.collection import (
    LOCAL_OWNER,
    DeckCardRef,
    DeckVersion,
    Inventory,
    InventoryEntry,
    UserDeck,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_inventory_entry():
    def _make(**kwargs) -> InventoryEntry:
        defaults = dict(name="Brainstorm", count=4)
        defaults.update(kwargs)
        return InventoryEntry(**defaults)
    return _make


@pytest.fixture
def make_deck_version():
    def _make(**kwargs) -> DeckVersion:
        defaults = dict(
            id="ver-001",
            version=1,
            cards=[
                DeckCardRef(name="Brainstorm", count=4, board="main"),
                DeckCardRef(name="Daze", count=4, board="side"),
            ],
            created="2026-06-13T00:00:00Z",
        )
        defaults.update(kwargs)
        return DeckVersion(**defaults)
    return _make


@pytest.fixture
def make_user_deck(make_deck_version):
    def _make(**kwargs) -> UserDeck:
        ver = make_deck_version()
        defaults = dict(
            id="deck-001",
            owner=LOCAL_OWNER,
            name="my Dimir Tempo",
            versions=[ver],
            current_version_id=ver.id,
            created="2026-06-13T00:00:00Z",
            updated="2026-06-13T00:00:00Z",
        )
        defaults.update(kwargs)
        return UserDeck(**defaults)
    return _make


# ---------------------------------------------------------------------------
# InventoryEntry
# ---------------------------------------------------------------------------


class TestInventoryEntry:
    def test_defaults(self, make_inventory_entry):
        e = make_inventory_entry()
        assert e.count == 4
        assert e.printing is None
        assert e.condition is None
        assert e.foil is False

    def test_with_printing(self, make_inventory_entry):
        e = make_inventory_entry(name="Dismember", count=2, printing="mh3:62", condition="NM")
        assert e.printing == "mh3:62"
        assert e.condition == "NM"

    def test_extra_fields_ignored(self):
        """LegacyEngineModel extra='ignore' — unknown fields silently dropped."""
        e = InventoryEntry(name="Force of Will", count=4, unknown_field="oops")
        assert e.name == "Force of Will"
        assert not hasattr(e, "unknown_field")


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


class TestInventory:
    def test_default_owner(self):
        inv = Inventory()
        assert inv.owner == LOCAL_OWNER

    def test_entries_list(self, make_inventory_entry):
        e1 = make_inventory_entry(name="Brainstorm", count=4)
        e2 = make_inventory_entry(name="Force of Will", count=4)
        inv = Inventory(entries=[e1, e2])
        assert len(inv.entries) == 2

    def test_owner_thread(self):
        inv = Inventory(owner="alice")
        assert inv.owner == "alice"


# ---------------------------------------------------------------------------
# DeckVersion — immutability / append-only
# ---------------------------------------------------------------------------


class TestDeckVersion:
    def test_stable_id(self, make_deck_version):
        ver = make_deck_version(id="abc-123")
        assert ver.id == "abc-123"

    def test_card_boards(self, make_deck_version):
        ver = make_deck_version()
        main = [c for c in ver.cards if c.board == "main"]
        side = [c for c in ver.cards if c.board == "side"]
        assert len(main) == 1
        assert len(side) == 1

    def test_version_number(self, make_deck_version):
        ver = make_deck_version(version=3)
        assert ver.version == 3


# ---------------------------------------------------------------------------
# UserDeck — id stability, owner, versioning invariants
# ---------------------------------------------------------------------------


class TestUserDeck:
    def test_default_owner(self):
        """A UserDeck without explicit owner defaults to LOCAL_OWNER."""
        deck = UserDeck(id="x", name="Test")
        assert deck.owner == LOCAL_OWNER

    def test_id_stable_across_rename(self, make_user_deck):
        """The deck id must not change when the name changes."""
        deck = make_user_deck(name="old name")
        original_id = deck.id
        deck2 = deck.model_copy(update={"name": "new name"})
        assert deck2.id == original_id

    def test_append_only_version(self, make_deck_version, make_user_deck):
        """Appending a new version does not mutate the old version."""
        deck = make_user_deck()
        old_ver = deck.versions[0]
        new_ver = make_deck_version(id="ver-002", version=2)
        deck2 = deck.model_copy(
            update={
                "versions": [*deck.versions, new_ver],
                "current_version_id": new_ver.id,
            }
        )
        # Old version is intact.
        assert deck2.versions[0].id == old_ver.id
        assert deck2.versions[0].version == 1
        # New current points to v2.
        assert deck2.current_version_id == "ver-002"
        assert len(deck2.versions) == 2

    def test_current_version_id_moves(self, make_deck_version, make_user_deck):
        deck = make_user_deck()
        v1 = deck.versions[0]
        v2 = make_deck_version(id="ver-002", version=2)
        deck2 = deck.model_copy(
            update={"versions": [v1, v2], "current_version_id": v2.id}
        )
        assert deck2.current_version_id == v2.id

    def test_owner_threaded(self):
        deck = UserDeck(id="x", owner="charlie", name="Test")
        assert deck.owner == "charlie"

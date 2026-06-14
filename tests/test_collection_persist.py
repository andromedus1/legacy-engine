"""Tests for collection/persist.py — JSON round-trip, id stability, file layout.

All tests use a tmp_path-scoped COLLECTION_DIR so they never touch real data.
"""

from __future__ import annotations

import json
from pathlib import Path

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
# Helpers: patch config paths to a temp dir
# ---------------------------------------------------------------------------


@pytest.fixture
def patch_collection_paths(tmp_path, monkeypatch):
    """Redirect all collection paths to a fresh tmp_path subtree."""
    coll_dir = tmp_path / "collection"
    inv_path = coll_dir / "inventory.json"
    decks_dir = coll_dir / "decks"

    import legacy_engine.collection.persist as persist_mod
    import legacy_engine.config as config_mod

    monkeypatch.setattr(config_mod, "COLLECTION_DIR", coll_dir)
    monkeypatch.setattr(config_mod, "INVENTORY_PATH", inv_path)
    monkeypatch.setattr(config_mod, "DECKS_DIR", decks_dir)
    monkeypatch.setattr(persist_mod, "COLLECTION_DIR", coll_dir)
    monkeypatch.setattr(persist_mod, "INVENTORY_PATH", inv_path)
    monkeypatch.setattr(persist_mod, "DECKS_DIR", decks_dir)

    return coll_dir


# ---------------------------------------------------------------------------
# Inventory round-trips
# ---------------------------------------------------------------------------


class TestInventoryRoundTrip:
    def test_save_and_load(self, patch_collection_paths):
        from legacy_engine.collection.persist import load_inventory, save_inventory

        inv = Inventory(
            owner=LOCAL_OWNER,
            entries=[
                InventoryEntry(name="Brainstorm", count=4),
                InventoryEntry(name="Dismember", count=2, printing="mh3:62", condition="NM"),
            ],
        )
        save_inventory(inv)
        loaded = load_inventory()

        assert loaded.owner == LOCAL_OWNER
        assert len(loaded.entries) == 2
        names = {e.name for e in loaded.entries}
        assert "Brainstorm" in names
        assert "Dismember" in names

    def test_missing_file_returns_empty(self, patch_collection_paths):
        from legacy_engine.collection.persist import load_inventory

        inv = load_inventory()
        assert inv.entries == []
        assert inv.owner == LOCAL_OWNER

    def test_updated_stamp_set_on_save(self, patch_collection_paths):
        from legacy_engine.collection.persist import load_inventory, save_inventory

        inv = Inventory(owner=LOCAL_OWNER, entries=[InventoryEntry(name="X", count=1)])
        save_inventory(inv)
        loaded = load_inventory()
        assert loaded.updated != ""  # timestamp was set

    def test_owner_filter(self, patch_collection_paths):
        """load_inventory with wrong owner returns empty (single-user now)."""
        from legacy_engine.collection.persist import load_inventory, save_inventory

        inv = Inventory(owner="alice", entries=[InventoryEntry(name="X", count=1)])
        save_inventory(inv)
        loaded = load_inventory(owner="bob")
        assert loaded.entries == []


# ---------------------------------------------------------------------------
# UserDeck round-trips
# ---------------------------------------------------------------------------


def _make_simple_deck(name="Test Deck", deck_id="deck-abc") -> UserDeck:
    ver = DeckVersion(
        id="ver-001",
        version=1,
        cards=[DeckCardRef(name="Brainstorm", count=4, board="main")],
        created="2026-06-13T00:00:00Z",
    )
    return UserDeck(
        id=deck_id,
        owner=LOCAL_OWNER,
        name=name,
        versions=[ver],
        current_version_id=ver.id,
        created="2026-06-13T00:00:00Z",
        updated="2026-06-13T00:00:00Z",
    )


class TestUserDeckRoundTrip:
    def test_save_and_load(self, patch_collection_paths):
        from legacy_engine.collection.persist import load_user_deck, save_user_deck

        deck = _make_simple_deck()
        save_user_deck(deck)
        loaded = load_user_deck(deck.id)

        assert loaded is not None
        assert loaded.id == deck.id
        assert loaded.name == deck.name
        assert len(loaded.versions) == 1
        assert loaded.versions[0].cards[0].name == "Brainstorm"

    def test_file_named_by_id(self, patch_collection_paths):
        from legacy_engine.collection.persist import save_user_deck

        deck = _make_simple_deck(deck_id="deck-xyz-123")
        save_user_deck(deck)

        import legacy_engine.collection.persist as persist_mod
        expected = persist_mod.DECKS_DIR / "deck-xyz-123.json"
        assert expected.exists()

    def test_id_stable_across_rename(self, patch_collection_paths):
        """Renaming (a name change + re-save) does not change the file or the id."""
        from legacy_engine.collection.persist import load_user_deck, save_user_deck

        deck = _make_simple_deck(name="old name", deck_id="deck-stable")
        save_user_deck(deck)

        renamed = deck.model_copy(update={"name": "new name"})
        save_user_deck(renamed)

        loaded = load_user_deck("deck-stable")
        assert loaded is not None
        assert loaded.id == "deck-stable"
        assert loaded.name == "new name"

    def test_load_missing_returns_none(self, patch_collection_paths):
        from legacy_engine.collection.persist import load_user_deck

        assert load_user_deck("nonexistent-id") is None

    def test_list_user_decks(self, patch_collection_paths):
        from legacy_engine.collection.persist import list_user_decks, save_user_deck

        d1 = _make_simple_deck(name="Zx deck", deck_id="deck-zx")
        d2 = _make_simple_deck(name="Aa deck", deck_id="deck-aa")
        save_user_deck(d1)
        save_user_deck(d2)

        decks = list_user_decks()
        names = [d.name for d in decks]
        # Should be sorted by name.
        assert names == ["Aa deck", "Zx deck"]

    def test_find_deck_by_name(self, patch_collection_paths):
        from legacy_engine.collection.persist import find_deck_by_name, save_user_deck

        deck = _make_simple_deck(name="my Dimir Tempo")
        save_user_deck(deck)

        found = find_deck_by_name("my Dimir Tempo")
        assert found is not None
        assert found.id == deck.id

    def test_find_deck_by_name_case_insensitive(self, patch_collection_paths):
        from legacy_engine.collection.persist import find_deck_by_name, save_user_deck

        deck = _make_simple_deck(name="My Dimir Tempo")
        save_user_deck(deck)

        found = find_deck_by_name("my dimir tempo")
        assert found is not None

    def test_find_deck_by_name_missing(self, patch_collection_paths):
        from legacy_engine.collection.persist import find_deck_by_name

        assert find_deck_by_name("Does Not Exist") is None


# ---------------------------------------------------------------------------
# _deck_path path-traversal hardening
# ---------------------------------------------------------------------------


class TestDeckPathTraversalRejection:
    """_deck_path must reject deck_id values that escape DECKS_DIR."""

    def test_normal_id_is_accepted(self, patch_collection_paths):
        from legacy_engine.collection.persist import _deck_path
        import legacy_engine.collection.persist as persist_mod

        path = _deck_path("deck-abc123")
        assert path.parent == persist_mod.DECKS_DIR.resolve()

    def test_dotdot_id_is_rejected(self, patch_collection_paths):
        from legacy_engine.collection.persist import _deck_path

        with pytest.raises(ValueError, match="escapes DECKS_DIR"):
            _deck_path("../../../etc/passwd")

    def test_dotdot_in_middle_is_rejected(self, patch_collection_paths):
        from legacy_engine.collection.persist import _deck_path

        with pytest.raises(ValueError, match="escapes DECKS_DIR"):
            _deck_path("subdir/../../evil")

    def test_absolute_path_is_rejected(self, patch_collection_paths):
        from legacy_engine.collection.persist import _deck_path

        with pytest.raises(ValueError, match="escapes DECKS_DIR"):
            _deck_path("/etc/passwd")

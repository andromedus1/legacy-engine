"""Tests for collection/store.py — DuckDB derived tables, rebuild, owner filter.

Uses :memory: DuckDB so tests are fast and isolated.
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
# Helpers
# ---------------------------------------------------------------------------


def _memory_con():
    from legacy_engine.collection.store import connect, init_schema

    con = connect(":memory:")
    init_schema(con)
    return con


def _make_inventory(owner=LOCAL_OWNER, entries=None) -> Inventory:
    if entries is None:
        entries = [
            InventoryEntry(name="Brainstorm", count=4),
            InventoryEntry(name="Force of Will", count=4),
        ]
    return Inventory(owner=owner, entries=entries)


def _make_user_deck(name="Test", deck_id="d1", owner=LOCAL_OWNER, cards=None) -> UserDeck:
    if cards is None:
        cards = [
            DeckCardRef(name="Brainstorm", count=4, board="main"),
            DeckCardRef(name="Daze", count=3, board="side"),
        ]
    ver = DeckVersion(
        id=f"{deck_id}-v1",
        version=1,
        cards=cards,
        created="2026-06-13T00:00:00Z",
    )
    return UserDeck(
        id=deck_id,
        owner=owner,
        name=name,
        versions=[ver],
        current_version_id=ver.id,
        created="2026-06-13T00:00:00Z",
        updated="2026-06-13T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# init_schema idempotency
# ---------------------------------------------------------------------------


class TestInitSchema:
    def test_idempotent(self):
        from legacy_engine.collection.store import connect, init_schema

        con = connect(":memory:")
        init_schema(con)
        init_schema(con)  # Must not raise.
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        assert "inventory_entries" in tables
        assert "user_decks" in tables
        assert "deck_versions" in tables
        assert "deck_version_cards" in tables


# ---------------------------------------------------------------------------
# load_inventory_rows
# ---------------------------------------------------------------------------


class TestLoadInventoryRows:
    def test_load_and_query(self):
        from legacy_engine.collection.store import load_inventory_rows

        con = _memory_con()
        inv = _make_inventory()
        load_inventory_rows(con, inv)

        rows = con.execute("SELECT name, count FROM inventory_entries ORDER BY name").fetchall()
        assert rows == [("Brainstorm", 4), ("Force of Will", 4)]

    def test_idempotent_reload(self):
        from legacy_engine.collection.store import load_inventory_rows

        con = _memory_con()
        inv = _make_inventory()
        load_inventory_rows(con, inv)
        load_inventory_rows(con, inv)  # reload

        cnt = con.execute("SELECT COUNT(*) FROM inventory_entries").fetchone()[0]
        assert cnt == 2  # not 4 (no duplication)

    def test_owner_in_rows(self):
        from legacy_engine.collection.store import load_inventory_rows

        con = _memory_con()
        inv = _make_inventory(owner="alice")
        load_inventory_rows(con, inv)

        row = con.execute("SELECT owner FROM inventory_entries LIMIT 1").fetchone()
        assert row[0] == "alice"


# ---------------------------------------------------------------------------
# load_user_deck_rows
# ---------------------------------------------------------------------------


class TestLoadUserDeckRows:
    def test_load_and_query(self):
        from legacy_engine.collection.store import load_user_deck_rows

        con = _memory_con()
        deck = _make_user_deck()
        load_user_deck_rows(con, deck)

        deck_row = con.execute("SELECT id, name FROM user_decks").fetchone()
        assert deck_row[0] == "d1"
        assert deck_row[1] == "Test"

        ver_row = con.execute("SELECT version FROM deck_versions WHERE deck_id = 'd1'").fetchone()
        assert ver_row[0] == 1

        cards = con.execute("SELECT name, board FROM deck_version_cards ORDER BY board").fetchall()
        assert ("Brainstorm", "main") in cards
        assert ("Daze", "side") in cards

    def test_idempotent_reload(self):
        from legacy_engine.collection.store import load_user_deck_rows

        con = _memory_con()
        deck = _make_user_deck()
        load_user_deck_rows(con, deck)
        load_user_deck_rows(con, deck)

        cnt = con.execute("SELECT COUNT(*) FROM user_decks").fetchone()[0]
        assert cnt == 1


# ---------------------------------------------------------------------------
# fetch_owned_counts
# ---------------------------------------------------------------------------


class TestFetchOwnedCounts:
    def test_sums_all_printings(self):
        from legacy_engine.collection.store import fetch_owned_counts, load_inventory_rows

        con = _memory_con()
        inv = Inventory(
            owner=LOCAL_OWNER,
            entries=[
                InventoryEntry(name="Dismember", count=2, printing="mh3:62"),
                InventoryEntry(name="Dismember", count=1, printing="mm2:80"),
                InventoryEntry(name="Brainstorm", count=4),
            ],
        )
        load_inventory_rows(con, inv)
        owned = fetch_owned_counts(con)
        assert owned["Dismember"] == 3
        assert owned["Brainstorm"] == 4

    def test_owner_scoped(self):
        from legacy_engine.collection.store import fetch_owned_counts, load_inventory_rows

        con = _memory_con()
        alice_inv = _make_inventory(owner="alice", entries=[InventoryEntry(name="X", count=10)])
        bob_inv = _make_inventory(owner="bob", entries=[InventoryEntry(name="Y", count=5)])
        load_inventory_rows(con, alice_inv)
        load_inventory_rows(con, bob_inv)

        alice_owned = fetch_owned_counts(con, owner="alice")
        bob_owned = fetch_owned_counts(con, owner="bob")
        assert "X" in alice_owned
        assert "Y" not in alice_owned
        assert "Y" in bob_owned
        assert "X" not in bob_owned


# ---------------------------------------------------------------------------
# rebuild_collection (needs patched paths)
# ---------------------------------------------------------------------------


class TestRebuildCollection:
    def test_rebuild_idempotent(self, tmp_path, monkeypatch):
        """rebuild_collection drops+reloads; running twice is idempotent."""
        import legacy_engine.collection.persist as persist_mod
        import legacy_engine.config as config_mod

        coll_dir = tmp_path / "collection"
        inv_path = coll_dir / "inventory.json"
        decks_dir = coll_dir / "decks"
        monkeypatch.setattr(config_mod, "COLLECTION_DIR", coll_dir)
        monkeypatch.setattr(config_mod, "INVENTORY_PATH", inv_path)
        monkeypatch.setattr(config_mod, "DECKS_DIR", decks_dir)
        monkeypatch.setattr(persist_mod, "COLLECTION_DIR", coll_dir)
        monkeypatch.setattr(persist_mod, "INVENTORY_PATH", inv_path)
        monkeypatch.setattr(persist_mod, "DECKS_DIR", decks_dir)

        from legacy_engine.collection.persist import save_inventory, save_user_deck
        from legacy_engine.collection.store import fetch_owned_counts, rebuild_collection

        con = _memory_con()
        save_inventory(_make_inventory())
        save_user_deck(_make_user_deck())

        rebuild_collection(con)
        owned = fetch_owned_counts(con)
        assert owned["Brainstorm"] == 4

        rebuild_collection(con)  # second run: no duplication
        owned2 = fetch_owned_counts(con)
        assert owned2["Brainstorm"] == 4

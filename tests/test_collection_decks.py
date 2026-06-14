"""Tests for collection/decks.py — save_deck, current_cards, export round-trip.

Pure (no DB, no FS) except for save_deck_from_file and export_deck_text.
"""

from __future__ import annotations

import pytest

from legacy_engine.models.collection import (
    LOCAL_OWNER,
    DeckCardRef,
    DeckVersion,
    UserDeck,
)


# ---------------------------------------------------------------------------
# save_deck (new deck)
# ---------------------------------------------------------------------------


class TestSaveDeckNew:
    def test_creates_new_deck(self):
        from legacy_engine.collection.decks import save_deck

        deck = save_deck("my Dimir Tempo", {"Brainstorm": 4, "Island": 10}, {"Daze": 3})
        assert deck.name == "my Dimir Tempo"
        assert deck.owner == LOCAL_OWNER
        assert len(deck.versions) == 1
        ver = deck.versions[0]
        assert ver.version == 1
        assert deck.current_version_id == ver.id

    def test_cards_in_version(self):
        from legacy_engine.collection.decks import save_deck

        deck = save_deck("Test", {"Brainstorm": 4}, {"Daze": 3})
        ver = deck.versions[0]
        boards = {c.board for c in ver.cards}
        assert "main" in boards
        assert "side" in boards
        main_cards = {c.name: c.count for c in ver.cards if c.board == "main"}
        side_cards = {c.name: c.count for c in ver.cards if c.board == "side"}
        assert main_cards == {"Brainstorm": 4}
        assert side_cards == {"Daze": 3}

    def test_stable_uuid_id(self):
        from legacy_engine.collection.decks import save_deck

        d1 = save_deck("A", {"X": 1})
        d2 = save_deck("B", {"X": 1})
        assert d1.id != d2.id
        assert len(d1.id) == 36  # UUID format

    def test_owner_default(self):
        from legacy_engine.collection.decks import save_deck

        deck = save_deck("Test", {"X": 1})
        assert deck.owner == LOCAL_OWNER

    def test_owner_override(self):
        from legacy_engine.collection.decks import save_deck

        deck = save_deck("Test", {"X": 1}, owner="charlie")
        assert deck.owner == "charlie"


# ---------------------------------------------------------------------------
# save_deck (append version) — requires patched persist paths
# ---------------------------------------------------------------------------


@pytest.fixture
def patch_persist_paths(tmp_path, monkeypatch):
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


class TestSaveDeckAppendVersion:
    def test_append_version(self, patch_persist_paths):
        from legacy_engine.collection.decks import save_deck
        from legacy_engine.collection.persist import save_user_deck

        # Create v1.
        deck_v1 = save_deck("my Dimir Tempo", {"Brainstorm": 4})
        save_user_deck(deck_v1)

        # Append v2.
        deck_v2 = save_deck(
            "my Dimir Tempo",
            {"Brainstorm": 4, "Ponder": 2},
            deck_id=deck_v1.id,
        )
        assert len(deck_v2.versions) == 2
        assert deck_v2.versions[0].version == 1
        assert deck_v2.versions[1].version == 2
        assert deck_v2.current_version_id == deck_v2.versions[1].id

    def test_prior_version_immutable(self, patch_persist_paths):
        from legacy_engine.collection.decks import save_deck
        from legacy_engine.collection.persist import save_user_deck

        deck_v1 = save_deck("Test", {"X": 4})
        save_user_deck(deck_v1)
        v1_id = deck_v1.versions[0].id
        v1_cards_snapshot = list(deck_v1.versions[0].cards)

        deck_v2 = save_deck("Test", {"Y": 4}, deck_id=deck_v1.id)
        # V1 record in v2 is unchanged.
        assert deck_v2.versions[0].id == v1_id
        assert [c.name for c in deck_v2.versions[0].cards] == [c.name for c in v1_cards_snapshot]

    def test_id_stable_across_rename(self, patch_persist_paths):
        from legacy_engine.collection.decks import save_deck
        from legacy_engine.collection.persist import save_user_deck

        deck_v1 = save_deck("old name", {"X": 4})
        save_user_deck(deck_v1)

        deck_v2 = save_deck("new name", {"X": 4}, deck_id=deck_v1.id)
        assert deck_v2.id == deck_v1.id
        assert deck_v2.name == "new name"


# ---------------------------------------------------------------------------
# current_cards
# ---------------------------------------------------------------------------


class TestCurrentCards:
    def _deck_with_version(self, main, side):
        cards = []
        for name, cnt in main.items():
            cards.append(DeckCardRef(name=name, count=cnt, board="main"))
        for name, cnt in side.items():
            cards.append(DeckCardRef(name=name, count=cnt, board="side"))
        ver = DeckVersion(id="v1", version=1, cards=cards, created="")
        return UserDeck(
            id="d1",
            name="Test",
            versions=[ver],
            current_version_id=ver.id,
        )

    def test_returns_main_and_side(self):
        from legacy_engine.collection.decks import current_cards

        deck = self._deck_with_version({"Brainstorm": 4}, {"Daze": 3})
        main, side = current_cards(deck)
        assert main == {"Brainstorm": 4}
        assert side == {"Daze": 3}

    def test_empty_deck(self):
        from legacy_engine.collection.decks import current_cards

        deck = UserDeck(id="d1", name="Empty")
        main, side = current_cards(deck)
        assert main == {}
        assert side == {}


# ---------------------------------------------------------------------------
# export_deck_text — round-trip
# ---------------------------------------------------------------------------


class TestExportDeckText:
    def test_round_trip(self):
        """format_decklist(current_cards(deck)) round-trips back via parse_decklist."""
        from legacy_engine.collection.decks import current_cards, export_deck_text, save_deck
        from legacy_engine.models.decklist import parse_decklist

        deck = save_deck("Roundtrip", {"Brainstorm": 4, "Island": 10}, {"Daze": 3})
        text = export_deck_text(deck)
        parsed_main, parsed_side = parse_decklist(text)

        main, side = current_cards(deck)
        assert parsed_main == main
        assert parsed_side == side

    def test_version_by_number(self, patch_persist_paths):
        from legacy_engine.collection.decks import export_deck_text, save_deck
        from legacy_engine.collection.persist import save_user_deck
        from legacy_engine.models.decklist import parse_decklist

        deck_v1 = save_deck("Test", {"X": 4})
        save_user_deck(deck_v1)
        deck_v2 = save_deck("Test", {"Y": 4}, deck_id=deck_v1.id)

        text_v1 = export_deck_text(deck_v2, version_num=1)
        parsed_main, _ = parse_decklist(text_v1)
        assert parsed_main == {"X": 4}

"""Scryfall ingestion — whole-pool index (name + faces), on-demand Card resolution, mocked download."""

from __future__ import annotations

import json

import pytest

from legacy_engine.ingestion import scryfall
from legacy_engine.ingestion.scryfall import ScryfallClient, normalize_name
from legacy_engine.models.card import Card

NORMAL = {"name": "Brainstorm", "type_line": "Instant", "colors": ["U"], "mana_cost": "{U}", "cmc": 1.0}
LAND = {"name": "Volcanic Island", "type_line": "Land — Island Mountain", "colors": [], "produced_mana": ["U", "R"]}
SPLIT = {
    "name": "Fire // Ice",
    "layout": "split",
    "type_line": "Instant // Instant",
    "card_faces": [{"name": "Fire"}, {"name": "Ice"}],
}
# DFC with accented name — NFC form as Scryfall delivers it.
KHAZAD_NFC = "Troll of Khazad-dûm"  # "û" as single precomposed NFC codepoint
DFC_ACCENTED = {
    "name": KHAZAD_NFC,
    "layout": "transform",
    "type_line": "Creature — Troll",
    "card_faces": [{"name": KHAZAD_NFC}, {"name": "Troll of Khazad-dûm (Back)"}],
}
# Card with separate card_faces names (not a "//" split) — e.g. a modal double-faced card.
DFC_MODAL = {
    "name": "Valki, God of Lies // Tibalt, Cosmic Impostor",
    "layout": "modal_dfc",
    "type_line": "Legendary Creature — God // Legendary Planeswalker — Tibalt",
    "card_faces": [
        {"name": "Valki, God of Lies"},
        {"name": "Tibalt, Cosmic Impostor"},
    ],
}
# Card with a curly-apostrophe name — Scryfall delivers NFC smart quotes.
APOSTROPHE = {"name": "Teferi’s Protection", "type_line": "Instant"}


def _write_bulk(tmp_path, monkeypatch, cards):
    p = tmp_path / "oracle_cards.json"
    p.write_text(json.dumps(cards))
    monkeypatch.setattr(scryfall, "ORACLE_CARDS_PATH", p)
    return p


def test_normalize_name_curly_apostrophe():
    """Curly apostrophes are collapsed to straight apostrophes (existing behaviour preserved)."""
    assert normalize_name(" Brain’storm ") == "Brain'storm"


def test_normalize_name_nfd_becomes_nfc():
    """NFD-encoded accented characters are normalized to NFC form."""
    import unicodedata

    nfd = unicodedata.normalize("NFD", "Khazad-dûm")  # "û" decomposed
    nfc = unicodedata.normalize("NFC", "Khazad-dûm")  # "û" precomposed
    assert normalize_name(nfd) == nfc


def test_normalize_name():
    # Keep the original assertion for compatibility.
    assert normalize_name(" Brain’storm ") == "Brain'storm"


class TestLoadCardIndex:
    def test_indexes_by_name_and_face(self, tmp_path, monkeypatch):
        _write_bulk(tmp_path, monkeypatch, [NORMAL, LAND, SPLIT])
        with ScryfallClient() as client:
            idx = client.load_card_index()
        assert "Brainstorm" in idx and "Volcanic Island" in idx
        assert "Fire // Ice" in idx
        assert "Fire" in idx and "Ice" in idx  # faces indexed
        assert idx["Fire"]["name"] == "Fire // Ice"

    def test_missing_bulk_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scryfall, "ORACLE_CARDS_PATH", tmp_path / "nope.json")
        with ScryfallClient() as client:
            with pytest.raises(FileNotFoundError):
                client.load_card_index()

    def test_nfc_encoded_accented_name_indexed(self, tmp_path, monkeypatch):
        """Index contains the NFC-normalized accented name so NFD queries resolve (finding #8)."""
        import unicodedata

        _write_bulk(tmp_path, monkeypatch, [DFC_ACCENTED])
        with ScryfallClient() as client:
            idx = client.load_card_index()
        nfc_key = unicodedata.normalize("NFC", KHAZAD_NFC)
        assert nfc_key in idx

    def test_card_faces_names_indexed(self, tmp_path, monkeypatch):
        """card_faces[].name entries are indexed to the parent card (finding #8)."""
        _write_bulk(tmp_path, monkeypatch, [DFC_MODAL])
        with ScryfallClient() as client:
            idx = client.load_card_index()
        # Both face names should resolve to the parent card.
        assert "Valki, God of Lies" in idx
        assert "Tibalt, Cosmic Impostor" in idx
        assert idx["Valki, God of Lies"]["name"] == "Valki, God of Lies // Tibalt, Cosmic Impostor"
        assert idx["Tibalt, Cosmic Impostor"]["name"] == "Valki, God of Lies // Tibalt, Cosmic Impostor"

    def test_curly_apostrophe_in_index_normalized(self, tmp_path, monkeypatch):
        """A card whose Scryfall name uses a curly apostrophe is queryable via a straight one."""
        _write_bulk(tmp_path, monkeypatch, [APOSTROPHE])
        with ScryfallClient() as client:
            idx = client.load_card_index()
        # normalize_name turns curly apostrophe (U+2019) → straight (U+0027); the index key
        # must use the normalized (straight-apostrophe) form so straight-quote decklists resolve.
        # Build with chr() to avoid editor auto-curling literal apostrophes.
        straight_key = "Teferi" + chr(0x0027) + "s Protection"  # U+0027 straight apostrophe
        assert straight_key in idx


class TestGetCard:
    def test_resolves_split_via_face(self, tmp_path, monkeypatch):
        _write_bulk(tmp_path, monkeypatch, [SPLIT])
        with ScryfallClient() as client:
            card = client.get_card("Fire")
        assert isinstance(card, Card)
        assert card.name == "Fire // Ice"

    def test_unknown_returns_none(self, tmp_path, monkeypatch):
        _write_bulk(tmp_path, monkeypatch, [NORMAL])
        with ScryfallClient() as client:
            assert client.get_card("Nonexistent Card") is None

    def test_nfd_query_resolves_nfc_index_entry(self, tmp_path, monkeypatch):
        """An NFD-encoded query for an accented name resolves to the NFC index entry (finding #8)."""
        import unicodedata

        _write_bulk(tmp_path, monkeypatch, [DFC_ACCENTED])
        nfd_query = unicodedata.normalize("NFD", KHAZAD_NFC)
        with ScryfallClient() as client:
            card = client.get_card(nfd_query)
        assert card is not None
        assert card.name == KHAZAD_NFC

    def test_card_face_resolves_to_parent(self, tmp_path, monkeypatch):
        """A card_faces[].name query resolves to the parent DFC card (finding #8)."""
        _write_bulk(tmp_path, monkeypatch, [DFC_MODAL])
        with ScryfallClient() as client:
            card = client.get_card("Tibalt, Cosmic Impostor")
        assert card is not None
        assert card.name == "Valki, God of Lies // Tibalt, Cosmic Impostor"

    def test_curly_apostrophe_query_resolves(self, tmp_path, monkeypatch):
        """Both curly and straight apostrophe queries resolve to the same card."""
        _write_bulk(tmp_path, monkeypatch, [APOSTROPHE])
        # APOSTROPHE fixture name uses curly apostrophe (U+2019) as Scryfall delivers.
        # Build query strings via chr() to avoid editor auto-curling literal apostrophes.
        curly_query = "Teferi" + chr(0x2019) + "s Protection"   # right single quotation mark U+2019
        straight_query = "Teferi" + chr(0x0027) + "s Protection"  # straight apostrophe U+0027
        with ScryfallClient() as client:
            card_curly = client.get_card(curly_query)
            card_straight = client.get_card(straight_query)
        assert card_curly is not None, "Curly-apostrophe query should resolve"
        assert card_straight is not None, "Straight-apostrophe query should resolve"
        assert card_curly.name == card_straight.name


def test_download_bulk_data_mocked(tmp_path, monkeypatch):
    monkeypatch.setattr(scryfall, "SCRYFALL_DIR", tmp_path)
    monkeypatch.setattr(scryfall, "ORACLE_CARDS_PATH", tmp_path / "oracle_cards.json")
    monkeypatch.setattr(scryfall, "METADATA_PATH", tmp_path / "metadata.json")

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return [NORMAL, LAND]

    with ScryfallClient() as client:
        monkeypatch.setattr(
            client, "_fetch_bulk_metadata", lambda: {"download_uri": "http://x/bulk", "updated_at": "2026-05-29"}
        )
        monkeypatch.setattr(client.client, "get", lambda *a, **k: FakeResp())
        path = client.download_bulk_data()
        assert path.exists()
        idx = client.load_card_index()
    assert "Brainstorm" in idx and "Volcanic Island" in idx

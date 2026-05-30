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


def _write_bulk(tmp_path, monkeypatch, cards):
    p = tmp_path / "oracle_cards.json"
    p.write_text(json.dumps(cards))
    monkeypatch.setattr(scryfall, "ORACLE_CARDS_PATH", p)
    return p


def test_normalize_name():
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

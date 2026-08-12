"""Scryfall ingestion — whole-pool index (name + faces), on-demand Card resolution, mocked download."""

from __future__ import annotations

import json
import gzip

import pytest

from legacy_engine.ingestion import scryfall
from legacy_engine.ingestion.scryfall import ScryfallClient, _validate_scryfall_uri, normalize_name
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
            client, "_fetch_bulk_metadata",
            lambda: {"download_uri": "https://api.scryfall.com/bulk-data/oracle-cards-test.json", "updated_at": "2026-05-29", "object_count": 2}
        )
        monkeypatch.setattr(client.client, "get", lambda *a, **k: FakeResp())
        path = client.download_bulk_data()
        assert path.exists()
        idx = client.load_card_index()
    assert "Brainstorm" in idx and "Volcanic Island" in idx


def test_download_bulk_data_accepts_live_jsonl_download_uri(tmp_path, monkeypatch):
    """Current Scryfall metadata exposes gzipped JSONL via jsonl_download_uri only."""
    oracle_path = tmp_path / "oracle_cards.json"
    metadata_path = tmp_path / "metadata.json"
    payload = b"".join(json.dumps(card).encode() + b"\n" for card in (NORMAL, LAND))
    compressed = gzip.compress(payload)

    class Response:
        headers = {"content-encoding": "gzip"}

        def raise_for_status(self):
            return None

        def iter_raw(self, chunk_size):
            yield compressed

        def iter_bytes(self, chunk_size):
            yield payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class Http:
        def stream(self, *args, **kwargs):
            return Response()

        def close(self):
            return None

    monkeypatch.setattr(scryfall, "SCRYFALL_DIR", tmp_path)
    monkeypatch.setattr(scryfall, "ORACLE_CARDS_PATH", oracle_path)
    monkeypatch.setattr(scryfall, "METADATA_PATH", metadata_path)
    client = ScryfallClient()
    client.client.close()
    client.client = Http()
    monkeypatch.setattr(client, "_fetch_bulk_metadata", lambda: {
        "jsonl_download_uri": "https://data.scryfall.io/oracle.jsonl.gz",
        "updated_at": "2026-08-11T00:00:00Z",
        "compressed_size": len(compressed),
    })

    path = client.download_bulk_data(force=True)

    assert path == oracle_path
    assert [row["name"] for row in scryfall.iter_bulk_rows(path)] == [
        "Brainstorm", "Volcanic Island",
    ]
    assert json.loads(metadata_path.read_text())["compressed_size"] == len(compressed)
    assert client.load_card_index()["Brainstorm"]["name"] == "Brainstorm"


def test_jsonl_completeness_requires_provider_size_or_count():
    with pytest.raises(ValueError, match="lacks compressed_size and object_count"):
        scryfall._bulk_completeness({
            "jsonl_download_uri": "https://data.scryfall.io/oracle.jsonl.gz",
        })


def test_corrupt_jsonl_candidate_preserves_last_good_oracle_and_metadata(tmp_path, monkeypatch):
    oracle_path = tmp_path / "oracle_cards.json"
    metadata_path = tmp_path / "metadata.json"
    oracle_path.write_text(json.dumps([NORMAL]), encoding="utf-8")
    metadata_path.write_text('{"updated_at":"last-good"}', encoding="utf-8")

    class Response:
        headers = {"content-encoding": "gzip"}

        def raise_for_status(self):
            return None

        def iter_raw(self, chunk_size):
            yield gzip.compress(b'{"name":"Brainstorm"}\nnot-json\n')

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class Http:
        def stream(self, *args, **kwargs):
            return Response()

        def close(self):
            return None

    monkeypatch.setattr(scryfall, "SCRYFALL_DIR", tmp_path)
    monkeypatch.setattr(scryfall, "ORACLE_CARDS_PATH", oracle_path)
    monkeypatch.setattr(scryfall, "METADATA_PATH", metadata_path)
    client = ScryfallClient()
    client.client.close()
    client.client = Http()
    monkeypatch.setattr(client, "_fetch_bulk_metadata", lambda: {
        "jsonl_download_uri": "https://data.scryfall.io/oracle.jsonl.gz",
        "updated_at": "broken",
        "compressed_size": len(gzip.compress(b'{"name":"Brainstorm"}\nnot-json\n')),
    })

    with pytest.raises(json.JSONDecodeError):
        client.download_bulk_data(force=True)

    assert json.loads(oracle_path.read_text()) == [NORMAL]
    assert metadata_path.read_text() == '{"updated_at":"last-good"}'


def test_truncated_jsonl_candidate_preserves_last_good_oracle_and_metadata(tmp_path, monkeypatch):
    oracle_path = tmp_path / "oracle_cards.json"
    metadata_path = tmp_path / "metadata.json"
    oracle_path.write_text(json.dumps([NORMAL, LAND]), encoding="utf-8")
    metadata_path.write_text('{"updated_at":"last-good"}', encoding="utf-8")

    class Response:
        headers = {"content-encoding": "gzip"}
        def raise_for_status(self): return None
        def iter_raw(self, chunk_size):
            yield gzip.compress((json.dumps(NORMAL) + "\n").encode())
        def __enter__(self): return self
        def __exit__(self, *args): return None

    class Http:
        def stream(self, *args, **kwargs): return Response()
        def close(self): return None

    monkeypatch.setattr(scryfall, "SCRYFALL_DIR", tmp_path)
    monkeypatch.setattr(scryfall, "ORACLE_CARDS_PATH", oracle_path)
    monkeypatch.setattr(scryfall, "METADATA_PATH", metadata_path)
    client = ScryfallClient()
    client.client.close()
    client.client = Http()
    monkeypatch.setattr(client, "_fetch_bulk_metadata", lambda: {
        "jsonl_download_uri": "https://data.scryfall.io/oracle.jsonl.gz",
        "updated_at": "truncated",
        "compressed_size": len(gzip.compress((json.dumps(NORMAL) + "\n").encode())) + 1,
    })

    with pytest.raises(ValueError, match="compressed size mismatch"):
        client.download_bulk_data(force=True)
    assert json.loads(oracle_path.read_text()) == [NORMAL, LAND]
    assert metadata_path.read_text() == '{"updated_at":"last-good"}'


def test_download_prices_bulk_accepts_jsonl_metadata(tmp_path, monkeypatch):
    price_path = tmp_path / "default_cards.json"
    metadata_path = tmp_path / "prices_metadata.json"
    price = {
        "id": "p1", "name": "Brainstorm", "layout": "normal",
        "games": ["paper"], "set": "ice", "prices": {"usd": "1.00"},
    }

    class Response:
        headers = {"content-encoding": "gzip"}

        def raise_for_status(self):
            return None

        def iter_raw(self, chunk_size):
            yield gzip.compress((json.dumps(price) + "\n").encode())

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class Http:
        def stream(self, *args, **kwargs):
            return Response()

        def close(self):
            return None

    monkeypatch.setattr(scryfall, "SCRYFALL_DIR", tmp_path)
    monkeypatch.setattr(scryfall, "SCRYFALL_PRICES_PATH", price_path)
    monkeypatch.setattr(scryfall, "SCRYFALL_PRICES_META_PATH", metadata_path)
    client = ScryfallClient()
    client.client.close()
    client.client = Http()
    monkeypatch.setattr(client, "_fetch_prices_metadata", lambda: {
        "jsonl_download_uri": "https://data.scryfall.io/default.jsonl.gz",
        "updated_at": "2026-08-11T00:00:00Z",
        "compressed_size": len(gzip.compress((json.dumps(price) + "\n").encode())),
    })

    client.download_prices_bulk(force=True)

    rows = list(client.iter_price_rows(price_path))
    assert len(rows) == 1
    assert rows[0].name == "Brainstorm"


# ---------------------------------------------------------------------------
# _validate_scryfall_uri — SSRF host allowlist
# ---------------------------------------------------------------------------


class TestValidateScryfallUri:
    """_validate_scryfall_uri must accept Scryfall-owned hosts and reject others."""

    @pytest.mark.parametrize("uri", [
        "https://api.scryfall.com/bulk-data/oracle_cards",
        "https://c2.scryfall.com/file/scryfall-bulk/oracle-cards-20260101.json",
        "https://data.scryfall.io/oracle-cards-20260101.json",
        "https://cdn.scryfall.com/file/oracle-cards.json",
    ])
    def test_scryfall_hosts_accepted(self, uri):
        _validate_scryfall_uri(uri)  # must not raise

    @pytest.mark.parametrize("uri", [
        "https://evil.com/malicious",
        "https://169.254.169.254/latest/meta-data/",
        "http://localhost/admin",
        "http://internal.corp/secret",
        "https://notscryfall.com/file.json",
    ])
    def test_non_scryfall_hosts_rejected(self, uri):
        with pytest.raises(ValueError, match="not in the allowlist"):
            _validate_scryfall_uri(uri)

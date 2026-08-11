from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone

import pytest

from legacy_engine.ingestion import store
from legacy_engine.ingestion.card_coverage import reconcile_card_dimension
from legacy_engine.ingestion import scryfall
from legacy_engine.ingestion.scryfall import ScryfallClient, normalize_alias_key
from legacy_engine.models.card import Card, CardAliasManifest, CardNameStatus


NOW = datetime(2026, 8, 11, tzinfo=timezone.utc)


def _manifest(**overrides) -> CardAliasManifest:
    values = {
        "source_updated_at": "2026-08-10T00:00:00Z",
        "built_at": NOW,
        "release_codes": ("eoe",),
        "alias_count": 0,
        "ambiguous_key_count": 0,
    }
    values.update(overrides)
    return CardAliasManifest(**values)


def _write_jsonl_gzip(path, rows) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


class TestPrintedAliasStream:
    def test_streams_top_level_and_face_aliases_with_provenance(self, tmp_path):
        path = tmp_path / "all-cards.json.gz"
        _write_jsonl_gzip(path, [
            {
                "id": "pt-1",
                "lang": "pt",
                "name": "Counterspell",
                "printed_name": "Contramágica",
            },
            {
                "id": "ru-1",
                "lang": "ru",
                "name": "Fire // Ice",
                "card_faces": [{"name": "Fire", "printed_name": "Огонь"}],
            },
        ])
        client = ScryfallClient()
        try:
            aliases = list(client.iter_printed_aliases(path))
        finally:
            client.close()
        assert [(item.printed_name, item.canonical_name, item.language) for item in aliases] == [
            ("Contramágica", "Counterspell", "pt"),
            ("Огонь", "Fire", "ru"),
        ]
        assert aliases[0].scryfall_id == "pt-1"

    def test_alias_key_normalizes_unicode_apostrophe_accents_case_and_space(self):
        assert normalize_alias_key("  CONTRAMÁGICA  ") == "contramagica"
        assert normalize_alias_key("Urza’s   Saga") == "urza's saga"

    def test_download_preserves_transport_gzip_and_validates_full_stream(self, tmp_path, monkeypatch):
        raw = (json.dumps({
            "id": "pt-1", "lang": "pt", "name": "Counterspell",
            "printed_name": "Contramágica",
        }, ensure_ascii=False) + "\n").encode()
        compressed = gzip.compress(raw)

        class Response:
            headers = {"content-encoding": "gzip"}
            def raise_for_status(self):
                return None
            def iter_raw(self, chunk_size):
                yield compressed
            def iter_bytes(self, chunk_size):
                raise AssertionError("decoded bytes must not be persisted as .gz")
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
        monkeypatch.setattr(scryfall, "SCRYFALL_ALL_CARDS_PATH", tmp_path / "all.json.gz")
        monkeypatch.setattr(scryfall, "SCRYFALL_ALL_CARDS_META_PATH", tmp_path / "meta.json")
        monkeypatch.setattr(scryfall, "_ALL_CARDS_MIN_ROWS", 1)
        monkeypatch.setattr(scryfall, "_ALL_CARDS_MIN_ALIASES", 1)
        client = ScryfallClient()
        client.client.close()
        client.client = Http()
        monkeypatch.setattr(client, "_fetch_all_cards_metadata", lambda: {
            "download_uri": "https://data.scryfall.io/all.json", "updated_at": "2026-08-10",
        })

        path = client.download_all_cards_bulk(force=True)

        assert gzip.decompress(path.read_bytes()) == raw
        assert [item.canonical_name for item in client.iter_printed_aliases(path)] == ["Counterspell"]

    @pytest.mark.parametrize(
        "payload",
        [
            b"[]",
            b'{"object":"error","details":"provider failure"}\n',
            b'{"lang":"pt","name":"Counterspell","printed_name":"Contramagica"}\n',
            (
                json.dumps({
                    "id": "pt-1", "lang": "pt", "name": "Counterspell",
                    "printed_name": "Contramagica",
                }) + "\n"
            ).encode(),
        ],
        ids=("empty-array", "error-object", "missing-provenance", "implausibly-incomplete"),
    )
    def test_invalid_download_candidate_preserves_last_good_snapshot(
        self, tmp_path, monkeypatch, payload,
    ):
        old_raw = gzip.compress(b'{"id":"old","lang":"pt","name":"Old","printed_name":"Velho"}\n')
        raw_path = tmp_path / "all.json.gz"
        meta_path = tmp_path / "meta.json"
        raw_path.write_bytes(old_raw)
        meta_path.write_text('{"updated_at":"old"}')
        candidate = gzip.compress(payload)

        class Response:
            headers = {"content-encoding": "gzip"}
            def raise_for_status(self):
                return None
            def iter_raw(self, chunk_size):
                yield candidate
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
        monkeypatch.setattr(scryfall, "SCRYFALL_ALL_CARDS_PATH", raw_path)
        monkeypatch.setattr(scryfall, "SCRYFALL_ALL_CARDS_META_PATH", meta_path)
        monkeypatch.setattr(scryfall, "_ALL_CARDS_MIN_ROWS", 2)
        monkeypatch.setattr(scryfall, "_ALL_CARDS_MIN_ALIASES", 1)
        client = ScryfallClient()
        client.client.close()
        client.client = Http()
        monkeypatch.setattr(client, "_fetch_all_cards_metadata", lambda: {
            "download_uri": "https://data.scryfall.io/all.json",
            "updated_at": "2026-08-11T00:00:00Z",
        })

        with pytest.raises(ValueError):
            client.download_all_cards_bulk(force=True)

        assert raw_path.read_bytes() == old_raw
        assert meta_path.read_text() == '{"updated_at":"old"}'


class TestAliasStore:
    def test_preserves_colliding_canonical_candidates_and_manifest(self):
        from legacy_engine.models.card import PrintedCardAlias

        con = store.connect(":memory:")
        aliases = [
            PrintedCardAlias(
                printed_name="Alias", normalized_alias="alias", canonical_name="Card A",
                language="pt", scryfall_id="2",
            ),
            PrintedCardAlias(
                printed_name="ALIAS", normalized_alias="alias", canonical_name="Card B",
                language="fr", scryfall_id="1",
            ),
        ]
        effective = store.rebuild_card_aliases(con, aliases, manifest=_manifest())
        candidates = store.fetch_card_alias_candidates(con, "Alias")
        assert {item.canonical_name for item in candidates} == {"Card A", "Card B"}
        assert effective.alias_count == 2
        assert effective.ambiguous_key_count == 1
        assert store.load_card_alias_manifest(con) == effective
        con.close()

    def test_release_code_gate_reuses_current_snapshot(self):
        assert not store.alias_snapshot_needs_refresh(_manifest(), ["eoe"])
        assert store.alias_snapshot_needs_refresh(_manifest(), ["eoe", "new"])
        assert store.alias_snapshot_needs_refresh(None, [])

    def test_invalid_candidate_preserves_last_good_alias_state(self):
        from legacy_engine.models.card import PrintedCardAlias

        con = store.connect(":memory:")
        old = [
            PrintedCardAlias(
                printed_name=f"Alias {index}", normalized_alias=f"alias {index}",
                canonical_name=f"Card {index}", language="pt", scryfall_id=str(index),
            )
            for index in range(4)
        ]
        last_good = store.rebuild_card_aliases(
            con, old, manifest=_manifest(alias_count=4),
        )
        incomplete = [old[0]]

        with pytest.raises(ValueError, match="implausibly incomplete"):
            store.rebuild_card_aliases(
                con, incomplete, manifest=_manifest(source_updated_at="new"),
            )

        assert store.load_card_alias_manifest(con) == last_good
        assert len(store.fetch_card_alias_candidates(con, "Alias 3")) == 1
        con.close()


class TestCardDimensionReconciliation:
    def _con(self):
        con = store.connect(":memory:")
        store.init_schema(con)
        store.load_cards(con, [Card(name="Counterspell"), Card(name="New Card"), Card(name="Card A"), Card(name="Card B")])
        return con

    def test_resolves_unique_localized_and_new_card_but_not_ambiguous_or_truncated(self):
        from legacy_engine.models.card import PrintedCardAlias

        con = self._con()
        aliases = [
            PrintedCardAlias(
                printed_name="Contramágica", normalized_alias=normalize_alias_key("Contramágica"),
                canonical_name="Counterspell", language="pt", scryfall_id="pt-1",
            ),
            PrintedCardAlias(
                printed_name="Alias", normalized_alias="alias", canonical_name="Card A",
                language="pt", scryfall_id="a",
            ),
            PrintedCardAlias(
                printed_name="Alias", normalized_alias="alias", canonical_name="Card B",
                language="fr", scryfall_id="b",
            ),
            PrintedCardAlias(
                printed_name="Длинное Имя", normalized_alias=normalize_alias_key("Длинное Имя"),
                canonical_name="Counterspell", language="ru", scryfall_id="ru-1",
            ),
        ]
        manifest = store.rebuild_card_aliases(con, aliases, manifest=_manifest())
        con.executemany(
            "INSERT INTO deck_cards VALUES (?, ?, 'main', ?, 1)",
            [("t", index, name) for index, name in enumerate(
                ["CONTRAMÁGICA", "new card", "Alias", "Длинное", "Mystery"]
            )],
        )

        report = reconcile_card_dimension(
            con,
            new_card_names=frozenset({"New Card"}),
            alias_manifest=manifest,
            alias_snapshot_reason=None,
            resolved_at=NOW,
        )

        names = [row[0] for row in con.execute("SELECT name FROM deck_cards ORDER BY deck_idx").fetchall()]
        assert names == ["Counterspell", "New Card", "Alias", "Длинное", "Mystery"]
        assert report.localized_recovered[0].language == "pt"
        assert report.localized_recovered[0].scryfall_id == "pt-1"
        assert report.new_cards_recovered[0].status is CardNameStatus.NEW_CARD
        assert [item.observed_name for item in report.ambiguous] == ["Alias"]
        assert [item.observed_name for item in report.suspected_truncated] == ["Длинное"]
        assert [item.observed_name for item in report.unresolved] == ["Mystery"]
        assert report.unresolved_count == 3
        con.close()

    def test_empty_corpus_returns_explicit_zero_gap_report(self):
        con = self._con()
        report = reconcile_card_dimension(
            con,
            new_card_names=frozenset(),
            alias_manifest=None,
            alias_snapshot_reason="snapshot unavailable",
            resolved_at=NOW,
        )
        assert report.distinct_names == 0
        assert report.unresolved_count == 0
        assert report.alias_snapshot_degraded
        con.close()

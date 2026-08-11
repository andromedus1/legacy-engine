from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from legacy_engine.advisory.ranking_benchmark import (
    BenchmarkFold,
    BenchmarkProtocol,
    protocol_sha256,
    write_frozen_predictions,
)
from legacy_engine.ingestion import store
from legacy_engine.workflows.ranking_benchmark import build_origin_snapshot, freeze_origin_predictions


def _source_db(path: Path, *, future_result: str = "2-0") -> Path:
    con = store.connect(path)
    store.init_schema(con)
    con.executemany(
        "INSERT INTO cards (name) VALUES (?)",
        [("Brainstorm",), ("Future Card",)],
    )
    con.executemany(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("past", "Past", "2025-12-20", "u1", "Legacy", "fixture", "online"),
            ("future", "Future", "2026-01-10", "u2", "Legacy", "fixture", "online"),
        ],
    )
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("past", 0, "alice", "1st", "Alpha", "Old Camp"),
            ("past", 1, "bob", "2nd", "Beta", None),
            ("future", 0, "future-alias", "1st", "Future Archetype", "Promoted Camp"),
            ("future", 1, "other", "2nd", "Alpha", None),
        ],
    )
    con.executemany(
        "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
        [
            ("past", 0, "main", "Brainstorm", 4),
            ("past", 1, "main", "Brainstorm", 4),
            ("future", 0, "main", "Future Card", 4),
        ],
    )
    con.executemany(
        "INSERT INTO rounds VALUES (?, ?, ?, ?, ?)",
        [
            ("past", 0, "alice", "bob", "2-0"),
            ("future", 0, "future-alias", "other", future_result),
        ],
    )
    con.execute("INSERT INTO player_aliases VALUES ('future-alias', 'future-player')")
    con.execute("CREATE TABLE entity_eras (entity VARCHAR, stable_since VARCHAR)")
    con.execute("INSERT INTO entity_eras VALUES ('Alpha', '2026-01-10')")
    con.execute("CREATE TABLE superarchetype_members (member VARCHAR, cluster VARCHAR)")
    con.execute("INSERT INTO superarchetype_members VALUES ('Alpha', 'Future Family')")
    con.close()
    return path


def _fold() -> BenchmarkFold:
    return BenchmarkFold(
        fold_id="2026-01-01--2026-01-29", cutoff="2026-01-01",
        evaluation_until="2026-01-29", regime_start="2025-11-10", regime_end=None,
        event_dates=("2026-01-10",),
    )


def _protocol() -> BenchmarkProtocol:
    return BenchmarkProtocol(
        protocol_id="snapshot-test", created_at="2026-01-01T00:00:00Z",
        taxonomy_mode="retrospective-fixed-parent", first_cutoff="2026-01-01",
        final_evaluation_until="2026-01-29",
    )


def test_snapshot_excludes_every_future_or_derived_surface(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    output = tmp_path / "snapshot.duckdb"
    manifest = build_origin_snapshot(
        source, output, fold=_fold(), protocol_hash="protocol",
    )

    assert manifest.max_training_event_date == "2025-12-20"
    assert manifest.training_events == 1
    assert manifest.degraded is True
    con = duckdb.connect(str(output), read_only=True)
    assert con.execute("SELECT id FROM tournaments").fetchall() == [("past",)]
    assert con.execute("SELECT DISTINCT variant FROM decks").fetchall() == [(None,)]
    assert con.execute("SELECT name FROM cards").fetchall() == [("Brainstorm",)]
    assert con.execute("SELECT count(*) FROM player_aliases").fetchone()[0] == 0
    assert not con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name='superarchetype_members'"
    ).fetchone()[0]
    con.close()


def test_post_cutoff_changes_leave_manifest_identical(tmp_path):
    one = _source_db(tmp_path / "one.duckdb", future_result="2-0")
    two = _source_db(tmp_path / "two.duckdb", future_result="0-2")
    first = build_origin_snapshot(one, tmp_path / "one-snapshot.duckdb", fold=_fold(), protocol_hash="p")
    second = build_origin_snapshot(two, tmp_path / "two-snapshot.duckdb", fold=_fold(), protocol_hash="p")
    assert first == second


def test_contemporaneous_taxonomy_fails_closed_when_future_dated(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    taxonomy = tmp_path / "taxonomy"
    taxonomy.mkdir()
    rules = taxonomy / "rules.json"
    rules.write_text("{}")
    (taxonomy / "manifest.json").write_text(json.dumps({
        "source": "fixture", "effective_at": "2026-02-01", "action_level": "parent",
        "rules_manifest": "rules.json", "rules_sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
    }))
    with pytest.raises(ValueError, match="later than"):
        build_origin_snapshot(
            source, tmp_path / "snapshot.duckdb", fold=_fold(), protocol_hash="p",
            taxonomy_mode="contemporaneous", taxonomy_snapshot=taxonomy,
        )


def test_freeze_is_deterministic_and_emits_every_preregistered_estimator(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    snapshot = tmp_path / "snapshot.duckdb"
    configured = _protocol()
    manifest = build_origin_snapshot(
        source, snapshot, fold=_fold(), protocol_hash=protocol_sha256(configured),
    )
    first = freeze_origin_predictions(snapshot, protocol=configured, manifest=manifest)
    second = freeze_origin_predictions(snapshot, protocol=configured, manifest=manifest)
    assert first == second
    assert {item.estimator for item in first.recommendations} == set(configured.estimator_ids)
    assert {item.estimator for item in first.matchup_predictions} == set(configured.estimator_ids)
    assert all("future" not in item.subject.casefold() for item in first.matchup_predictions)
    ci = next(item for item in first.matchup_predictions if (
        item.estimator == "production-ci-gated" and item.subject == "Alpha"
        and item.opponent == "Beta"
    ))
    selected = first.methodology["Alpha"]["canonical"]["cells"][1]["selected"]
    assert ci.probability == selected["cell"]["p_shrunk"]

    one_hash = write_frozen_predictions(tmp_path / "one.json", first)
    two_hash = write_frozen_predictions(tmp_path / "two.json", second)
    assert one_hash == two_hash
    assert (tmp_path / "one.json").read_bytes() == (tmp_path / "two.json").read_bytes()

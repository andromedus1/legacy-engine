from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from legacy_engine.advisory.ranking_benchmark import (
    BenchmarkFold,
    BenchmarkProtocol,
    CardMetadataPolicy,
    protocol_sha256,
    write_frozen_predictions,
)
from legacy_engine.ingestion import store
from legacy_engine.workflows.ranking_benchmark import (
    build_origin_snapshot,
    freeze_origin_predictions,
    load_heldout_outcomes,
    load_heldout_matches,
    validate_frozen_taxonomy,
)


def _source_db(path: Path, *, future_result: str = "2-0") -> Path:
    con = store.connect(path)
    store.init_schema(con)
    con.executemany(
        "INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("Brainstorm", "{U}", 1.0, "Instant", "U", "", "", "normal", False, None, None),
            ("Ponder", "{U}", 1.0, "Sorcery", "U", "", "", "normal", False, None, None),
            ("Future Card", "{1}", 1.0, "Artifact", "", "", "", "normal", False, None, None),
        ],
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
            ("past", 1, "main", "Ponder", 4),
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


@pytest.fixture(autouse=True)
def _pinned_retrospective_rules(tmp_path, monkeypatch):
    import legacy_engine.workflows.ranking_benchmark as workflow

    snapshot = _taxonomy_snapshot(tmp_path / "retrospective-taxonomy")
    monkeypatch.setattr(workflow, "RULES_DIR", snapshot / "rules")


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
    assert con.execute("SELECT name FROM cards ORDER BY name").fetchall() == [
        ("Brainstorm",), ("Ponder",),
    ]
    assert con.execute("SELECT count(*) FROM player_aliases").fetchone()[0] == 0
    assert not con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name='superarchetype_members'"
    ).fetchone()[0]
    con.close()


def test_optional_color_split_registry_matches_production_parent_labeling(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    color_path = tmp_path / "color-splits.json"
    color_path.write_text(json.dumps({
        "version": "test",
        "splits": [{
            "parent": "Alpha", "min_copies": 1,
            "buckets": [
                {"name": "Blue Alpha", "requires_any": ["U"]},
                {"name": "Other Alpha", "forbids_all": ["U"]},
            ],
        }],
    }))
    snapshot = tmp_path / "snapshot.duckdb"
    manifest = build_origin_snapshot(
        source, snapshot, fold=_fold(), protocol_hash="protocol",
        color_splits_path=color_path,
    )
    assert manifest.color_splits_sha256 == hashlib.sha256(color_path.read_bytes()).hexdigest()
    con = duckdb.connect(str(snapshot), read_only=True)
    assert con.execute(
        "SELECT archetype FROM decks WHERE tournament_id='past' AND deck_idx=0"
    ).fetchone() == ("Blue Alpha",)
    con.close()
    outcomes = load_heldout_outcomes(
        source, _fold(), color_splits_path=color_path,
        expected_color_splits_sha256=manifest.color_splits_sha256,
    )
    assert all(match.match_idx is not None for match in outcomes.matches)
    with pytest.raises(ValueError, match="color-split registry hash"):
        load_heldout_outcomes(
            source, _fold(), color_splits_path=color_path,
            expected_color_splits_sha256="tampered",
        )


def test_quarantine_snapshot_removes_whole_training_deck_before_classification(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    con = store.connect(source)
    con.execute("DELETE FROM rounds WHERE tournament_id='past'")
    # One unresolved deck among 200 is exactly the preregistered 0.5% ceiling.
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
        [("past", idx, f"player-{idx}", "", None, None) for idx in range(2, 200)],
    )
    con.close()
    con = store.connect(source)
    policy = CardMetadataPolicy(
        mode="quarantine-unresolved-decks", max_deck_fraction=0.005, max_round_fraction=0.02,
    )
    # Make the first deck corrupt; it is removed as a unit, not partially repaired.
    con.execute("UPDATE deck_cards SET name='Unresolved' WHERE tournament_id='past' AND deck_idx=0")
    con.close()
    output = tmp_path / "snapshot.duckdb"
    manifest = build_origin_snapshot(
        source, output, fold=_fold(), protocol_hash="protocol", card_metadata_policy=policy,
    )
    assert manifest.card_metadata_quarantine is not None
    assert manifest.card_metadata_quarantine.retained_decks == 199
    assert manifest.card_metadata_quarantine.excluded_decks[0].unresolved_names == ("Unresolved",)
    con = duckdb.connect(str(output), read_only=True)
    assert con.execute("SELECT count(*) FROM decks").fetchone()[0] == 199
    assert con.execute("SELECT count(*) FROM deck_cards WHERE name='Unresolved'").fetchone()[0] == 0
    con.close()


def test_quarantine_manifest_binds_policy_digest_and_retained_snapshot(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    policy = CardMetadataPolicy(
        mode="quarantine-unresolved-decks", max_deck_fraction=0.005, max_round_fraction=0.02,
    )
    configured = _protocol().model_copy(update={
        "registered_at": "2025-12-01T00:00:00Z",
        "claim_ceiling": "descriptive", "card_metadata": policy,
    })
    snapshot = tmp_path / "snapshot.duckdb"
    manifest = build_origin_snapshot(
        source, snapshot, fold=_fold(), protocol_hash=protocol_sha256(configured),
        card_metadata_policy=policy,
    )
    assert manifest.card_metadata_quarantine_sha256 == manifest.card_metadata_quarantine.digest
    frozen = freeze_origin_predictions(snapshot, protocol=configured, manifest=manifest)
    assert frozen.protocol_hash == protocol_sha256(configured)
    with pytest.raises(ValueError, match="digest mismatch"):
        freeze_origin_predictions(
            snapshot, protocol=configured,
            manifest=manifest.model_copy(update={"card_metadata_quarantine_sha256": "tampered"}),
        )


def test_quarantine_heldout_outcomes_bind_ledger_and_retained_hash(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    policy = CardMetadataPolicy(
        mode="quarantine-unresolved-decks", max_deck_fraction=0.005, max_round_fraction=0.02,
    )
    outcomes = load_heldout_outcomes(
        source, _fold(), card_metadata_policy=policy,
    )
    assert outcomes.card_metadata_quarantine is not None
    assert outcomes.card_metadata_quarantine_sha256 == outcomes.card_metadata_quarantine.digest


def test_quarantine_heldout_outcomes_honors_excluded_round_identity(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    con = store.connect(source)
    con.execute(
        "UPDATE deck_cards SET name='Unresolved' "
        "WHERE tournament_id='future' AND deck_idx=0"
    )
    # Keep the single affected round below the fixed two-percent round ceiling.
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
        [("future", index, f"ghost-{index}", "", None, None) for index in range(2, 202)],
    )
    con.executemany(
        "INSERT INTO rounds VALUES (?, ?, ?, ?, ?)",
        [("future", index, f"missing-{index}", f"other-{index}", "2-0")
         for index in range(1, 101)],
    )
    con.close()
    policy = CardMetadataPolicy(
        mode="quarantine-unresolved-decks", max_deck_fraction=0.005, max_round_fraction=0.02,
    )
    outcomes = load_heldout_outcomes(source, _fold(), card_metadata_policy=policy)
    affected = next(match for match in outcomes.matches if match.match_idx == 0)
    assert affected.exclusion_reason == "card-metadata-unresolved"
    assert affected.match_idx == 0


def test_heldout_outcome_and_stored_label_mutations_do_not_change_ledger_digest(tmp_path):
    one = _source_db(tmp_path / "one.duckdb", future_result="2-0")
    two = _source_db(tmp_path / "two.duckdb", future_result="0-2")
    con = store.connect(two)
    con.execute("UPDATE decks SET archetype='Mutated Label' WHERE tournament_id='future'")
    con.close()
    policy = CardMetadataPolicy(
        mode="quarantine-unresolved-decks", max_deck_fraction=0.005, max_round_fraction=0.02,
    )
    first = load_heldout_outcomes(one, _fold(), card_metadata_policy=policy)
    second = load_heldout_outcomes(two, _fold(), card_metadata_policy=policy)
    assert first.card_metadata_quarantine.digest == second.card_metadata_quarantine.digest


def test_post_cutoff_changes_leave_manifest_identical(tmp_path):
    one = _source_db(tmp_path / "one.duckdb", future_result="2-0")
    two = _source_db(tmp_path / "two.duckdb", future_result="0-2")
    first = build_origin_snapshot(one, tmp_path / "one-snapshot.duckdb", fold=_fold(), protocol_hash="p")
    second = build_origin_snapshot(two, tmp_path / "two-snapshot.duckdb", fold=_fold(), protocol_hash="p")
    assert first == second


def test_retrospective_training_replays_rules_and_ignores_stored_label_mutation(tmp_path):
    first_source = _source_db(tmp_path / "first.duckdb")
    second_source = _source_db(tmp_path / "second.duckdb")
    con = store.connect(second_source)
    con.execute(
        "UPDATE decks SET archetype='Mutable Stored Label', variant='Mutable Variant' "
        "WHERE tournament_id='past'"
    )
    con.close()
    protocol = _protocol()
    first_manifest = build_origin_snapshot(
        first_source, tmp_path / "first-snapshot.duckdb", fold=_fold(),
        protocol_hash=protocol_sha256(protocol),
    )
    second_manifest = build_origin_snapshot(
        second_source, tmp_path / "second-snapshot.duckdb", fold=_fold(),
        protocol_hash=protocol_sha256(protocol),
    )
    assert first_manifest == second_manifest
    first = freeze_origin_predictions(
        tmp_path / "first-snapshot.duckdb", protocol=protocol, manifest=first_manifest,
    )
    second = freeze_origin_predictions(
        tmp_path / "second-snapshot.duckdb", protocol=protocol, manifest=second_manifest,
    )
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


def _taxonomy_snapshot(path: Path) -> Path:
    rules = path / "rules" / "Formats" / "Legacy" / "Archetypes"
    rules.mkdir(parents=True)
    (rules / "Alpha.json").write_text(json.dumps({
        "Name": "Alpha", "Conditions": [{"Type": "InMainboard", "Cards": ["Brainstorm"]}],
    }))
    (rules / "Beta.json").write_text(json.dumps({
        "Name": "Beta", "Conditions": [{"Type": "InMainboard", "Cards": ["Ponder"]}],
    }))
    digest = hashlib.sha256()
    root = path / "rules"
    for item in sorted(file for file in root.rglob("*") if file.is_file()):
        digest.update(item.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    (path / "manifest.json").write_text(json.dumps({
        "source": "fixture", "effective_at": "2025-12-01", "action_level": "parent",
        "rules_manifest": "rules", "rules_sha256": digest.hexdigest(),
    }))
    return path


def test_contemporaneous_rules_classify_training_and_holdout_with_same_payload(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    con = store.connect(source)
    con.execute(
        "UPDATE cards SET cmc=1, type_line='Instant', colors='U', produced_mana='', "
        "oracle_text='', layout='normal', is_land=false"
    )
    con.execute("UPDATE deck_cards SET name='Ponder' WHERE deck_idx=1")
    con.execute("DELETE FROM deck_cards WHERE tournament_id='future'")
    con.executemany(
        "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
        [("future", 0, "main", "Brainstorm", 4), ("future", 1, "main", "Ponder", 4)],
    )
    con.execute("UPDATE decks SET archetype='Wrong Current Label'")
    con.close()
    taxonomy = _taxonomy_snapshot(tmp_path / "taxonomy")
    snapshot = tmp_path / "snapshot.duckdb"
    configured = _protocol().model_copy(update={"taxonomy_mode": "contemporaneous"})
    build_origin_snapshot(
        source, snapshot, fold=_fold(), protocol_hash=protocol_sha256(configured),
        taxonomy_mode="contemporaneous", taxonomy_snapshot=taxonomy,
    )
    con = duckdb.connect(str(snapshot), read_only=True)
    assert con.execute("SELECT archetype FROM decks ORDER BY deck_idx").fetchall() == [
        ("Alpha",), ("Beta",),
    ]
    con.close()
    heldout = load_heldout_matches(source, _fold(), taxonomy_snapshot=taxonomy)
    assert [(match.subject, match.opponent) for match in heldout] == [("Alpha", "Beta")]


def test_evaluation_taxonomy_must_match_frozen_prediction_identity(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    con = store.connect(source)
    con.execute(
        "UPDATE cards SET cmc=1, type_line='Instant', colors='U', produced_mana='', "
        "oracle_text='', layout='normal', is_land=false"
    )
    con.close()
    snapshot = tmp_path / "snapshot.duckdb"
    configured = _protocol().model_copy(update={"taxonomy_mode": "contemporaneous"})
    frozen_taxonomy = _taxonomy_snapshot(tmp_path / "frozen-taxonomy")
    manifest = build_origin_snapshot(
        source, snapshot, fold=_fold(), protocol_hash=protocol_sha256(configured),
        taxonomy_mode="contemporaneous", taxonomy_snapshot=frozen_taxonomy,
    )
    predictions = freeze_origin_predictions(snapshot, protocol=configured, manifest=manifest)
    validate_frozen_taxonomy(predictions, frozen_taxonomy)

    different_taxonomy = _taxonomy_snapshot(tmp_path / "different-taxonomy")
    different_manifest_path = different_taxonomy / "manifest.json"
    different_manifest = json.loads(different_manifest_path.read_text())
    different_manifest["effective_at"] = "2025-12-02"
    different_manifest_path.write_text(json.dumps(different_manifest))
    with pytest.raises(ValueError, match="does not match frozen predictions"):
        validate_frozen_taxonomy(predictions, different_taxonomy)


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

    # Byte-identical replay is allowed; a different artifact may not replace the frozen path.
    assert write_frozen_predictions(tmp_path / "one.json", first) == one_hash
    with pytest.raises(FileExistsError, match="refusing to overwrite different artifact"):
        write_frozen_predictions(
            tmp_path / "one.json", first.model_copy(update={"code_commit": "different"}),
        )


def test_boundary_origin_uses_declared_trailing_field_and_replays_snapshot_idempotently(tmp_path):
    source = _source_db(tmp_path / "source.duckdb")
    snapshot = tmp_path / "snapshot.duckdb"
    boundary = _fold().model_copy(update={"regime_start": _fold().cutoff})
    configured = _protocol()
    first = build_origin_snapshot(
        source, snapshot, fold=boundary, protocol_hash=protocol_sha256(configured),
    )
    second = build_origin_snapshot(
        source, snapshot, fold=boundary, protocol_hash=protocol_sha256(configured),
    )
    assert first == second
    assert any("trailing 28-day" in reason for reason in first.reasons)
    frozen = freeze_origin_predictions(snapshot, protocol=configured, manifest=first)
    assert frozen.action_universe == ("Alpha", "Beta")


def test_retrospective_holdout_ignores_stored_relabels_and_rejects_rule_drift(tmp_path, monkeypatch):
    source = _source_db(tmp_path / "source.duckdb")
    expected = hashlib.sha256(b"frozen-rules").hexdigest()
    import legacy_engine.workflows.ranking_benchmark as workflow

    monkeypatch.setattr(workflow, "_tree_hash", lambda _path: expected)
    first = load_heldout_outcomes(
        source, _fold(), expected_rules_sha256=expected,
    )
    con = duckdb.connect(str(source))
    con.execute("UPDATE decks SET archetype='Post-freeze relabel' WHERE tournament_id='future'")
    con.close()
    second = load_heldout_outcomes(
        source, _fold(), expected_rules_sha256=expected,
    )
    assert first == second

    monkeypatch.setattr(workflow, "_tree_hash", lambda _path: "changed")
    with pytest.raises(ValueError, match="rules changed after prediction freeze"):
        load_heldout_outcomes(source, _fold(), expected_rules_sha256=expected)

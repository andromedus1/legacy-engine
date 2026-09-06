from datetime import date
import json

import duckdb
import pytest

from legacy_engine.analytics.eras.certification import load_certification_calibration
from legacy_engine.analytics.eras.certification import SemanticFact
from legacy_engine.analytics.eras.certification_run import run_recurrent_certification
from legacy_engine.analytics.eras.certificate_store import (
    certification_run_ids,
    init_certificate_schema,
    read_certification_run,
    write_certification_run,
)
from legacy_engine.analytics.eras.discovery import DiscoveryCalibration
from legacy_engine.analytics.eras.discovery_run import run_recurrent_discovery
from legacy_engine.config import CERTIFICATION_CALIBRATION_PATH


def _db(n=12):
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE tournaments (id VARCHAR, date DATE, source VARCHAR, provenance VARCHAR)")
    con.execute("CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, archetype VARCHAR)")
    con.execute("CREATE TABLE deck_cards (tournament_id VARCHAR, deck_idx INTEGER, board VARCHAR, name VARCHAR, count INTEGER)")
    rows = [(f"e{i}", date(2026, 1, 5 + i), "mtgo" if i % 2 else "paper", "online") for i in range(n)]
    con.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?)", rows)
    con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?)", [(f"e{i}", 0, f"pilot-{i}", "X") for i in range(n)])
    con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [(f"e{i}", 0, "main", "A", 4) for i in range(n)])
    return con


def _discovery_calibration():
    return DiscoveryCalibration.model_validate({
        "calibration_id": "run-test-v2", "method_id": "segment-fingerprint-complete-link-v2",
        "bucket_days": 7, "min_segment_buckets": 1, "min_segment_decks": 1,
        "min_segment_events": 1, "min_subject_decks": 1, "pelt_penalty": 0.5, "smoothing_alpha": 0.5,
        "weights": {"main": 0.4, "side": 0.25, "field": 0.2, "source": 0.1, "subject_share": 0.05},
        "thresholds": {"main_js_max": 0.12, "side_js_max": 0.18, "mixture_energy_max": 0.2, "field_js_max": 0.25, "source_js_max": 0.25},
    })


def test_no_candidate_entity_is_persisted_and_exact_retries_round_trip():
    con = _db()
    discovery = run_recurrent_discovery(con, as_of=date(2026, 1, 31), taxonomy_version="t", legality_version="l",
                                        calibration=_discovery_calibration())
    run = run_recurrent_certification(
        con, discovery_run_id=discovery.run_id,
        calibration=load_certification_calibration(CERTIFICATION_CALIBRATION_PATH),
        semantic_facts=(), format_observation_sha256=None,
    )
    assert run.results
    assert run.run_id
    init_certificate_schema(con)
    write_certification_run(con, run)
    write_certification_run(con, run)
    stored = read_certification_run(con, run.run_id)
    assert stored is not None
    assert stored.run_id == run.run_id
    assert stored.knowledge_available_at is not None
    assert stored.knowledge_available_at.tzinfo is not None
    assert read_certification_run(con, run.run_id) == stored
    assert certification_run_ids(con) == (run.run_id,)


def test_absent_table_and_exact_id_are_honest():
    con = duckdb.connect(":memory:")
    assert read_certification_run(con, "missing") is None
    assert certification_run_ids(con) == ()


def test_mutating_same_id_payload_refuses_collision():
    con = _db()
    discovery = run_recurrent_discovery(con, as_of=date(2026, 1, 31), taxonomy_version="t", legality_version="l",
                                        calibration=_discovery_calibration())
    run = run_recurrent_certification(
        con, discovery_run_id=discovery.run_id,
        calibration=load_certification_calibration(CERTIFICATION_CALIBRATION_PATH),
        semantic_facts=(), format_observation_sha256=None,
    )
    write_certification_run(con, run)
    with pytest.raises(ValueError, match="manifest digest"):
        write_certification_run(con, run.model_copy(update={"manifest": run.manifest.model_copy(update={"seed": 4})}))


def test_direct_status_or_reason_tampering_is_hash_bound():
    con = _db()
    discovery = run_recurrent_discovery(con, as_of=date(2026, 1, 31), taxonomy_version="t", legality_version="l",
                                        calibration=_discovery_calibration())
    run = run_recurrent_certification(
        con, discovery_run_id=discovery.run_id,
        calibration=load_certification_calibration(CERTIFICATION_CALIBRATION_PATH),
        semantic_facts=(), format_observation_sha256=None,
    )
    write_certification_run(con, run)
    con.execute("UPDATE era_certification_runs SET status = 'complete' WHERE run_id = ?", [run.run_id])
    with pytest.raises(ValueError, match="hash mismatch"):
        read_certification_run(con, run.run_id)


def test_post_cutoff_semantic_fact_cannot_change_run_identity():
    con = _db()
    discovery = run_recurrent_discovery(con, as_of=date(2026, 1, 31), taxonomy_version="t", legality_version="l",
                                        calibration=_discovery_calibration())
    calibration = load_certification_calibration(CERTIFICATION_CALIBRATION_PATH)
    baseline = run_recurrent_certification(con, discovery_run_id=discovery.run_id, calibration=calibration,
                                           semantic_facts=(), format_observation_sha256=None)
    future = SemanticFact(fact_id="future", kind="taxonomy", state="confirmed", effective_on=date(2026, 2, 1),
                          affected_entities=("X",), source="frozen-contract", evidence_sha256="7" * 64, detail="future")
    with_future = run_recurrent_certification(con, discovery_run_id=discovery.run_id, calibration=calibration,
                                              semantic_facts=(future,), format_observation_sha256=None)
    assert with_future.run_id == baseline.run_id
    assert with_future.results_sha256 == baseline.results_sha256


def test_checked_in_control_manifest_is_schema_valid_and_digest_bound():
    calibration = load_certification_calibration(CERTIFICATION_CALIBRATION_PATH)
    controls_path = CERTIFICATION_CALIBRATION_PATH.with_name("certification-controls-v1.json")
    manifest = json.loads(controls_path.read_text())
    assert manifest["schema"] == "recurrent-certification-controls-v1"
    assert manifest["outcome_free"] is True
    assert {control["expected"] for control in manifest["controls"]} == {"certified", "rejected", "inconclusive"}
    assert all(control["id"] and control["channels"] is not None for control in manifest["controls"])
    assert calibration.control_evidence_sha256

from datetime import date

import duckdb
import pytest

from legacy_engine.analytics.eras.certification import load_certification_calibration
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
    assert read_certification_run(con, run.run_id) == run
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

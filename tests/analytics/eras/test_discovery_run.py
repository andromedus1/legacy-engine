from datetime import date, timedelta

import duckdb

from legacy_engine.analytics.eras.discovery import DiscoveryCalibration
from legacy_engine.analytics.eras.discovery_run import (
    DISCOVERY_FEATURE_ALLOWLIST,
    run_recurrent_discovery,
)
from legacy_engine.analytics.eras.discovery_store import (
    discovery_run_ids,
    read_discovery_run,
)


def _calibration():
    return DiscoveryCalibration.model_validate({
        "calibration_id": "ledger-test-v1",
        "method_id": "segment-fingerprint-complete-link-v2",
        "bucket_days": 7,
        "min_segment_buckets": 3,
        "min_segment_decks": 3,
        "min_segment_events": 1,
        "min_subject_decks": 3,
        "pelt_penalty": 0.5,
        "smoothing_alpha": 0.5,
        "weights": {"main": 0.4, "side": 0.25, "field": 0.2, "source": 0.1, "subject_share": 0.05},
        "thresholds": {"main_js_max": 0.12, "side_js_max": 0.18, "mixture_energy_max": 0.2, "field_js_max": 0.25, "source_js_max": 0.25},
    })


def _db(n_weeks: int = 4):
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE tournaments (id VARCHAR, date DATE, source VARCHAR, provenance VARCHAR)")
    con.execute("CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, archetype VARCHAR)")
    con.execute("CREATE TABLE deck_cards (tournament_id VARCHAR, deck_idx INTEGER, board VARCHAR, name VARCHAR, count INTEGER)")
    con.execute("CREATE TABLE rounds (tournament_id VARCHAR, result VARCHAR)")
    con.execute("CREATE TABLE standings (tournament_id VARCHAR, wins INTEGER)")
    rows = []
    decks = []
    cards = []
    for week in range(n_weeks):
        when = date(2026, 1, 5) + timedelta(days=7 * week)
        for idx in range(3):
            event = f"e-{week}-{idx}"
            rows.append((event, when, "mtgo", "online"))
            decks.append((event, 0, f"Pilot {week}-{idx}", "X"))
            cards.append((event, 0, "main", "A", 4))
    if rows:
        con.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?)", rows)
        con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?)", decks)
        con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", cards)
    return con


def test_run_round_trips_and_retries_are_idempotent():
    con = _db()
    run = run_recurrent_discovery(
        con, as_of=date(2026, 1, 31), taxonomy_version="tax-v1", legality_version="leg-v1",
        calibration=_calibration(), seed=5,
    )
    again = run_recurrent_discovery(
        con, as_of=date(2026, 1, 31), taxonomy_version="tax-v1", legality_version="leg-v1",
        calibration=_calibration(), seed=5,
    )
    assert run == again
    assert tuple(DISCOVERY_FEATURE_ALLOWLIST) == tuple(sorted(DISCOVERY_FEATURE_ALLOWLIST))
    assert discovery_run_ids(con, as_of=date(2026, 1, 31)) == (run.run_id,)
    assert read_discovery_run(con, run.run_id) == run


def test_cutoffs_coexist_and_missing_run_is_honest():
    con = _db()
    cal = _calibration()
    earlier = run_recurrent_discovery(con, as_of=date(2026, 1, 17), taxonomy_version="t", legality_version="l", calibration=cal)
    later = run_recurrent_discovery(con, as_of=date(2026, 1, 31), taxonomy_version="t", legality_version="l", calibration=cal)
    assert earlier.run_id != later.run_id
    assert set(discovery_run_ids(con)) == {earlier.run_id, later.run_id}
    assert read_discovery_run(con, "missing") is None


def test_degraded_empty_fleet_is_persisted():
    con = _db(0)
    run = run_recurrent_discovery(
        con, as_of=date(2026, 1, 31), taxonomy_version="t", legality_version="l", calibration=_calibration()
    )
    assert run.status == "degraded"
    assert run.reasons == ("no-eligible-parent-archetypes",)
    assert read_discovery_run(con, run.run_id) == run

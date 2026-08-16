from datetime import date

import duckdb
import pytest

from legacy_engine.analytics.eras.certification import (
    EventPartitionPlan,
    load_certification_calibration,
    partition_outcome_free_corpus,
    partition_role,
)
from legacy_engine.analytics.eras.discovery import (
    DiscoveryCard,
    DiscoveryDeck,
    OutcomeFreeCorpus,
)
from legacy_engine.analytics.eras.discovery_run import run_recurrent_discovery
from legacy_engine.analytics.eras.certification_source import load_certification_corpus
from legacy_engine.config import CERTIFICATION_CALIBRATION_PATH


def _deck(event_id: str, idx: int = 0) -> DiscoveryDeck:
    return DiscoveryDeck(
        event_id=event_id,
        event_date=date(2026, 1, 1),
        deck_idx=idx,
        pilot_key=f"{event_id}:pilot-{idx}",
        parent_archetype="X",
        source="mtgo",
        provenance="online",
        mainboard=(DiscoveryCard(name="A", copies=4),),
        sideboard=(),
    )


def _corpus(*events: str) -> OutcomeFreeCorpus:
    return OutcomeFreeCorpus(
        as_of=date(2026, 1, 31),
        taxonomy_version="taxonomy-v1",
        legality_version="legality-v1",
        provenance_filter=None,
        semantic_boundaries=(),
        decks=tuple(_deck(event, idx) for event in events for idx in range(2)),
        source_sha256="0" * 64,
    )


def test_partition_is_atomic_disjoint_exhaustive_and_order_invariant():
    plan = EventPartitionPlan(plan_id="test-plan", salt="test-salt", modulus=3, discovery_buckets=(0,))
    first = partition_outcome_free_corpus(_corpus("e0", "e1", "e2", "e3"), plan)
    second = partition_outcome_free_corpus(_corpus("e3", "e2", "e1", "e0"), plan)
    assert first == second
    discovery = {deck.event_id for deck in first.discovery.decks}
    certification = {deck.event_id for deck in first.certification.decks}
    assert discovery.isdisjoint(certification)
    assert discovery | certification == {"e0", "e1", "e2", "e3"}
    for event_id in discovery | certification:
        expected = "discovery" if event_id in discovery else "certification"
        assert partition_role(event_id, plan) == expected
        roles = {
            "discovery" if deck.event_id in discovery else "certification"
            for deck in (*first.discovery.decks, *first.certification.decks)
            if deck.event_id == event_id
        }
        assert roles == {expected}


def test_empty_partition_roles_have_stable_digests():
    plan = EventPartitionPlan(plan_id="test-plan", salt="test-salt", modulus=2, discovery_buckets=(0,))
    result = partition_outcome_free_corpus(_corpus("e1"), plan)
    assert result.manifest.discovery_events + result.manifest.certification_events == 1
    assert len(result.manifest.discovery_event_ids_sha256) == 64
    assert len(result.manifest.certification_event_ids_sha256) == 64


def test_outcome_tables_are_not_required_by_partition_core():
    con = duckdb.connect(":memory:")
    # This test is intentionally structural: partitioning receives an
    # already-projected corpus and therefore has no path to outcome tables.
    con.execute("CREATE TABLE standings (event_id VARCHAR, wins INTEGER)")
    result = partition_outcome_free_corpus(_corpus("e1", "e2"), EventPartitionPlan(
        plan_id="test-plan", salt="test-salt", modulus=2, discovery_buckets=(0,)
    ))
    assert result.discovery.source_sha256 != result.certification.source_sha256


def test_partition_plan_rejects_all_or_empty_discovery_buckets():
    with pytest.raises(ValueError):
        EventPartitionPlan(plan_id="p", salt="s", modulus=2, discovery_buckets=())
    with pytest.raises(ValueError):
        EventPartitionPlan(plan_id="p", salt="s", modulus=2, discovery_buckets=(0, 1))


def test_certification_source_rebuilds_only_exact_held_out_role():
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE tournaments (id VARCHAR, date DATE, source VARCHAR, provenance VARCHAR)")
    con.execute("CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, archetype VARCHAR)")
    con.execute("CREATE TABLE deck_cards (tournament_id VARCHAR, deck_idx INTEGER, board VARCHAR, name VARCHAR, count INTEGER)")
    con.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?)", [
        (f"e{i}", date(2026, 1, 5 + i), "mtgo", "online") for i in range(6)
    ])
    con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?)", [
        (f"e{i}", 0, f"pilot-{i}", "X") for i in range(6)
    ])
    con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [
        (f"e{i}", 0, "main", "A", 4) for i in range(6)
    ])
    from legacy_engine.analytics.eras.discovery import DiscoveryCalibration
    discovery_calibration = DiscoveryCalibration.model_validate({
        "calibration_id": "test-v2", "method_id": "segment-fingerprint-complete-link-v2",
        "bucket_days": 7, "min_segment_buckets": 1, "min_segment_decks": 1,
        "min_segment_events": 1, "min_subject_decks": 1, "pelt_penalty": 0.5,
        "smoothing_alpha": 0.5,
        "weights": {"main": 0.4, "side": 0.25, "field": 0.2, "source": 0.1, "subject_share": 0.05},
        "thresholds": {"main_js_max": 0.12, "side_js_max": 0.18, "mixture_energy_max": 0.2, "field_js_max": 0.25, "source_js_max": 0.25},
    })
    run = run_recurrent_discovery(con, as_of=date(2026, 1, 31), taxonomy_version="t", legality_version="l",
                                  calibration=discovery_calibration)
    corpus, manifest = load_certification_corpus(
        con, discovery_run=run,
        calibration=load_certification_calibration(CERTIFICATION_CALIBRATION_PATH),
        as_of=date(2026, 1, 31), taxonomy_version="t", legality_version="l",
    )
    assert manifest.plan_id == run.manifest.partition_plan_id
    assert {deck.event_id for deck in corpus.decks}.isdisjoint(
        set(run.results[0].segments[0].event_ids)
        if run.results and run.results[0].segments else set()
    )

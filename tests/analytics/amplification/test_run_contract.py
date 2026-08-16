from __future__ import annotations

import json

import duckdb
import pytest
from pydantic import ValidationError

from legacy_engine.analytics.amplification import (
    AMPLIFICATION_METHOD_IDS,
    pair_from_key,
    read_amplification_run,
    validate_amplification_run,
    write_amplification_run,
)
from legacy_engine.models.matchup import MatchupCell


def test_real_interval_run_has_exact_typed_common_universe(
    amplification_run, interval_matrix
):
    run = amplification_run
    assert run.status == "complete"
    assert run.corpus.corpus_id == interval_matrix.selected_outcomes.content_sha256
    assert run.corpus.clock == interval_matrix.clock
    assert run.corpus.certificate_run_id == interval_matrix.certificate_run_id
    assert (
        tuple(candidate.method_id for candidate in run.candidates)
        == AMPLIFICATION_METHOD_IDS
    )
    assert len({tuple(candidate.all_case_pairs) for candidate in run.candidates}) == 1
    assert set(run.baselines) == set(run.candidates[0].all_case_pairs)
    assert all(pair_from_key(key) in interval_matrix.evidence for key in run.baselines)
    assert all(
        isinstance(value.current_only.cell, MatchupCell)
        for value in run.baselines.values()
    )
    assert all(
        candidate.fit_id
        and all(p.fit_id == candidate.fit_id for p in candidate.predictions)
        for candidate in run.candidates
    )
    validate_amplification_run(run)
    assert run.comparison.fair
    assert run.comparison.common_corpus_id == run.corpus.corpus_id
    assert set(run.comparison.per_method_input_sha256) == set(AMPLIFICATION_METHOD_IDS)
    assert not hasattr(run, "winner")
    assert not hasattr(run, "promotion")


def test_exact_id_store_round_trip_retains_predictions_and_typed_cells(
    amplification_run,
):
    con = duckdb.connect(":memory:")
    write_amplification_run(con, amplification_run)
    restored = read_amplification_run(con, amplification_run.run_id)
    assert restored == amplification_run
    assert sum(len(candidate.predictions) for candidate in restored.candidates) == 36
    assert isinstance(
        next(iter(restored.baselines.values())).current_only.cell, MatchupCell
    )
    assert read_amplification_run(con, "missing") is None


def test_store_rejects_nested_draw_and_run_tampering(amplification_run):
    con = duckdb.connect(":memory:")
    write_amplification_run(con, amplification_run)
    payload = json.loads(
        con.execute("SELECT payload FROM amplification_runs").fetchone()[0]
    )
    payload["aligned_draws"]["series"][0]["probabilities"][0] = 0.123456
    con.execute("UPDATE amplification_runs SET payload=?", [json.dumps(payload)])
    try:
        read_amplification_run(con, amplification_run.run_id)
    except ValueError as exc:
        assert "draw" in str(exc) or "run" in str(exc)
    else:
        raise AssertionError("tampered aligned draw was accepted")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["comparison"].update({"audit_id": "0" * 64}),
        lambda payload: payload["corpus"]["outcomes"][0].update(
            {"subject_won": not payload["corpus"]["outcomes"][0]["subject_won"]}
        ),
        lambda payload: next(iter(payload["baselines"].values()))[
            "current_only"
        ].update({"match_ids": ["injected"]}),
        lambda payload: payload["aligned_draws"]["replay_plan"].update(
            {"seed": payload["aligned_draws"]["seed"] + 1}
        ),
    ],
)
def test_store_recomputes_nested_content_identities(amplification_run, mutate):
    con = duckdb.connect(":memory:")
    write_amplification_run(con, amplification_run)
    payload = json.loads(
        con.execute("SELECT payload FROM amplification_runs").fetchone()[0]
    )
    mutate(payload)
    con.execute("UPDATE amplification_runs SET payload=?", [json.dumps(payload)])
    with pytest.raises(ValueError):
        read_amplification_run(con, amplification_run.run_id)


def test_authority_and_unknown_method_are_closed(amplification_run):
    payload = amplification_run.model_dump(mode="json")
    payload["authority"] = "ranking-authoritative"
    with pytest.raises(ValidationError):
        type(amplification_run).model_validate(payload)
    payload = amplification_run.model_dump(mode="json")
    payload["candidates"][0]["method_id"] = "winner-v1"
    with pytest.raises(ValidationError):
        type(amplification_run).model_validate(payload)

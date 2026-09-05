"""Focused contracts for the current-field performance/floor projection."""

from __future__ import annotations

import pytest

from legacy_engine.advisory.deck_ranking import rank_matchup_rows
from legacy_engine.advisory.ranking_measurement import (
    RankingCellMeasurement,
    RankingCellSource,
)
from legacy_engine.analytics.matchup import build_cell


def _source(subject: str, opponent: str, wins: int, n: int, **kwargs) -> RankingCellSource:
    return RankingCellSource(
        kind=kwargs.pop("kind", "era"),
        since=None,
        cell=build_cell(subject, opponent, wins, n, **kwargs),
    )


def _measurement(
    subject: str,
    opponent: str,
    share: float,
    *,
    era: RankingCellSource | None = None,
    fallback: RankingCellSource | None = None,
) -> RankingCellMeasurement:
    return RankingCellMeasurement(
        subject=subject,
        opponent=opponent,
        field_share=share,
        era=era,
        fallback=fallback,
        selected_kind=era.kind if era is not None else fallback.kind if fallback is not None else None,
        selected=era if era is not None else fallback,
        selection_reason="test",
        measured=bool((era or fallback) and (era or fallback).cell.n > 0),
        concentration_warning=None,
    )


def test_uses_cell_prior_and_actual_strength_for_hand_computable_mean():
    cell = _source("A", "B", 1, 3, prior_mean=0.8, prior_strength=20.0)
    result = rank_matchup_rows(
        {"A": [_measurement("A", "B", 0.6, era=cell)]},
        {"A": 0.4, "B": 0.6},
        draws=300,
        seed=19,
    )
    record = result["rows"]["A"]["cells"][1]
    assert record["mean"] == pytest.approx((16.0 + 1.0) / (20.0 + 3.0))
    assert record["mean"] == pytest.approx(cell.cell.p_shrunk)
    assert record["prior_mean"] == pytest.approx(0.8)
    assert record["prior_strength"] == pytest.approx(20.0)


def test_era_is_preferred_even_when_thin_and_no_n7_to_n8_gate_cliff():
    era7 = _source("A", "B", 0, 7)
    fallback = _source("A", "B", 90, 100, kind="ban-fallback")
    first = rank_matchup_rows(
        {"A": [_measurement("A", "B", 1.0, era=era7, fallback=fallback)]},
        {"B": 1.0},
        draws=100,
        seed=23,
    )
    era8 = _source("A", "B", 0, 8)
    second = rank_matchup_rows(
        {"A": [_measurement("A", "B", 1.0, era=era8, fallback=fallback)]},
        {"B": 1.0},
        draws=100,
        seed=23,
    )
    # Both estimates use the thin era record, rather than silently switching to
    # the much thicker fallback at a support threshold.
    assert first["rows"]["A"]["cells"][0]["source_kind"] == "era"
    assert first["rows"]["A"]["cells"][0]["n"] == 7
    assert second["rows"]["A"]["cells"][0]["n"] == 8
    assert first["rows"]["A"]["performance"] != second["rows"]["A"]["performance"]
    assert first["rows"]["A"]["nonmirror_coverage"] == pytest.approx(1.0)
    assert second["rows"]["A"]["nonmirror_coverage"] == pytest.approx(1.0)


def test_missing_field_is_weak_prior_mirror_is_performance_only_and_parent_is_not_mirror():
    result = rank_matchup_rows(
        {
            "Camp": [
                _measurement("Camp", "Parent", 0.5, era=_source("Camp", "Parent", 0, 1)),
            ],
        },
        {"Camp": 0.2, "Parent": 0.5, "Other": 0.3},
        draws=500,
        seed=29,
    )
    row = result["rows"]["Camp"]
    cells = {cell["opponent"]: cell for cell in row["cells"]}
    assert set(cells) == {"Camp", "Other", "Parent"}
    assert cells["Other"]["source_kind"] == "missing"
    assert cells["Other"]["prior_mean"] == pytest.approx(0.5)
    assert cells["Other"]["prior_strength"] == pytest.approx(2.0)
    assert cells["Camp"]["is_mirror"] is True
    assert cells["Camp"]["mean"] == pytest.approx(0.5)
    assert cells["Parent"]["is_mirror"] is False
    assert row["worst_opponent"] in {"Other", "Parent"}
    assert row["nonmirror_coverage"] == pytest.approx(0.5 / 0.8)
    # The structural mirror is part of the full-field performance calculation.
    expected = 0.2 * 0.5 + 0.5 * cells["Parent"]["mean"] + 0.3 * cells["Other"]["mean"]
    assert row["performance"] == pytest.approx(expected)


def test_performance_and_floor_are_separate_objectives_and_frontier_is_deterministic():
    rows = {
        "Steady": [
            _measurement("Steady", "Wide", 0.7, era=_source("Steady", "Wide", 7, 10)),
            _measurement("Steady", "Narrow", 0.3, era=_source("Steady", "Narrow", 6, 10)),
        ],
        "Spike": [
            _measurement("Spike", "Wide", 0.7, era=_source("Spike", "Wide", 10, 10)),
            _measurement("Spike", "Narrow", 0.3, era=_source("Spike", "Narrow", 0, 10)),
        ],
    }
    shares = {"Wide": 0.7, "Narrow": 0.3, "Steady": 0.1, "Spike": 0.1}
    first = rank_matchup_rows(rows, shares, counts=shares, draws=1_000, seed=31)
    second = rank_matchup_rows(rows, shares, counts=shares, draws=1_000, seed=31)
    assert first == second
    assert first["rows"]["Spike"]["performance"] > first["rows"]["Steady"]["performance"]
    assert first["rows"]["Spike"]["floor"] < first["rows"]["Steady"]["floor"]
    assert first["rows"]["Spike"]["worst_opponent"] == "Narrow"
    assert first["rows"]["Spike"]["eligible"] is True


def test_prior_only_rows_are_serialized_but_not_recommended():
    result = rank_matchup_rows({"Absent": []}, {"Absent": 1.0}, draws=30, seed=37)
    row = result["rows"]["Absent"]
    assert row["cells"]
    assert row["direct_support"] is False
    assert row["eligible"] is False
    assert result["efficient_frontier"] == []


def test_ineligible_prior_only_peer_does_not_dominate_eligible_frontier():
    result = rank_matchup_rows(
        {
            "Supported": [
                _measurement("Supported", "Opponent", 0.9, era=_source("Supported", "Opponent", 0, 100)),
            ],
            "Retired": [],
        },
        {"Supported": 0.1, "Opponent": 0.8, "Retired": 0.1},
        draws=200,
        seed=41,
    )
    assert result["rows"]["Retired"]["eligible"] is False
    assert result["rows"]["Retired"]["pareto"] is False
    assert result["rows"]["Supported"]["pareto"] is True
    assert result["efficient_frontier"] == ["Supported"]


@pytest.mark.parametrize(
    ("rows", "shares", "kwargs", "message"),
    [
        ({"A": []}, {}, {}, "positive total"),
        ({"A": []}, {"B": -1.0}, {}, "non-negative"),
        ({"A": []}, {"B": 1.0}, {"draws": 0}, "draws"),
        ({"A": []}, {"B": 1.0}, {"counts": {"C": 1.0}}, "exactly"),
    ],
)
def test_invalid_inputs_fail_loudly(rows, shares, kwargs, message):
    with pytest.raises(ValueError, match=message):
        rank_matchup_rows(rows, shares, **kwargs)

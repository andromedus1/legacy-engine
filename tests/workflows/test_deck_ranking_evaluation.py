"""Pure scoring contracts for the served-model historical ranking evaluator."""

from __future__ import annotations

import pytest

from legacy_engine.advisory.ranking_benchmark import content_sha256
from legacy_engine.workflows.deck_ranking_evaluation import (
    _phase_summary,
    _seal_development_selection,
    _write_digested,
    evaluate_ranking_origin,
)


def _cell(subject: str, opponent: str, probability: float, support_n: int = 8) -> dict:
    return {
        "subject": subject, "opponent": opponent,
        "probability": probability, "support_n": support_n,
    }


def _artifact(*, floor_pairings: list[dict] | None = None) -> dict:
    payload = {
        "metadata": {
            "protocol_id": "deck-ranking-evaluation-v1",
            "taxonomy_mode": "retrospective-fixed-parent",
            "fold": {
                "fold_id": "2026-01-01--2026-01-08",
                "cutoff": "2026-01-01", "evaluation_until": "2026-01-08",
                "regime_start": "2025-11-10", "regime_end": None, "event_dates": [],
            },
        },
        "forecasts": {
            "1": {
                "prior_scale": 1.0,
                "cells": [_cell("A", "B", 0.8), _cell("B", "A", 0.2)],
                "floor_pairings": floor_pairings or [],
            },
            "0.5": {
                "prior_scale": 0.5,
                "cells": [_cell("A", "B", 0.6), _cell("B", "A", 0.4)],
                "floor_pairings": [],
            },
        },
    }
    payload["artifact_sha256"] = content_sha256(payload)
    return payload


def _match(
    *, won: bool = True, event: str = "event-1", a: str = "A", b: str = "B",
    match_idx: int | None = None,
) -> dict:
    return {
        "event_id": event, "subject": a, "opponent": b,
        "match_idx": match_idx,
        "subject_player_key": f"{event}-a", "opponent_player_key": f"{event}-b",
        "subject_won": won, "exclusion_reason": None,
    }


def test_scores_two_directions_with_half_weight_and_event_pairing() -> None:
    result = evaluate_ranking_origin(_artifact(), [_match()])
    baseline = result["methods"]["1"]
    assert result["total_support_matches"] == 1
    assert baseline["scored_matches"] == 1
    assert baseline["common_case_matches"] == 1
    assert baseline["calibration"]["predictions"] == 2
    assert baseline["calibration"]["weighted_predictions"] == pytest.approx(1.0)
    assert baseline["reciprocity"]["mean_absolute_discrepancy"] == pytest.approx(0.0)
    assert result["methods"]["0.5"]["paired_event_log_loss_difference_vs_scale_1"]["event-1"] > 0


def test_duplicate_reverse_rows_are_one_physical_match_and_unknown_labels_are_missing() -> None:
    artifact = _artifact(floor_pairings=[{
        "subject": "A", "opponent": "C", "support_n": 0, "available": True,
    }])
    first = _match()
    reverse_duplicate = {
        **first, "subject": "B", "opponent": "A",
        "subject_player_key": first["opponent_player_key"],
        "opponent_player_key": first["subject_player_key"],
        "subject_won": False,
    }
    unknown = _match(event="event-2", a="Unknown", b="A")
    result = evaluate_ranking_origin(artifact, [first, reverse_duplicate, unknown])
    baseline = result["methods"]["1"]
    assert result["total_support_matches"] == 2
    assert baseline["scored_matches"] == 1
    assert baseline["common_case_matches"] == 1
    assert baseline["missing_forecast_directions"] == 2
    floor = result["floor_evidence"][0]
    assert floor["available"] is False
    assert floor["matches"] == 0


def test_match_idx_preserves_same_player_rematches_and_deduplicates_reverse_rows() -> None:
    first = _match(match_idx=1)
    first_reverse = {
        **first, "subject": "B", "opponent": "A",
        "subject_player_key": first["opponent_player_key"],
        "opponent_player_key": first["subject_player_key"],
        "subject_won": False,
    }
    rematch = _match(match_idx=2, won=False)
    result = evaluate_ranking_origin(_artifact(), [first, first_reverse, rematch])
    baseline = result["methods"]["1"]
    assert result["total_support_matches"] == 2
    assert baseline["scored_matches"] == 2
    assert baseline["common_case_matches"] == 2


def test_tampered_frozen_artifact_fails_closed() -> None:
    artifact = _artifact()
    artifact["forecasts"]["1"]["cells"][0]["probability"] = 0.99
    with pytest.raises(ValueError, match="artifact digest"):
        evaluate_ranking_origin(artifact, [_match()])


def test_frozen_artifact_requires_digest() -> None:
    artifact = _artifact()
    artifact.pop("artifact_sha256")
    with pytest.raises(ValueError, match="missing artifact digest"):
        evaluate_ranking_origin(artifact, [_match()])


def test_frozen_artifact_rejects_duplicate_forecast_cells() -> None:
    artifact = _artifact()
    artifact["forecasts"]["1"]["cells"].append(_cell("A", "B", 0.8))
    artifact["artifact_sha256"] = content_sha256({
        key: value for key, value in artifact.items() if key != "artifact_sha256"
    })
    with pytest.raises(ValueError, match="duplicate forecast cells"):
        evaluate_ranking_origin(artifact, [_match()])


def test_named_floor_followup_is_reported_for_each_method() -> None:
    artifact = _artifact(floor_pairings=[{
        "subject": "A", "opponent": "C", "support_n": 0, "available": True,
    }])
    artifact["forecasts"]["0.5"]["floor_pairings"] = artifact["forecasts"]["1"]["floor_pairings"]
    artifact["artifact_sha256"] = content_sha256({
        key: value for key, value in artifact.items() if key != "artifact_sha256"
    })
    result = evaluate_ranking_origin(artifact, [_match()])
    assert {item["method"] for item in result["floor_evidence"]} == {"0.5", "1"}


def test_phase_summary_exposes_weighted_scores_and_independent_order_sensitivity() -> None:
    result = evaluate_ranking_origin(_artifact(), [_match()])
    summary = _phase_summary(
        [result], phase="development", selected_method=None,
        origins_declared=(("2026-01-01", "2026-01-08", "2025-12-01"),),
        scales=(1.0, 0.5, 2.0), draws=64,
    )
    assert summary["status"] == "tentative"
    assert summary["methods"]["1"]["match_weighted"]["weight"] == pytest.approx(1.0)
    assert summary["methods"]["0.5"]["performance_order_sensitivity"]["by_origin"]
    assert summary["methods"]["1"]["named_floor_followup"] == []


def test_development_selection_is_sealed_and_cannot_change(tmp_path) -> None:
    result = evaluate_ranking_origin(_artifact(), [_match()])
    development = _phase_summary(
        [result], phase="development", selected_method=None,
        origins_declared=(("2026-01-01", "2026-01-08", "2025-12-01"),),
        scales=(1.0, 0.5, 2.0), draws=64,
    )
    development = _write_digested(tmp_path / "development-summary.json", development)
    selection = _seal_development_selection(
        tmp_path, development, selected_method="0.5", scales=(1.0, 0.5, 2.0),
    )
    assert selection["selected_method"] == "0.5"
    with pytest.raises(ValueError, match="already sealed"):
        _seal_development_selection(
            tmp_path, development, selected_method="1", scales=(1.0, 0.5, 2.0),
        )


def test_excluded_and_mirror_rows_do_not_become_zero_loss() -> None:
    excluded = _match()
    excluded["exclusion_reason"] = "unclassified"
    mirror = _match(a="A", b="A")
    result = evaluate_ranking_origin(_artifact(), [excluded, mirror])
    assert result["total_support_matches"] == 0
    assert result["methods"]["1"]["log_loss"] is None

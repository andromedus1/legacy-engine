from __future__ import annotations

import math

import pytest

from legacy_engine.advisory.ranking_benchmark import content_sha256
from legacy_engine.advisory.recurrent_validation import (
    build_future_case_manifest,
    evaluate_recurrent_predictions,
)
from .recurrent_validation_helpers import future_rows, origin, protocol


def test_mapping_rows_canonicalize_without_dict_comparison_and_scores_are_exact():
    value = protocol(small=True)
    frozen = origin(
        value,
        probability=lambda _estimator, subject, _opponent: 0.75 if subject == "a" else 0.25,
    )
    cases = build_future_case_manifest(
        frozen,
        future_rows(value),
        protocol=value,
        future_field_counts={"a": 1, "b": 1},
    )
    assert cases.eligible_match_ids == ("m1", "m2")
    evaluation = evaluate_recurrent_predictions(frozen, cases, protocol=value)
    current = next(item for item in evaluation.metrics if item.estimator_id == "current-only-v1")
    assert current.log_loss == pytest.approx(-math.log(0.75))
    assert current.brier == pytest.approx(0.25**2)
    assert current.cumulative_calibration_error == pytest.approx(0.25)
    assert current.interval_coverage is not None
    assert current.interval_score is not None
    assert current.status == "support-censored"
    assert "calibration-support-insufficient" in current.reasons


def test_outcome_swap_changes_scores_not_origin_membership_service_or_draws():
    value = protocol(small=True)
    frozen = origin(value)
    first_rows = future_rows(value)
    second_rows = [dict(row) for row in first_rows]
    second_rows[0]["subject_won"] = False
    first_cases = build_future_case_manifest(
        frozen, first_rows, protocol=value, future_field_counts={"a": 1, "b": 1}
    )
    second_cases = build_future_case_manifest(
        frozen, second_rows, protocol=value, future_field_counts={"a": 1, "b": 1}
    )
    first = evaluate_recurrent_predictions(frozen, first_cases, protocol=value)
    second = evaluate_recurrent_predictions(frozen, second_cases, protocol=value)
    assert first_cases.eligible_match_ids == second_cases.eligible_match_ids
    assert first_cases.eligible_event_ids == second_cases.eligible_event_ids
    assert frozen.predictions_sha256 == first.origin_predictions_sha256
    assert frozen.predictions_sha256 == second.origin_predictions_sha256
    first_metric = next(item for item in first.metrics if item.estimator_id == "current-only-v1")
    second_metric = next(item for item in second.metrics if item.estimator_id == "current-only-v1")
    assert first_metric.log_loss != second_metric.log_loss
    assert first_metric.served_match_coverage == second_metric.served_match_coverage
    assert frozen.joint_draws.draws_sha256


def test_missing_candidate_probability_invalidates_fit_without_deleting_cases():
    value = protocol(small=True)
    frozen = origin(value)
    changed = tuple(
        prediction.model_copy(update={"probability": None})
        if prediction.estimator_id == "recurrent-expanded-v1" and prediction.subject == "a"
        else prediction
        for prediction in frozen.predictions
    )
    frozen = frozen.model_copy(update={
        "predictions": changed,
        "predictions_sha256": content_sha256(
            [prediction.model_dump(mode="json") for prediction in changed]
        ),
    })
    cases = build_future_case_manifest(
        frozen, future_rows(value), protocol=value, future_field_counts={"a": 1, "b": 1}
    )
    evaluation = evaluate_recurrent_predictions(frozen, cases, protocol=value)
    candidate = next(
        item for item in evaluation.metrics if item.estimator_id == "recurrent-expanded-v1"
    )
    assert cases.eligible_match_ids == ("m1", "m2")
    assert candidate.status == "invalid"
    assert candidate.common_matches == 0
    assert "missing-all-case-prediction" in candidate.reasons
    assert evaluation.status == "invalid"


def test_protocol_fold_horizon_case_and_action_identity_are_required():
    value = protocol(small=True)
    frozen = origin(value)
    cases = build_future_case_manifest(
        frozen, future_rows(value), protocol=value, future_field_counts={"a": 1, "b": 1}
    )
    with pytest.raises(ValueError, match="horizon differs"):
        evaluate_recurrent_predictions(
            frozen,
            cases.model_copy(update={"evaluation_until": "2026-09-13"}),
            protocol=value,
        )
    with pytest.raises(ValueError, match="case manifest digest"):
        evaluate_recurrent_predictions(
            frozen,
            cases.model_copy(update={"case_sha256": "1" * 64}),
            protocol=value,
        )
    with pytest.raises(ValueError, match="action universe"):
        evaluate_recurrent_predictions(
            frozen,
            cases.model_copy(update={"action_universe_sha256": "1" * 64}),
            protocol=value,
        )
    with pytest.raises(ValueError, match="eligible event ids"):
        evaluate_recurrent_predictions(
            frozen,
            cases.model_copy(update={"eligible_event_ids": ("invented-support",)}),
            protocol=value,
        )
    with pytest.raises(ValueError, match="field shares"):
        evaluate_recurrent_predictions(
            frozen,
            cases.model_copy(update={"future_field_shares": {"a": 1.0, "b": 0.0}}),
            protocol=value,
        )


def test_exclusions_are_global_and_future_field_denominator_is_not_renormalized():
    value = protocol(small=True)
    frozen = origin(value)
    rows = future_rows(value) + [
        {
            "match_id": "novel",
            "event_id": "e3",
            "event_date": value.folds[0].data_until,
            "subject": "novel-archetype",
            "opponent": "a",
            "subject_won": True,
        },
        {
            "match_id": "draw",
            "event_id": "e3",
            "event_date": value.folds[0].data_until,
            "subject": "a",
            "opponent": "b",
            "subject_won": None,
        },
    ]
    cases = build_future_case_manifest(
        frozen,
        rows,
        protocol=value,
        future_field_counts={"a": 1, "b": 1, "novel-archetype": 2},
    )
    assert cases.exclusions == {"bye-draw-invalid": 1, "outside-universe": 1}
    assert cases.eligible_field_mass == pytest.approx(0.5)
    assert cases.total_future_decks == 4


def test_duplicate_match_ids_refuse_even_when_rows_are_identical():
    value = protocol(small=True)
    frozen = origin(value)
    row = future_rows(value)[0]
    with pytest.raises(ValueError, match="duplicated"):
        build_future_case_manifest(
            frozen,
            [row, dict(row)],
            protocol=value,
            future_field_counts={"a": 1, "b": 1},
        )


def test_non_boolean_decisive_outcome_cannot_cross_the_future_case_boundary():
    value = protocol(small=True)
    frozen = origin(value)
    rows = future_rows(value)
    rows[0]["subject_won"] = "false"
    with pytest.raises(ValueError, match="must be a boolean"):
        build_future_case_manifest(
            frozen,
            rows,
            protocol=value,
            future_field_counts={"a": 1, "b": 1},
        )

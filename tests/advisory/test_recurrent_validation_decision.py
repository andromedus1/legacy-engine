from __future__ import annotations

import pytest

from legacy_engine.advisory.recurrent_validation import (
    build_future_case_manifest,
    evaluate_recurrent_decisions,
    evaluate_recurrent_predictions,
)
from .recurrent_validation_helpers import future_rows, origin, protocol


def _cases(value, frozen, rows=None):
    return build_future_case_manifest(
        frozen,
        rows or future_rows(value),
        protocol=value,
        future_field_counts={"a": 1, "b": 1},
    )


def test_refusal_executes_current_only_action_and_pays_its_regret():
    value = protocol(small=True)
    recommendations = {estimator: "b" for estimator in value.estimator_ids}
    recommendations["recurrent-expanded-v1"] = "a"
    frozen = origin(
        value,
        served=lambda estimator, _subject, _opponent: estimator != "recurrent-expanded-v1",
        recommendations=recommendations,
    )
    evaluation = evaluate_recurrent_decisions(
        frozen, _cases(value, frozen), protocol=value
    )
    current = next(item for item in evaluation.evaluations if item.estimator_id == "current-only-v1")
    candidate = next(
        item for item in evaluation.evaluations if item.estimator_id == "recurrent-expanded-v1"
    )
    assert candidate.requested_action == "a"
    assert candidate.frozen_action == "b"
    assert candidate.fallback_used is True
    assert candidate.regret == current.regret
    assert candidate.regret is not None and candidate.regret > 0
    assert "executed current-only action" in candidate.reasons[-1]


def test_input_order_cannot_change_action_or_shared_regret_draws():
    value = protocol(small=True)
    frozen = origin(value)
    rows = future_rows(value)
    forward = evaluate_recurrent_decisions(
        frozen, _cases(value, frozen, rows), protocol=value
    )
    reverse = evaluate_recurrent_decisions(
        frozen, _cases(value, frozen, list(reversed(rows))), protocol=value
    )
    assert forward.model_dump(mode="json") == reverse.model_dump(mode="json")
    assert forward.field_mass_sha256 == forward.field_mass_sha256
    assert forward.action_universe_sha256


def test_duplicate_matches_inside_events_do_not_create_new_event_blocks_or_narrow_bounds():
    value = protocol(small=True)
    recommendations = {estimator: "b" for estimator in value.estimator_ids}
    frozen = origin(value, recommendations=recommendations)
    base_rows = future_rows(value)
    duplicated = base_rows + [
        {**base_rows[0], "match_id": "m3", "subject_deck_id": "d5", "opponent_deck_id": "d6"},
        {**base_rows[1], "match_id": "m4", "subject_deck_id": "d7", "opponent_deck_id": "d8"},
    ]
    base = evaluate_recurrent_decisions(
        frozen, _cases(value, frozen, base_rows), protocol=value
    )
    repeated = evaluate_recurrent_decisions(
        frozen, _cases(value, frozen, duplicated), protocol=value
    )
    left = next(item for item in base.evaluations if item.estimator_id == "current-only-v1")
    right = next(item for item in repeated.evaluations if item.estimator_id == "current-only-v1")
    assert left.event_blocks == right.event_blocks == 2
    assert left.regret_interval == right.regret_interval


def test_practical_tie_missing_action_and_invalid_draws_are_typed_censors():
    value = protocol(small=True)
    frozen = origin(value)
    tied_rows = future_rows(value)
    tied_rows[0]["subject_won"] = False
    tied = evaluate_recurrent_decisions(
        frozen, _cases(value, frozen, tied_rows), protocol=value
    )
    assert all(item.censor_reason == "practical-tie" for item in tied.evaluations)
    assert all(item.regret is None for item in tied.evaluations)

    recommendations = {estimator: None for estimator in value.estimator_ids}
    no_action_origin = origin(value, recommendations=recommendations)
    no_action = evaluate_recurrent_decisions(
        no_action_origin, _cases(value, no_action_origin), protocol=value
    )
    assert all(item.censor_reason == "missing-action" for item in no_action.evaluations)

    bad_draw_origin = frozen.model_copy(
        update={
            "joint_draws": frozen.joint_draws.model_copy(update={"replicate_count": 39})
        }
    )
    invalid = evaluate_recurrent_decisions(
        bad_draw_origin, _cases(value, bad_draw_origin), protocol=value
    )
    assert invalid.status == "invalid"
    assert all(item.censor_reason == "invalid-joint-draws" for item in invalid.evaluations)


def test_better_log_loss_can_still_have_worse_decision_regret():
    value = protocol(small=True)
    recommendations = {estimator: "a" for estimator in value.estimator_ids}
    recommendations["recurrent-expanded-v1"] = "b"
    frozen = origin(
        value,
        probability=lambda estimator, subject, _opponent: (
            0.9 if subject == "a" else 0.1
        ) if estimator == "recurrent-expanded-v1" else (
            0.6 if subject == "a" else 0.4
        ),
        recommendations=recommendations,
    )
    cases = _cases(value, frozen)
    predictive = evaluate_recurrent_predictions(frozen, cases, protocol=value)
    decision = evaluate_recurrent_decisions(frozen, cases, protocol=value)
    metrics = {item.estimator_id: item for item in predictive.metrics}
    decisions = {item.estimator_id: item for item in decision.evaluations}
    assert metrics["recurrent-expanded-v1"].log_loss < metrics["current-only-v1"].log_loss
    assert decisions["recurrent-expanded-v1"].regret > decisions["current-only-v1"].regret


def test_decision_binding_rejects_a_different_case_manifest():
    value = protocol(small=True)
    frozen = origin(value)
    cases = _cases(value, frozen)
    with pytest.raises(ValueError, match="case manifest digest"):
        evaluate_recurrent_decisions(
            frozen,
            cases.model_copy(update={"case_sha256": "1" * 64}),
            protocol=value,
        )

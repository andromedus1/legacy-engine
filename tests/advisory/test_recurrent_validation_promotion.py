from __future__ import annotations

import pytest

from legacy_engine.advisory.ranking_benchmark import content_sha256
from legacy_engine.advisory.recurrent_validation import (
    aggregate_recurrent_validation,
    build_future_case_manifest,
    build_operator_proposal,
    evaluate_recurrent_decisions,
    evaluate_recurrent_predictions,
)
from .recurrent_validation_helpers import future_rows, origin, protocol


def _complete_evidence(value, *, change: tuple[str, tuple[float, ...]] | None = None):
    frozen = origin(value)
    cases = build_future_case_manifest(
        frozen,
        future_rows(value),
        protocol=value,
        future_field_counts={"a": 1, "b": 1},
    )
    predictive = evaluate_recurrent_predictions(frozen, cases, protocol=value)
    decision = evaluate_recurrent_decisions(frozen, cases, protocol=value)
    vectors = {}
    regrets = {}
    for comparator in ("current-only-v1", "contiguous-era-v1"):
        key = f"recurrent-expanded-v1|{comparator}"
        vectors[key] = {
            "served_field_coverage": (0.10, 0.10),
            "served_event_coverage": (0.10, 0.10),
            "log_loss": (-0.01, -0.01),
            "brier": (-0.01, -0.01),
            "calibration": (-0.01, -0.01),
            "interval_coverage": (1.0, 1.0),
            "interval_score": (-0.01, -0.01),
        }
        regrets[key] = {"regret": (-0.01, -0.01)}
        if change is not None:
            metric, values = change
            if metric == "regret":
                regrets[key][metric] = values
            else:
                vectors[key][metric] = values
    predictive = predictive.model_copy(
        update={"paired_event_differences": vectors, "status": "complete", "reasons": ()}
    )
    decision = decision.model_copy(
        update={"paired_regret_differences": regrets, "status": "complete", "reasons": ()}
    )
    return frozen, predictive, decision


def _assess(value, *, change=None, predictive_status="complete"):
    frozen, predictive, decision = _complete_evidence(value, change=change)
    predictive = predictive.model_copy(update={"status": predictive_status})
    return aggregate_recurrent_validation(
        [predictive],
        [decision],
        protocol=value,
        candidate_id="recurrent-expanded-v1",
        candidate_config_sha256=frozen.candidate_config_sha256["recurrent-expanded-v1"],
    )


def test_all_five_statuses_come_from_complete_value_bound_clause_ledgers():
    value = protocol(small=True)
    promotable = _assess(value)
    negative = _assess(value, change=("log_loss", (0.10, 0.10)))
    inconclusive = _assess(value, change=("log_loss", (-0.10, 0.10)))
    censored = _assess(value, predictive_status="support-censored")
    invalid = _assess(value, predictive_status="invalid")
    assert [item.status for item in (promotable, negative, inconclusive, censored, invalid)] == [
        "promotable", "negative", "inconclusive", "support-censored", "invalid"
    ]
    assert all(len(item.clauses) == 16 for item in (
        promotable, negative, inconclusive, censored, invalid
    ))
    assert promotable.useful_coverage is True
    assert promotable.predictive_non_degradation is True
    assert promotable.interval_non_degradation is True
    assert promotable.decision_non_degradation is True
    assert negative.predictive_non_degradation is False


def test_simultaneous_family_bound_is_stricter_than_an_uncorrected_metric_bound():
    value = protocol(small=True)
    # The isolated 5% upper quantile is zero, but the preregistered family-wide tail sees the
    # adverse replicate and therefore cannot declare non-degradation.
    assessment = _assess(value, change=("log_loss", (0.0,) * 99 + (0.10,)))
    clauses = [clause for clause in assessment.clauses if clause.metric == "log_loss"]
    assert assessment.status == "inconclusive"
    assert all(clause.status == "inconclusive" for clause in clauses)
    assert all(clause.upper_bound > value.margins.max_log_loss_delta for clause in clauses)


def test_negative_decision_evidence_cannot_be_hidden_by_predictive_gains():
    value = protocol(small=True)
    assessment = _assess(value, change=("regret", (0.20, 0.20)))
    assert assessment.status == "negative"
    assert assessment.predictive_non_degradation is True
    assert assessment.decision_non_degradation is False
    assert any(clause.metric == "regret" and clause.status == "fail" for clause in assessment.clauses)


def test_only_exact_promotable_assessment_creates_an_inert_proposal():
    value = protocol(small=True)
    assessment = _assess(value)
    proposal = build_operator_proposal(assessment, target_config_version="recurrent-production-v2")
    assert proposal.protocol_sha256 == assessment.protocol_sha256
    assert proposal.candidate_config_sha256 == assessment.candidate_config_sha256
    assert proposal.authority == "operator-review-required"
    assert len(proposal.proposal_id) == 64
    with pytest.raises(ValueError, match="exact promotable"):
        build_operator_proposal(
            assessment.model_copy(update={"status": "negative"}),
            target_config_version="recurrent-production-v2",
        )
    with pytest.raises(ValueError, match="exact promotable"):
        build_operator_proposal(
            assessment.model_copy(update={"clauses": ()}),
            target_config_version="recurrent-production-v2",
        )


def test_outer_outcomes_are_consumed_once_and_candidate_config_is_exact():
    value = protocol(small=True)
    frozen, predictive, decision = _complete_evidence(value)
    with pytest.raises(ValueError, match="exactly once"):
        aggregate_recurrent_validation(
            [predictive, predictive],
            [decision],
            protocol=value,
            candidate_id="recurrent-expanded-v1",
            candidate_config_sha256=frozen.candidate_config_sha256["recurrent-expanded-v1"],
        )
    with pytest.raises(ValueError, match="non-placeholder"):
        aggregate_recurrent_validation(
            [predictive],
            [decision],
            protocol=value,
            candidate_id="recurrent-expanded-v1",
            candidate_config_sha256="0" * 64,
        )
    assert frozen.candidate_config_sha256["recurrent-expanded-v1"] == content_sha256({
        "config": "recurrent-expanded-v1"
    })


def test_predictive_and_decision_branches_must_bind_the_same_origin_and_cases():
    value = protocol(small=True)
    frozen, predictive, decision = _complete_evidence(value)
    with pytest.raises(ValueError, match="origin identities differ"):
        aggregate_recurrent_validation(
            [predictive],
            [decision.model_copy(update={"origin_predictions_sha256": "1" * 64})],
            protocol=value,
            candidate_id="recurrent-expanded-v1",
            candidate_config_sha256=frozen.candidate_config_sha256["recurrent-expanded-v1"],
        )
    with pytest.raises(ValueError, match="field identities differ"):
        aggregate_recurrent_validation(
            [predictive],
            [decision.model_copy(update={"field_mass_sha256": "1" * 64})],
            protocol=value,
            candidate_id="recurrent-expanded-v1",
            candidate_config_sha256=frozen.candidate_config_sha256["recurrent-expanded-v1"],
        )

from pathlib import Path

import pytest

from legacy_engine.advisory.recurrent_validation import (
    PromotionAssessment,
    aggregate_recurrent_validation,
    build_operator_proposal,
    load_recurrent_protocol,
)


def test_unsupported_evidence_is_censored_not_promotable():
    protocol = load_recurrent_protocol(Path("src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json"))
    assessments = aggregate_recurrent_validation((), protocol=protocol, candidate_id="recurrent-expanded-v1")
    assert assessments[0].status == "support-censored"
    assert assessments[0].authority == "evidence-only"


def test_operator_proposal_is_inert_and_requires_promotable_status():
    assessment = PromotionAssessment(protocol_sha256="0" * 64, candidate_id="recurrent-expanded-v1", comparator_ids=("current-only-v1",), origin_evaluation_ids=(), clauses=(), useful_coverage=True, predictive_non_degradation=True, interval_non_degradation=True, decision_non_degradation=True, status="promotable")
    proposal = build_operator_proposal(assessment, target_config_version="future-v2")
    assert proposal.authority == "operator-review-required"
    with pytest.raises(ValueError, match="promotable"):
        build_operator_proposal(assessment.model_copy(update={"status": "negative"}), target_config_version="future-v2")

from __future__ import annotations

import pytest

from legacy_engine.advisory.ranking_benchmark import content_sha256
from legacy_engine.advisory.recurrent_validation import (
    GateClause,
    PromotionAssessment,
    write_recurrent_validation_bundle,
)
from legacy_engine.workflows.recurrent_validation import (
    aggregate_recurrent_evidence,
    evaluate_recurrent_origin,
    plan_recurrent_validation,
    write_operator_proposal,
)
from advisory.recurrent_validation_helpers import (
    base_protocol,
    future_rows,
    origin,
    protocol,
)


def test_plan_store_is_content_addressed_idempotent_and_has_no_latest_alias(tmp_path):
    value = protocol(small=True)
    digest = plan_recurrent_validation(value, base_protocol(), artifact_root=tmp_path)
    assert plan_recurrent_validation(value, base_protocol(), artifact_root=tmp_path) == digest
    assert (tmp_path / "protocols" / digest / "protocol.json").is_file()
    assert not any(path.name == "latest" for path in tmp_path.rglob("*"))
    (tmp_path / "protocols" / digest / "protocol.json").write_text("{}")
    with pytest.raises(FileExistsError, match="overwrite"):
        plan_recurrent_validation(value, base_protocol(), artifact_root=tmp_path)


def test_evaluation_store_canonicalizes_input_order_and_rejects_collision(tmp_path):
    value = protocol(small=True)
    frozen = origin(value)
    rows = future_rows(value)
    first = evaluate_recurrent_origin(
        frozen,
        rows,
        protocol=value,
        future_field_counts={"a": 1, "b": 1},
        artifact_root=tmp_path,
    )
    second = evaluate_recurrent_origin(
        frozen,
        list(reversed(rows)),
        protocol=value,
        future_field_counts={"b": 1, "a": 1},
        artifact_root=tmp_path,
    )
    assert first.artifact_sha256 == second.artifact_sha256
    path = tmp_path / "evaluations" / first.artifact_sha256 / "evaluation.json"
    path.write_text("{}")
    with pytest.raises(FileExistsError, match="overwrite"):
        evaluate_recurrent_origin(
            frozen,
            rows,
            protocol=value,
            future_field_counts={"a": 1, "b": 1},
            artifact_root=tmp_path,
        )


def test_aggregate_bundle_contains_both_evidence_branches_and_collision_refuses(tmp_path):
    value = protocol(small=True)
    frozen = origin(value)
    evaluated = evaluate_recurrent_origin(
        frozen,
        future_rows(value),
        protocol=value,
        future_field_counts={"a": 1, "b": 1},
        artifact_root=tmp_path,
    )
    bundle, digest = aggregate_recurrent_evidence(
        value,
        [frozen],
        [evaluated],
        artifact_root=tmp_path,
    )
    bundle_dir = tmp_path / "bundles" / digest
    assert (bundle_dir / "bundle.json").is_file()
    assert (bundle_dir / "summary.md").is_file()
    assert len(bundle.assessments) == 7
    assert all(item.status == "support-censored" for item in bundle.assessments)
    assert bundle.predictive_evaluations[0].future_cases.case_sha256 == (
        bundle.decision_evaluations[0].case_sha256
    )
    (bundle_dir / "summary.md").write_text("divergent")
    with pytest.raises(FileExistsError, match="summary collision"):
        write_recurrent_validation_bundle(tmp_path / "bundles", bundle)


def test_workflow_writes_only_an_inert_operator_proposal(tmp_path):
    value = protocol(small=True)
    candidate_config = content_sha256({"candidate": "recurrent-expanded-v1"})
    clause = GateClause(
        clause_id="fixture-pass",
        comparator_id="current-only-v1",
        metric="log_loss",
        estimate=-0.1,
        lower_bound=-0.1,
        upper_bound=-0.1,
        threshold=0.02,
        status="pass",
    )
    assessment = PromotionAssessment(
        protocol_sha256=content_sha256(value.model_dump(mode="json")),
        candidate_id="recurrent-expanded-v1",
        candidate_config_sha256=candidate_config,
        comparator_ids=("current-only-v1",),
        origin_evaluation_ids=("origin-evaluation",),
        clauses=(clause,),
        useful_coverage=True,
        predictive_non_degradation=True,
        interval_non_degradation=True,
        decision_non_degradation=True,
        status="promotable",
    )
    proposal = write_operator_proposal(
        assessment,
        target_config_version="recurrent-production-v2",
        artifact_root=tmp_path,
    )
    assert (tmp_path / "proposals" / proposal.proposal_id / "proposal.json").is_file()
    assert proposal.authority == "operator-review-required"
    assert not any("apply" in path.name or "latest" in path.name for path in tmp_path.rglob("*"))

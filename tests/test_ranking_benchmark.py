from __future__ import annotations

import hashlib
import json

import pytest

from legacy_engine.advisory.ranking_benchmark import (
    ESTIMATOR_REGISTRY,
    BenchmarkFold,
    BenchmarkProtocol,
    EvaluationSupport,
    ExternalRankingSnapshot,
    FrozenMatchupPrediction,
    FrozenOriginPredictions,
    FrozenRecommendation,
    HeldoutMatch,
    TaxonomySnapshotManifest,
    aggregate_benchmark,
    content_sha256,
    evaluate_origin,
    plan_walk_forward_folds,
    project_matchup_probability,
    protocol_sha256,
    render_benchmark_markdown,
)
from legacy_engine.advisory.ranking_measurement import (
    MethodologyVariantSpec,
    RankingCellMeasurement,
)


def protocol(**updates) -> BenchmarkProtocol:
    values = {
        "protocol_id": "future-test",
        "created_at": "2026-01-01T00:00:00Z",
        "taxonomy_mode": "retrospective-fixed-parent",
        "first_cutoff": "2026-01-01",
        "final_evaluation_until": "2026-03-15",
    }
    values.update(updates)
    return BenchmarkProtocol(**values)


def test_protocol_preregisters_primary_and_estimators():
    configured = protocol()
    assert configured.primary_estimator == "production-ci-gated"
    assert len(configured.estimator_ids) == 10
    with pytest.raises(ValueError, match="preregistered estimator registry"):
        protocol(estimator_ids=("coin-50",))


def test_walk_forward_folds_keep_dates_whole_and_reset_at_ban():
    folds = plan_walk_forward_folds(
        ["2026-01-02", "2026-01-15", "2026-01-15", "2026-01-20", "2026-02-10"],
        ["2026-01-15"],
        protocol(),
    )
    assert [(fold.cutoff, fold.evaluation_until) for fold in folds[:3]] == [
        ("2026-01-01", "2026-01-15"),
        ("2026-01-15", "2026-02-12"),
        ("2026-02-12", "2026-03-12"),
    ]
    assert folds[0].event_dates == ("2026-01-02",)
    assert folds[1].event_dates == ("2026-01-15", "2026-01-20", "2026-02-10")
    assert all(left.evaluation_until <= right.cutoff for left, right in zip(folds, folds[1:]))
    assert protocol_sha256(protocol()) == protocol_sha256(protocol())


def test_future_dated_taxonomy_manifest_shape_is_typed():
    payload = b"rules"
    manifest = TaxonomySnapshotManifest(
        source="operator fixture", effective_at="2027-01-01", rules_manifest="rules.json",
        rules_sha256=hashlib.sha256(payload).hexdigest(),
    )
    assert json.loads(manifest.model_dump_json())["action_level"] == "parent"


def test_unresolved_production_projection_is_explicit_unserved_half():
    cell = RankingCellMeasurement(
        subject="A", opponent="B", field_share=1.0, era=None, fallback=None,
        selected_kind=None, selected=None, selection_reason="none", measured=False,
        concentration_warning=None,
    )
    projected = project_matchup_probability(cell, spec=MethodologyVariantSpec(
        id="ci-gated", label="gated", source_policy="selected", rate_basis="shrunk",
        evidence_n=8,
    ))
    assert projected.probability == 0.5
    assert projected.imputed is True and projected.served is False
    assert "no frozen matchup evidence" in projected.refusal_reason


def _evaluation_protocol() -> BenchmarkProtocol:
    return protocol(
        final_evaluation_until="2026-01-29", bootstrap_draws=50,
        support=EvaluationSupport(
            min_common_matches=2, min_events=2, min_event_dates=2,
            min_calibration_matches=2, min_supported_actions=2, min_action_matches=1,
            min_future_field_coverage=0.8, min_claim_folds=2, min_claim_regimes=1,
        ),
    )


def _predictions(configured: BenchmarkProtocol) -> FrozenOriginPredictions:
    fold = BenchmarkFold(
        fold_id="f", cutoff="2026-01-01", evaluation_until="2026-01-29",
        regime_start="2025-11-10", regime_end=None,
        event_dates=("2026-01-02", "2026-01-03"),
    )
    matchup = []
    recommendations = []
    for estimator in ESTIMATOR_REGISTRY:
        for subject in ("A", "B"):
            for opponent in ("A", "B"):
                probability = 0.5
                if estimator == "production-ci-gated" and subject != opponent:
                    probability = 0.8 if subject == "A" else 0.2
                matchup.append(FrozenMatchupPrediction(
                    estimator=estimator, subject=subject, opponent=opponent,
                    probability=probability, served=True, source_kind="fixture",
                    imputed=False, refusal_reason=None,
                ))
        recommendations.append(FrozenRecommendation(
            estimator=estimator, chosen_action="A", ranked_actions=("A", "B"),
            scores={"A": 0.6, "B": 0.4}, served=True, refusal_reason=None,
        ))
    return FrozenOriginPredictions(
        protocol_hash=protocol_sha256(configured), snapshot_manifest_sha256="snapshot",
        fold=fold, generated_at=configured.created_at, code_commit="commit",
        taxonomy_mode=configured.taxonomy_mode, taxonomy_effective_at=None,
        taxonomy_sha256="taxonomy", rules_sha256="rules",
        estimator_registry=ESTIMATOR_REGISTRY, action_universe=("A", "B"),
        field_shares={"A": 0.5, "B": 0.5}, matchup_predictions=tuple(matchup),
        recommendations=tuple(recommendations), methodology={}, seeds={"benchmark": configured.seed},
    )


def _heldout(*, a_wins: bool = True) -> list[HeldoutMatch]:
    return [
        HeldoutMatch(
            event_id=f"e{index}", event_date=f"2026-01-0{index + 2}", provenance="online",
            subject="A", opponent="B", subject_player_key=None, opponent_player_key=None,
            subject_won=a_wins, exclusion_reason=None,
        )
        for index in range(2)
    ]


def test_future_outcome_swap_changes_evaluation_not_frozen_prediction():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    frozen_hash = content_sha256(frozen)
    favorable = evaluate_origin(frozen, _heldout(a_wins=True), protocol=configured)
    adverse = evaluate_origin(frozen, _heldout(a_wins=False), protocol=configured)
    good = next(item for item in favorable.estimators if item.estimator == "production-ci-gated")
    bad = next(item for item in adverse.estimators if item.estimator == "production-ci-gated")
    assert good.log_loss < bad.log_loss
    assert content_sha256(frozen) == frozen_hash
    assert favorable.status == "descriptive"
    assert favorable.player_sensitivity_reason.startswith("player-component sensitivity unavailable")


def test_exclusions_common_case_and_bootstrap_are_deterministic():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    rows = [
        *_heldout(),
        HeldoutMatch(
            event_id="mirror", event_date="2026-01-04", provenance="online",
            subject="A", opponent="A", subject_player_key="p", opponent_player_key="q",
            subject_won=True, exclusion_reason=None,
        ),
        HeldoutMatch(
            event_id="new", event_date="2026-01-05", provenance="online",
            subject="New", opponent="Other", subject_player_key="p", opponent_player_key="q",
            subject_won=True, exclusion_reason=None,
        ),
    ]
    first = evaluate_origin(frozen, rows, protocol=configured)
    second = evaluate_origin(frozen, rows, protocol=configured)
    assert first == second
    assert first.exclusions["mirror"] == 1
    assert first.exclusions["emerging-label"] == 1
    assert {item.common_matches for item in first.estimators} == {2}


def test_player_component_sensitivity_is_coverage_gated_and_seeded():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    rows = [match.model_copy(update={
        "subject_player_key": f"a{index}", "opponent_player_key": f"b{index}",
    }) for index, match in enumerate(_heldout())]
    result = evaluate_origin(frozen, rows, protocol=configured)
    assert result.player_sensitivity_reason is None
    assert result.player_sensitivity["identity_coverage"] == 1.0
    assert result.player_sensitivity["components"] == 2.0
    assert result.player_sensitivity["primary_log_loss_ci_low"] <= result.player_sensitivity[
        "primary_log_loss_ci_high"
    ]


def test_external_snapshot_is_dated_exact_and_partial():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    with pytest.raises(ValueError, match="future-dated"):
        evaluate_origin(frozen, _heldout(), protocol=configured, external=[
            ExternalRankingSnapshot(
                source="future", observed_at="2026-01-02T00:00:00Z", taxonomy="parent",
                ranks={"A": 1},
            )
        ])
    result = evaluate_origin(frozen, _heldout(), protocol=configured, external=[
        ExternalRankingSnapshot(
            source="dated", observed_at="2025-12-31T00:00:00Z", taxonomy="parent",
            scores={"A": 1.0}, matchup_probabilities={"A|||B": 0.7},
        )
    ])
    assert result.external[0].estimator == "external:dated"
    assert result.external[0].common_matches == 2


def test_aggregate_remains_descriptive_without_claim_support():
    configured = _evaluation_protocol()
    fold = evaluate_origin(_predictions(configured), _heldout(), protocol=configured)
    summary = aggregate_benchmark(configured, [fold])
    assert summary.status == "descriptive"
    assert "evaluable folds 1 < 2" in summary.reasons
    rendered = render_benchmark_markdown(summary)
    assert "Evaluation is read-only" in rendered
    assert "Paired primary-minus-baseline log loss" in rendered


def test_aggregate_requires_both_calibration_coefficients():
    configured = _evaluation_protocol()
    fold = evaluate_origin(_predictions(configured), _heldout(), protocol=configured)
    estimators = tuple(
        item.model_copy(update={"calibration_intercept": None, "calibration_slope": 1.0})
        if item.estimator == configured.primary_estimator else item
        for item in fold.estimators
    )
    summary = aggregate_benchmark(configured, [
        fold.model_copy(update={"estimators": estimators}),
        fold.model_copy(update={"estimators": estimators}),
    ])
    assert "required primary calibration metrics are unavailable" in summary.reasons

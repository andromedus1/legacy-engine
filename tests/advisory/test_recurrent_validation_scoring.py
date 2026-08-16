from pathlib import Path

from legacy_engine.advisory.recurrent_validation import (
    FrozenEvidencePrediction,
    build_future_case_manifest,
    evaluate_recurrent_predictions,
    freeze_origin,
    load_recurrent_protocol,
)


def test_common_case_manifest_and_scores_are_estimator_independent():
    protocol = load_recurrent_protocol(Path("src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json"))
    predictions = tuple(FrozenEvidencePrediction(estimator_id=method, subject="a", opponent="b", probability=0.75, served=True, evidence_kind="current-only", current_match_ids_sha256="0" * 64, imputation="none", fit_id=method) for method in protocol.estimator_ids)
    origin = freeze_origin(protocol, protocol.folds[0], stage_artifacts={name: name for name in ("snapshot", "discovery", "certification", "interval", "amplification", "structure")}, predictions=predictions)
    cases = build_future_case_manifest("origin-2026-01", [{"match_id": "m1", "event_id": "e1", "subject": "a", "opponent": "b", "subject_won": True}])
    evaluation = evaluate_recurrent_predictions(origin, cases, protocol=protocol, outcomes=[{"match_id": "m1", "event_id": "e1", "subject": "a", "opponent": "b", "subject_won": True}])
    assert evaluation.status == "complete"
    assert all(metric.common_matches == 1 and metric.log_loss is not None for metric in evaluation.metrics)


def test_missing_candidate_prediction_is_invalid_not_case_deletion():
    protocol = load_recurrent_protocol(Path("src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json"))
    origin = freeze_origin(protocol, protocol.folds[0], stage_artifacts={name: name for name in ("snapshot", "discovery", "certification", "interval", "amplification", "structure")})
    cases = build_future_case_manifest("origin-2026-01", [{"match_id": "m1", "event_id": "e1"}])
    evaluation = evaluate_recurrent_predictions(origin, cases, protocol=protocol, outcomes=[{"match_id": "m1", "event_id": "e1", "subject": "a", "opponent": "b", "subject_won": True}])
    assert evaluation.status == "invalid"
    assert all(metric.common_matches == 0 for metric in evaluation.metrics)

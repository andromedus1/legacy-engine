from pathlib import Path

from legacy_engine.advisory.recurrent_validation import (
    build_future_case_manifest,
    evaluate_recurrent_decisions,
    freeze_origin,
    load_recurrent_protocol,
)


def test_decision_refusal_is_censored_and_does_not_become_zero_regret():
    protocol = load_recurrent_protocol(Path("src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json"))
    origin = freeze_origin(protocol, protocol.folds[0], stage_artifacts={name: name for name in ("snapshot", "discovery", "certification", "interval", "amplification", "structure")})
    cases = build_future_case_manifest("origin-2026-01", [{"match_id": "m1", "event_id": "e1"}])
    evaluation = evaluate_recurrent_decisions(origin, cases, protocol=protocol, outcomes=[{"match_id": "m1", "event_id": "e1", "subject": "a", "subject_won": True}])
    assert evaluation.status == "support-censored"
    assert all(item.regret is None for item in evaluation.evaluations)


def test_decision_replay_uses_same_event_ledger():
    protocol = load_recurrent_protocol(Path("src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json"))
    origin = freeze_origin(protocol, protocol.folds[0], stage_artifacts={name: name for name in ("snapshot", "discovery", "certification", "interval", "amplification", "structure")}, action_universe=("a",), field_shares={"a": 1.0})
    cases = build_future_case_manifest("origin-2026-01", [{"match_id": "m1", "event_id": "e1"}])
    evaluation = evaluate_recurrent_decisions(origin, cases, protocol=protocol, outcomes=[{"match_id": "m1", "event_id": "e1", "subject": "a", "subject_won": True}])
    assert evaluation.field_mass_sha256 == cases.field_mass_sha256
    assert evaluation.action_universe_sha256

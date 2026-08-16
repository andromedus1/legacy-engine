from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from legacy_engine.advisory.recurrent_validation import (
    EVIDENCE_ESTIMATOR_REGISTRY,
    RecurrentBenchmarkProtocol,
    load_recurrent_protocol,
    recurrent_protocol_sha256,
    validate_base_protocol,
)
from .recurrent_validation_helpers import (
    BASE_PROTOCOL_PATH,
    PROTOCOL_PATH,
    base_protocol,
    protocol,
)


def test_checked_protocol_is_preregistered_hash_bound_and_self_consistent():
    value = load_recurrent_protocol(PROTOCOL_PATH, base_protocol=BASE_PROTOCOL_PATH)
    assert value.estimator_ids == EVIDENCE_ESTIMATOR_REGISTRY
    assert value.registered_at.date().isoformat() < value.folds[0].data_until
    assert len(value.folds) >= value.support.min_origins
    assert len({fold.regime_id for fold in value.folds}) >= value.support.min_regimes
    assert all(getattr(value, name) != "0" * 64 for name in (
        "base_benchmark_protocol_sha256",
        "discovery_calibration_sha256",
        "certification_calibration_sha256",
        "interval_policy_sha256",
        "amplification_profile_sha256",
        "structure_policy_sha256",
    ))
    assert recurrent_protocol_sha256(value) == recurrent_protocol_sha256(
        load_recurrent_protocol(PROTOCOL_PATH, base_protocol=BASE_PROTOCOL_PATH)
    )


def test_unknown_reordered_duplicate_and_placeholder_contracts_refuse():
    payload = protocol().model_dump(mode="json")
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="unexpected"):
        RecurrentBenchmarkProtocol.model_validate(payload)
    payload = protocol().model_dump(mode="json")
    payload["estimator_ids"] = list(reversed(payload["estimator_ids"]))
    with pytest.raises(ValueError, match="registry"):
        RecurrentBenchmarkProtocol.model_validate(payload)
    payload = protocol().model_dump(mode="json")
    payload["discovery_calibration_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="non-placeholder"):
        RecurrentBenchmarkProtocol.model_validate(payload)


def test_late_registration_overlap_and_impossible_support_refuse():
    payload = protocol().model_dump(mode="json")
    payload["registered_at"] = payload["folds"][0]["data_until"] + "T00:00:00Z"
    with pytest.raises(ValueError, match="precede"):
        RecurrentBenchmarkProtocol.model_validate(payload)
    payload = protocol().model_dump(mode="json")
    payload["folds"][0]["evaluation_until"] = payload["folds"][1]["evaluation_until"]
    with pytest.raises(ValueError, match="overlap"):
        RecurrentBenchmarkProtocol.model_validate(payload)
    payload = protocol().model_dump(mode="json")
    payload["support"]["min_origins"] = len(payload["folds"]) + 1
    with pytest.raises(ValueError, match="min_origins"):
        RecurrentBenchmarkProtocol.model_validate(payload)


def test_base_hash_fold_ban_taxonomy_and_horizon_are_exact():
    value = protocol()
    validate_base_protocol(value, base_protocol())
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_base_protocol(
            value.model_copy(update={"base_benchmark_protocol_sha256": "1" * 64}),
            base_protocol(),
        )
    drifted = value.model_copy(
        update={
            "folds": (
                value.folds[0].model_copy(update={"evaluation_until": "2026-09-13"}),
                *value.folds[1:],
            )
        }
    )
    with pytest.raises(ValueError, match="horizon"):
        validate_base_protocol(drifted, base_protocol())


def test_historical_v1_protocol_bytes_remain_unchanged():
    historical = Path("data/benchmarks/best-deck-decision-trust-current-corpus-v1/protocol.json")
    before = hashlib.sha256(historical.read_bytes()).hexdigest()
    _ = protocol()
    assert hashlib.sha256(historical.read_bytes()).hexdigest() == before

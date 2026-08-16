from pathlib import Path

import pytest

from legacy_engine.advisory.recurrent_validation import (
    EVIDENCE_ESTIMATOR_REGISTRY,
    RecurrentBenchmarkProtocol,
    load_recurrent_protocol,
    recurrent_protocol_sha256,
)


PROTOCOL = Path("src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json")


def test_recurrent_protocol_is_additive_closed_and_registry_bound():
    protocol = load_recurrent_protocol(PROTOCOL)
    assert protocol.estimator_ids == EVIDENCE_ESTIMATOR_REGISTRY
    assert protocol.authority == "evaluation-only"
    assert "winner" not in protocol.model_dump(mode="json")
    assert recurrent_protocol_sha256(protocol) == recurrent_protocol_sha256(load_recurrent_protocol(PROTOCOL))


def test_registry_duplicate_or_unknown_fields_refuse():
    payload = load_recurrent_protocol(PROTOCOL).model_dump(mode="json")
    payload["estimator_ids"] = list(EVIDENCE_ESTIMATOR_REGISTRY[:-1]) + [EVIDENCE_ESTIMATOR_REGISTRY[-2]]
    with pytest.raises(ValueError, match="registry"):
        RecurrentBenchmarkProtocol.model_validate(payload)
    payload = load_recurrent_protocol(PROTOCOL).model_dump(mode="json")
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="unexpected"):
        RecurrentBenchmarkProtocol.model_validate(payload)


def test_fold_clock_and_hash_validation():
    payload = load_recurrent_protocol(PROTOCOL).model_dump(mode="json")
    payload["folds"][0]["knowledge_as_of"] = "2025-01-01T00:00:00Z"
    assert RecurrentBenchmarkProtocol.model_validate(payload).folds[0].knowledge_as_of.tzinfo is not None
    payload["base_benchmark_protocol_sha256"] = "bad"
    with pytest.raises(ValueError, match="SHA-256"):
        RecurrentBenchmarkProtocol.model_validate(payload)

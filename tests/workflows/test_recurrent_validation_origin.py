from pathlib import Path

import pytest

from legacy_engine.advisory.recurrent_validation import (
    FrozenEvidencePrediction,
    freeze_origin,
    load_recurrent_protocol,
)


def test_origin_requires_all_injected_stage_artifacts():
    protocol = load_recurrent_protocol(Path("src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json"))
    origin = freeze_origin(protocol, protocol.folds[0], stage_artifacts={})
    assert origin.manifest.status == "not-evaluable"
    assert "missing stage artifacts" in origin.manifest.reasons[0]


def test_origin_prediction_rejects_invalid_probability():
    with pytest.raises(ValueError, match="probability"):
        FrozenEvidencePrediction(
            estimator_id="current-only-v1", subject="a", opponent="b", probability=1.2,
            served=False, evidence_kind="current-only", current_match_ids_sha256="0" * 64,
            imputation="none", fit_id="fit",
        )


def test_origin_is_deterministic_for_same_injected_bundle():
    protocol = load_recurrent_protocol(Path("src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json"))
    artifacts = {name: name + "-digest" for name in ("snapshot", "discovery", "certification", "interval", "amplification", "structure")}
    left = freeze_origin(protocol, protocol.folds[0], stage_artifacts=artifacts)
    right = freeze_origin(protocol, protocol.folds[0], stage_artifacts=artifacts)
    assert left.model_dump(mode="json") == right.model_dump(mode="json")

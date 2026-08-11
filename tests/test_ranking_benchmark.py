from __future__ import annotations

import hashlib
import json

import pytest

from legacy_engine.advisory.ranking_benchmark import (
    BenchmarkProtocol,
    TaxonomySnapshotManifest,
    plan_walk_forward_folds,
    protocol_sha256,
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

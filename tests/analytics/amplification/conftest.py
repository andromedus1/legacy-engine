from __future__ import annotations

import copy

import pytest

from legacy_engine.analytics.amplification import (
    AmplificationProfile,
    StructureSnapshot,
    load_amplification_profile,
    run_amplification,
)
from legacy_engine.analytics.eras.certificate_store import write_certification_run
from legacy_engine.analytics.matchup import build_interval_adaptive_matrix
from tests.analytics.eras.test_interval_consumption import _clock, _matrix_db, _run


@pytest.fixture
def interval_matrix():
    con = _matrix_db()
    certificate = _run()
    write_certification_run(con, certificate)
    return build_interval_adaptive_matrix(
        con,
        clock=_clock(),
        certificate_run_id=certificate.run_id,
        min_row_share=0.0,
    )


@pytest.fixture
def diagnostic_profile():
    payload = load_amplification_profile(
        "src/legacy_engine/data/amplification/diagnostic-v1.json"
    ).model_dump(mode="json")
    payload["bootstrap_replicates"] = 4
    payload["service_gates"] = {
        "min_effective_events": 0,
        "min_effective_components": 0,
        "min_effective_donor_pairs": 0,
        "max_event_share": 1,
        "max_component_share": 1,
        "max_donor_share": 1,
        "max_ablation_delta": 1,
        "min_bootstrap_success_fraction": 1,
    }
    for spec in payload["method_specs"]:
        if spec["method_id"] == "composition-kernel-v1":
            spec["parameters"].update({"min_similarity": 0.2, "min_weight": 0.0})
        elif spec["method_id"] == "strategic-family-ladder-v1":
            spec["parameters"]["min_member_matches"] = 1
        elif spec["method_id"].startswith("skew-low-rank"):
            spec["parameters"].update({"multistarts": 2, "max_iterations": 80})
    return AmplificationProfile.model_validate(payload)


@pytest.fixture
def structure(interval_matrix):
    return StructureSnapshot(
        snapshot_id="structure-fixture-v1",
        knowledge_as_of=interval_matrix.clock.knowledge_as_of,
        taxonomy_id="taxonomy-v1",
        superarchetype_registry_sha256="a" * 64,
        composition_features_sha256="b" * 64,
        entities=("A", "B", "C"),
        composition_features={
            "A": ("blue", "tempo"),
            "B": ("red", "tempo"),
            "C": ("blue", "control"),
        },
        strategic_families={"A": "fair", "B": "fair", "C": "control"},
    )


@pytest.fixture
def amplification_run(interval_matrix, structure, diagnostic_profile):
    # Copy inputs so mutation checks can compare the caller's objects after the run.
    return run_amplification(
        copy.deepcopy(interval_matrix), structure, diagnostic_profile
    )

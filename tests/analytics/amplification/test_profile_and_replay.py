from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from legacy_engine.analytics.amplification import (
    AmplificationProfile,
    make_event_bootstrap_plan,
    run_amplification,
)
from legacy_engine.analytics.amplification.corpus import build_interval_evidence_corpus


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["method_specs"][0].update({"parameters": {"rank": 1}}),
        lambda p: p["method_specs"][0].update({"method_id": "unknown-v1"}),
        lambda p: p["method_specs"][1]["parameters"].update({"bandwidth": -1}),
        lambda p: p["method_specs"][1]["parameters"].update(
            {"bandwidth": float("nan")}
        ),
        lambda p: p["method_specs"][3]["parameters"].update({"rank": 2}),
        lambda p: p["service_gates"].update({"min_effective_events": -1}),
        lambda p: p["service_gates"].update({"max_donor_share": float("nan")}),
    ],
)
def test_profile_is_closed_discriminated_and_finite(diagnostic_profile, mutation):
    payload = diagnostic_profile.model_dump(mode="json")
    mutation(payload)
    with pytest.raises(ValidationError):
        AmplificationProfile.model_validate(payload)


def test_runner_honors_enabled_order_seed_and_replay(
    interval_matrix, structure, diagnostic_profile
):
    payload = diagnostic_profile.model_dump(mode="json")
    payload["method_specs"] = list(reversed(payload["method_specs"]))
    payload["method_specs"][1]["enabled"] = False
    profile = AmplificationProfile.model_validate(payload)
    corpus = build_interval_evidence_corpus(interval_matrix)
    plan = make_event_bootstrap_plan(
        corpus,
        origin_snapshot_id="historical-origin-42",
        seed=profile.seed,
        replicates=profile.bootstrap_replicates,
    )
    first = run_amplification(
        interval_matrix,
        structure,
        profile,
        origin_snapshot_id="historical-origin-42",
        bootstrap_plan=plan,
    )
    second = run_amplification(
        interval_matrix,
        structure,
        profile,
        origin_snapshot_id="historical-origin-42",
        bootstrap_plan=copy.deepcopy(plan),
    )
    expected = tuple(spec.method_id for spec in profile.method_specs if spec.enabled)
    assert tuple(candidate.method_id for candidate in first.candidates) == expected
    assert first.aligned_draws.method_ids == expected
    assert first == second
    assert first.aligned_draws.origin_snapshot_id == "historical-origin-42"
    assert all(
        len(series.probabilities) == profile.bootstrap_replicates
        for series in first.aligned_draws.series
    )
    assert (
        len({len(series.probabilities) for series in first.aligned_draws.series}) == 1
    )


def test_seed_offset_is_bound_to_low_rank_fit_identity(
    interval_matrix, structure, diagnostic_profile
):
    first = run_amplification(interval_matrix, structure, diagnostic_profile)
    payload = diagnostic_profile.model_dump(mode="json")
    low_rank = next(
        spec
        for spec in payload["method_specs"]
        if spec["method_id"] == "skew-low-rank-r1-v1"
    )
    low_rank["seed_offset"] = 99
    changed = run_amplification(
        interval_matrix, structure, AmplificationProfile.model_validate(payload)
    )
    first_fit = next(
        candidate.fit_id
        for candidate in first.candidates
        if candidate.method_id == "skew-low-rank-r1-v1"
    )
    changed_fit = next(
        candidate.fit_id
        for candidate in changed.candidates
        if candidate.method_id == "skew-low-rank-r1-v1"
    )
    assert changed_fit != first_fit


def test_replay_refuses_current_origin_or_event_injection(
    interval_matrix, structure, diagnostic_profile
):
    corpus = build_interval_evidence_corpus(interval_matrix)
    plan = make_event_bootstrap_plan(
        corpus,
        origin_snapshot_id="origin-a",
        seed=diagnostic_profile.seed,
        replicates=diagnostic_profile.bootstrap_replicates,
    )
    with pytest.raises(ValueError, match="origin"):
        run_amplification(
            interval_matrix,
            structure,
            diagnostic_profile,
            origin_snapshot_id="origin-b",
            bootstrap_plan=plan,
        )
    altered = plan.model_copy(
        update={
            "event_blocks": (("future-event",),)
            * diagnostic_profile.bootstrap_replicates
        }
    )
    with pytest.raises(ValueError, match="digest"):
        run_amplification(
            interval_matrix,
            structure,
            diagnostic_profile,
            origin_snapshot_id="origin-a",
            bootstrap_plan=altered,
        )

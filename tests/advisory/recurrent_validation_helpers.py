from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from legacy_engine.advisory.ranking_benchmark import BenchmarkProtocol, content_sha256
from legacy_engine.advisory.recurrent_validation import (
    EVIDENCE_ESTIMATOR_REGISTRY,
    FrozenDrawSeries,
    FrozenEvidencePrediction,
    FrozenJointDraws,
    FrozenRecurrentOrigin,
    OriginForecastPayload,
    RecurrentBenchmarkProtocol,
    RefitStageArtifact,
    load_recurrent_protocol,
    seal_recurrent_origin,
)

PROTOCOL_PATH = Path("src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json")
BASE_PROTOCOL_PATH = Path("src/legacy_engine/data/benchmark/recurrent-parent-future-v1.json")


def base_protocol() -> BenchmarkProtocol:
    return BenchmarkProtocol.model_validate_json(BASE_PROTOCOL_PATH.read_bytes())


def protocol(*, small: bool = False) -> RecurrentBenchmarkProtocol:
    value = load_recurrent_protocol(PROTOCOL_PATH, base_protocol=base_protocol())
    if not small:
        return value
    return value.model_copy(
        update={
            "bootstrap_draws": 40,
            "support": value.support.model_copy(
                update={
                    "min_common_matches": 1,
                    "min_events": 1,
                    "min_event_dates": 1,
                    "min_origins": 1,
                    "min_regimes": 1,
                    "min_calibration_matches": 2,
                    "min_supported_actions": 2,
                    "min_action_matches": 1,
                    "min_future_field_coverage": 0.5,
                }
            ),
        }
    )


def refit_stages(
    value: RecurrentBenchmarkProtocol,
    snapshot_sha: str,
    *,
    max_outcome_date: str | None = None,
) -> tuple[RefitStageArtifact, ...]:
    fold = value.folds[0]
    pair_sha = content_sha256(("a\0b", "b\0a"))
    configs = {
        "discovery": value.discovery_calibration_sha256,
        "certification": value.certification_calibration_sha256,
        "interval": value.interval_policy_sha256,
        "structure": value.structure_policy_sha256,
        "amplification": value.amplification_profile_sha256,
    }
    prior = snapshot_sha
    stages = []
    for stage in configs:
        output = content_sha256({"stage": stage, "input": prior})
        artifact = RefitStageArtifact(
            stage=stage,
            run_id=f"{stage}-run",
            input_sha256=prior,
            output_sha256=output,
            config_sha256=configs[stage],
            data_until=fold.data_until,
            knowledge_as_of=fold.knowledge_as_of,
            max_outcome_date=(None if stage in {"discovery", "structure"} else max_outcome_date),
            outcome_ids_sha256=content_sha256(("past-match",) if stage != "discovery" else ()),
            pair_universe_sha256=pair_sha if stage in {"interval", "amplification"} else None,
        )
        stages.append(artifact)
        prior = output
    return tuple(stages)


def forecast(
    value: RecurrentBenchmarkProtocol,
    *,
    probability: Callable[[str, str, str], float] | None = None,
    served: Callable[[str, str, str], bool] | None = None,
    recommendations: dict[str, str | None] | None = None,
) -> OriginForecastPayload:
    probability = probability or (lambda _method, subject, _opponent: 0.8 if subject == "a" else 0.2)
    served = served or (lambda _method, _subject, _opponent: True)
    series = []
    fits: dict[tuple[str, str, str], str] = {}
    for estimator in value.estimator_ids:
        for subject, opponent in (("a", "b"), ("b", "a")):
            fit_id = f"fit-{estimator}"
            fits[(estimator, subject, opponent)] = fit_id
            mean = probability(estimator, subject, opponent)
            probabilities = tuple(
                min(1.0, max(0.0, mean + (0.02 if index % 2 else -0.02)))
                for index in range(value.bootstrap_draws)
            )
            series.append(
                FrozenDrawSeries(
                    estimator_id=estimator,
                    subject=subject,
                    opponent=opponent,
                    fit_id=fit_id,
                    probabilities=probabilities,
                )
            )
    draws_sha = content_sha256([item.model_dump(mode="json") for item in series])
    event_blocks_sha = content_sha256(("origin-training-events",))
    draw_payload = {
        "seed": value.seed,
        "replicate_count": value.bootstrap_draws,
        "event_blocks_sha256": event_blocks_sha,
        "series": [item.model_dump(mode="json") for item in series],
        "draws_sha256": draws_sha,
    }
    draw_artifact = content_sha256(draw_payload)
    draws = FrozenJointDraws(
        artifact_sha256=draw_artifact,
        seed=value.seed,
        replicate_count=value.bootstrap_draws,
        event_blocks_sha256=event_blocks_sha,
        series=tuple(series),
        draws_sha256=draws_sha,
    )
    predictions = []
    for estimator in value.estimator_ids:
        evidence_kind = (
            "current-only"
            if estimator == "current-only-v1"
            else "contiguous-era"
            if estimator == "contiguous-era-v1"
            else "certified-expanded"
            if estimator == "recurrent-expanded-v1"
            else "amplified"
        )
        for subject, opponent in (("a", "b"), ("b", "a")):
            predictions.append(
                FrozenEvidencePrediction(
                    estimator_id=estimator,
                    subject=subject,
                    opponent=opponent,
                    probability=probability(estimator, subject, opponent),
                    interval=(0.1, 0.9),
                    draw_artifact_sha256=draw_artifact,
                    served=served(estimator, subject, opponent),
                    fallback_estimator_id=(
                        "current-only-v1"
                        if estimator not in {"current-only-v1", "contiguous-era-v1", "recurrent-expanded-v1"}
                        else None
                    ),
                    evidence_kind=evidence_kind,
                    current_match_ids_sha256=content_sha256(("current",)),
                    historical_match_ids_sha256=(
                        None if estimator == "current-only-v1" else content_sha256(("historical",))
                    ),
                    borrowed_match_ids_sha256=(
                        content_sha256(("borrowed",)) if evidence_kind == "amplified" else None
                    ),
                    imputation="none",
                    fit_id=fits[(estimator, subject, opponent)],
                    effective_support=20.0,
                    event_concentration=0.2,
                    source_concentration=0.2,
                    component_concentration=0.2,
                    donor_concentration=0.2,
                    reasons=(() if served(estimator, subject, opponent) else ("support-refusal",)),
                )
            )
    actions = recommendations or {estimator: "a" for estimator in value.estimator_ids}
    return OriginForecastPayload(
        action_universe=("a", "b"),
        field_shares={"a": 0.5, "b": 0.5},
        predictions=tuple(predictions),
        recommendation_actions=actions,
        joint_draws=draws,
        candidate_config_sha256={
            estimator: content_sha256({"config": estimator})
            for estimator in value.estimator_ids
        },
    )


def origin(
    value: RecurrentBenchmarkProtocol | None = None,
    *,
    probability: Callable[[str, str, str], float] | None = None,
    served: Callable[[str, str, str], bool] | None = None,
    recommendations: dict[str, str | None] | None = None,
) -> FrozenRecurrentOrigin:
    value = value or protocol(small=True)
    snapshot_sha = content_sha256({"snapshot": value.folds[0].fold_id})
    previous_day = (date.fromisoformat(value.folds[0].data_until) - timedelta(days=1)).isoformat()
    return seal_recurrent_origin(
        value,
        value.folds[0],
        snapshot_manifest_sha256=snapshot_sha,
        stages=refit_stages(value, snapshot_sha, max_outcome_date=previous_day),
        forecast=forecast(
            value,
            probability=probability,
            served=served,
            recommendations=recommendations,
        ),
        code_commit="fixture-commit",
    )


def future_rows(value: RecurrentBenchmarkProtocol | None = None) -> list[dict[str, object]]:
    value = value or protocol(small=True)
    day = value.folds[0].data_until
    return [
        {
            "match_id": "m2",
            "event_id": "e2",
            "event_date": day,
            "subject_deck_id": "d3",
            "opponent_deck_id": "d4",
            "subject": "a",
            "opponent": "b",
            "subject_won": True,
        },
        {
            "match_id": "m1",
            "event_id": "e1",
            "event_date": day,
            "subject_deck_id": "d1",
            "opponent_deck_id": "d2",
            "subject": "a",
            "opponent": "b",
            "subject_won": True,
        },
    ]


def all_estimators() -> tuple[str, ...]:
    return EVIDENCE_ESTIMATOR_REGISTRY

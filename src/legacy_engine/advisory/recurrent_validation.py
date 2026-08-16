"""Cutoff-safe, evaluation-only recurrent-era validation contracts and pure logic."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Literal, TypeAlias

import numpy as np
from pydantic import ConfigDict, Field, StrictBool, field_validator, model_validator

from legacy_engine.analytics.amplification import AMPLIFICATION_METHOD_IDS, MethodId
from legacy_engine.advisory.ranking_benchmark import (
    BenchmarkProtocol,
    atomic_write_canonical,
    content_sha256,
    protocol_sha256,
)
from legacy_engine.models.base import LegacyEngineModel

DirectEstimatorId = Literal[
    "current-only-v1", "contiguous-era-v1", "recurrent-expanded-v1"
]
EvidenceEstimatorId: TypeAlias = DirectEstimatorId | MethodId
DIRECT_ESTIMATOR_IDS: tuple[DirectEstimatorId, ...] = (
    "current-only-v1",
    "contiguous-era-v1",
    "recurrent-expanded-v1",
)
EVIDENCE_ESTIMATOR_REGISTRY = DIRECT_ESTIMATOR_IDS + AMPLIFICATION_METHOD_IDS
ReplayMode = Literal["contemporaneous", "retrospective-policy-replay"]
EvaluationStatus = Literal["complete", "support-censored", "invalid"]
PromotionStatus = Literal[
    "promotable", "negative", "inconclusive", "support-censored", "invalid"
]

_HEX = frozenset("0123456789abcdef")
_STAGE_ORDER = ("discovery", "certification", "interval", "structure", "amplification")
_INTEGRITY_FIELDS = (
    "base_benchmark_protocol_sha256",
    "base_fold_plan_sha256",
    "base_ban_ledger_sha256",
    "discovery_calibration_sha256",
    "certification_calibration_sha256",
    "interval_policy_sha256",
    "amplification_profile_sha256",
    "structure_policy_sha256",
)


class _ClosedModel(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and set(value) <= _HEX


def _require_sha256(name: str, value: str) -> None:
    if not _is_sha256(value) or value == "0" * 64:
        raise ValueError(f"{name} must be a non-placeholder lowercase SHA-256 digest")


class PromotionMargins(_ClosedModel):
    alpha: float = Field(gt=0, lt=1)
    min_served_field_coverage_gain: float = Field(ge=0, le=1)
    min_served_event_coverage_gain: float = Field(ge=0, le=1)
    max_log_loss_delta: float = Field(ge=0)
    max_brier_delta: float = Field(ge=0)
    max_calibration_delta: float = Field(ge=0)
    min_interval_coverage: float = Field(ge=0, le=1)
    max_interval_score_delta: float = Field(ge=0)
    max_regret_delta: float = Field(ge=0)
    oracle_practical_tie_margin: float = Field(default=0.01, ge=0, le=1)
    min_oracle_stability: float = Field(default=0.80, gt=0, le=1)

    @model_validator(mode="after")
    def _finite(self) -> "PromotionMargins":
        if any(not math.isfinite(value) for value in self.__dict__.values()):
            raise ValueError("promotion margins must be finite")
        return self


class RecurrentEvaluationSupport(_ClosedModel):
    min_common_matches: int = Field(ge=1)
    min_events: int = Field(ge=1)
    min_event_dates: int = Field(ge=1)
    min_origins: int = Field(ge=1)
    min_regimes: int = Field(ge=1)
    min_calibration_matches: int = Field(ge=1)
    min_supported_actions: int = Field(ge=1)
    min_action_matches: int = Field(ge=1)
    min_future_field_coverage: float = Field(ge=0, le=1)


class RecurrentBenchmarkFold(_ClosedModel):
    fold_id: str
    data_until: str
    knowledge_as_of: datetime
    evaluation_until: str
    regime_id: str

    @model_validator(mode="after")
    def _clock(self) -> "RecurrentBenchmarkFold":
        start = date.fromisoformat(self.data_until)
        end = date.fromisoformat(self.evaluation_until)
        if self.knowledge_as_of.tzinfo is None or self.knowledge_as_of.utcoffset() is None:
            raise ValueError("knowledge_as_of must be timezone-aware")
        if end <= start:
            raise ValueError("evaluation_until must follow data_until")
        if self.knowledge_as_of.date() > start:
            raise ValueError("knowledge_as_of cannot follow the exclusive outcome cutoff")
        if not self.fold_id or not self.regime_id:
            raise ValueError("fold_id and regime_id must be non-empty")
        return self


class RecurrentBenchmarkProtocol(_ClosedModel):
    protocol_id: Literal["recurrent-evidence-future-v1"]
    registered_at: datetime
    authority: Literal["evaluation-only"]
    replay_mode: ReplayMode
    base_benchmark_protocol_sha256: str
    base_fold_plan_sha256: str
    base_ban_ledger_sha256: str
    base_taxonomy_mode: Literal["retrospective-fixed-parent", "contemporaneous"]
    estimator_ids: tuple[EvidenceEstimatorId, ...]
    discovery_calibration_sha256: str
    certification_calibration_sha256: str
    interval_policy_sha256: str
    amplification_profile_sha256: str
    structure_policy_sha256: str
    folds: tuple[RecurrentBenchmarkFold, ...]
    log_clip_epsilon: float = Field(gt=0, lt=0.5)
    interval_level: float = Field(gt=0, lt=1)
    bootstrap_draws: int = Field(ge=20)
    seed: int = Field(ge=0)
    support: RecurrentEvaluationSupport
    margins: PromotionMargins

    @model_validator(mode="after")
    def _closed_protocol(self) -> "RecurrentBenchmarkProtocol":
        if tuple(self.estimator_ids) != EVIDENCE_ESTIMATOR_REGISTRY:
            raise ValueError("estimator_ids must exactly equal the frozen recurrent registry")
        for name in _INTEGRITY_FIELDS:
            _require_sha256(name, getattr(self, name))
        if self.registered_at.tzinfo is None or self.registered_at.utcoffset() is None:
            raise ValueError("registered_at must be timezone-aware")
        if not self.folds:
            raise ValueError("at least one fold is required")
        if self.registered_at.date() >= date.fromisoformat(self.folds[0].data_until):
            raise ValueError("protocol registration must precede the first predictive origin")
        ids = tuple(fold.fold_id for fold in self.folds)
        if ids != tuple(dict.fromkeys(ids)):
            raise ValueError("fold ids must be unique")
        ordered = tuple(sorted(self.folds, key=lambda fold: (fold.data_until, fold.fold_id)))
        if self.folds != ordered:
            raise ValueError("folds must be ordered by data_until")
        for left, right in zip(self.folds, self.folds[1:], strict=False):
            if left.evaluation_until > right.data_until:
                raise ValueError("evaluation horizons must not overlap later origins")
        if len(self.folds) < self.support.min_origins:
            raise ValueError("fold plan cannot satisfy min_origins")
        if len({fold.regime_id for fold in self.folds}) < self.support.min_regimes:
            raise ValueError("fold plan cannot satisfy min_regimes")
        return self


def recurrent_protocol_sha256(protocol: RecurrentBenchmarkProtocol) -> str:
    return content_sha256(protocol.model_dump(mode="json"))


def validate_base_protocol(
    protocol: RecurrentBenchmarkProtocol,
    base_protocol: BenchmarkProtocol,
) -> None:
    """Prove the recurrent origins are exact members of the hash-bound parent plan."""
    if protocol_sha256(base_protocol) != protocol.base_benchmark_protocol_sha256:
        raise ValueError("base benchmark protocol hash mismatch")
    fold_plan = content_sha256(
        [fold.model_dump(mode="json") for fold in base_protocol.planned_folds]
    )
    if fold_plan != protocol.base_fold_plan_sha256:
        raise ValueError("base benchmark fold-plan hash mismatch")
    if content_sha256(base_protocol.ban_events_as_of) != protocol.base_ban_ledger_sha256:
        raise ValueError("base benchmark B&R ledger hash mismatch")
    if base_protocol.taxonomy_mode != protocol.base_taxonomy_mode:
        raise ValueError("base benchmark taxonomy mode mismatch")
    by_id = {fold.fold_id: fold for fold in base_protocol.planned_folds}
    for fold in protocol.folds:
        base = by_id.get(fold.fold_id)
        if base is None:
            raise ValueError(f"recurrent fold {fold.fold_id!r} is absent from the base plan")
        if base.cutoff != fold.data_until or base.evaluation_until != fold.evaluation_until:
            raise ValueError(f"recurrent fold {fold.fold_id!r} horizon differs from base plan")
        if base.regime_start != fold.regime_id:
            raise ValueError(f"recurrent fold {fold.fold_id!r} regime differs from base plan")


def load_recurrent_protocol(
    path: Path | str,
    *,
    base_protocol: BenchmarkProtocol | Path | str | None = None,
) -> RecurrentBenchmarkProtocol:
    protocol_path = Path(path)
    try:
        raw = json.loads(protocol_path.read_text(encoding="utf-8"))
        protocol = RecurrentBenchmarkProtocol.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid recurrent protocol {protocol_path}: {exc}") from exc
    if base_protocol is not None:
        base = (
            BenchmarkProtocol.model_validate_json(Path(base_protocol).read_bytes())
            if isinstance(base_protocol, (str, Path))
            else base_protocol
        )
        validate_base_protocol(protocol, base)
    return protocol


StageName = Literal["discovery", "certification", "interval", "structure", "amplification"]


class RefitStageArtifact(_ClosedModel):
    stage: StageName
    run_id: str
    input_sha256: str
    output_sha256: str
    config_sha256: str
    data_until: str
    knowledge_as_of: datetime
    max_outcome_date: str | None = None
    outcome_ids_sha256: str
    pair_universe_sha256: str | None = None
    outcome_columns_accessed: tuple[str, ...] = ()
    status: Literal["complete", "not-evaluable", "invalid"] = "complete"
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _identity(self) -> "RefitStageArtifact":
        for name in ("input_sha256", "output_sha256", "config_sha256", "outcome_ids_sha256"):
            _require_sha256(name, getattr(self, name))
        if self.pair_universe_sha256 is not None:
            _require_sha256("pair_universe_sha256", self.pair_universe_sha256)
        if self.knowledge_as_of.tzinfo is None or self.knowledge_as_of.utcoffset() is None:
            raise ValueError("stage knowledge_as_of must be timezone-aware")
        if not self.run_id:
            raise ValueError("stage run_id must be non-empty")
        return self


class FrozenEvidencePrediction(_ClosedModel):
    estimator_id: EvidenceEstimatorId
    subject: str
    opponent: str
    probability: float | None
    interval: tuple[float, float] | None = None
    draw_artifact_sha256: str | None = None
    served: bool
    fallback_estimator_id: Literal["current-only-v1"] | None = None
    evidence_kind: Literal[
        "current-only", "contiguous-era", "certified-expanded", "amplified"
    ]
    current_match_ids_sha256: str
    historical_match_ids_sha256: str | None = None
    borrowed_match_ids_sha256: str | None = None
    imputation: Literal["none", "partial", "full"]
    fit_id: str
    effective_support: float | None = Field(default=None, ge=0)
    event_concentration: float | None = Field(default=None, ge=0, le=1)
    source_concentration: float | None = Field(default=None, ge=0, le=1)
    component_concentration: float | None = Field(default=None, ge=0, le=1)
    donor_concentration: float | None = Field(default=None, ge=0, le=1)
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _prediction(self) -> "FrozenEvidencePrediction":
        if self.subject == self.opponent:
            raise ValueError("structural mirrors are not forecast cells")
        if self.probability is not None and (
            not math.isfinite(self.probability) or not 0 <= self.probability <= 1
        ):
            raise ValueError("probability must be a finite value in [0,1]")
        if self.served and self.probability is None:
            raise ValueError("a served prediction requires an all-case probability")
        if self.interval is not None:
            low, high = self.interval
            if not all(math.isfinite(value) for value in self.interval) or not 0 <= low <= high <= 1:
                raise ValueError("prediction interval must be finite and ordered in [0,1]")
        for name in (
            "current_match_ids_sha256",
            "historical_match_ids_sha256",
            "borrowed_match_ids_sha256",
            "draw_artifact_sha256",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_sha256(name, value)
        if not self.fit_id:
            raise ValueError("fit_id must be non-empty")
        return self


class FrozenDrawSeries(_ClosedModel):
    estimator_id: EvidenceEstimatorId
    subject: str
    opponent: str
    fit_id: str
    probabilities: tuple[float, ...]

    @field_validator("probabilities")
    @classmethod
    def _finite_probabilities(cls, values: tuple[float, ...]) -> tuple[float, ...]:
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values):
            raise ValueError("joint draw probabilities must be finite values in [0,1]")
        return values


class FrozenJointDraws(_ClosedModel):
    artifact_sha256: str
    seed: int
    replicate_count: int = Field(ge=1)
    event_blocks_sha256: str
    series: tuple[FrozenDrawSeries, ...]
    draws_sha256: str

    @model_validator(mode="after")
    def _draw_identity(self) -> "FrozenJointDraws":
        _require_sha256("event_blocks_sha256", self.event_blocks_sha256)
        expected_draws = content_sha256(
            [item.model_dump(mode="json") for item in self.series]
        )
        if self.draws_sha256 != expected_draws:
            raise ValueError("joint draw value digest mismatch")
        expected_artifact = content_sha256(
            self.model_dump(mode="json", exclude={"artifact_sha256"})
        )
        if self.artifact_sha256 != expected_artifact:
            raise ValueError("joint draw artifact digest mismatch")
        if any(len(item.probabilities) != self.replicate_count for item in self.series):
            raise ValueError("joint draw series length differs from replicate_count")
        return self


class OriginForecastPayload(_ClosedModel):
    action_universe: tuple[str, ...]
    field_shares: dict[str, float]
    predictions: tuple[FrozenEvidencePrediction, ...]
    recommendation_actions: dict[EvidenceEstimatorId, str | None]
    joint_draws: FrozenJointDraws
    candidate_config_sha256: dict[EvidenceEstimatorId, str]


class OriginRefitManifest(_ClosedModel):
    fold: RecurrentBenchmarkFold
    snapshot_manifest_sha256: str
    replay_mode: ReplayMode
    stages: tuple[RefitStageArtifact, ...]
    discovery_run_id: str
    certification_run_id: str
    interval_corpus_id: str
    amplification_run_id: str
    structure_snapshot_id: str
    stage_input_sha256: dict[str, str]
    stage_config_sha256: dict[str, str]
    max_outcome_date: str
    outcome_ids_sha256: str
    outcome_columns_accessed_by_discovery: tuple[()] = ()
    status: Literal["complete", "not-evaluable", "invalid"]
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _chain_identity(self) -> "OriginRefitManifest":
        _require_sha256("snapshot_manifest_sha256", self.snapshot_manifest_sha256)
        if tuple(stage.stage for stage in self.stages) != _STAGE_ORDER:
            raise ValueError("origin manifest stages are incomplete or out of order")
        prior = self.snapshot_manifest_sha256
        for stage in self.stages:
            if stage.input_sha256 != prior:
                raise ValueError(f"origin manifest has a disconnected {stage.stage} stage")
            if stage.data_until != self.fold.data_until:
                raise ValueError(f"origin manifest {stage.stage} data clock differs from fold")
            if stage.knowledge_as_of != self.fold.knowledge_as_of:
                raise ValueError(f"origin manifest {stage.stage} knowledge clock differs from fold")
            if stage.max_outcome_date is not None and (
                stage.max_outcome_date >= self.fold.data_until
            ):
                raise ValueError(f"origin manifest {stage.stage} includes a future outcome")
            prior = stage.output_sha256
        stage_map = {stage.stage: stage for stage in self.stages}
        expected_runs = {
            "discovery": self.discovery_run_id,
            "certification": self.certification_run_id,
            "interval": self.interval_corpus_id,
            "structure": self.structure_snapshot_id,
            "amplification": self.amplification_run_id,
        }
        if any(stage_map[name].run_id != run_id for name, run_id in expected_runs.items()):
            raise ValueError("origin manifest run identities differ from stage artifacts")
        if self.stage_input_sha256 != {
            stage.stage: stage.input_sha256 for stage in self.stages
        }:
            raise ValueError("origin manifest stage-input ledger mismatch")
        if self.stage_config_sha256 != {
            stage.stage: stage.config_sha256 for stage in self.stages
        }:
            raise ValueError("origin manifest stage-config ledger mismatch")
        expected_max = max(
            (stage.max_outcome_date for stage in self.stages if stage.max_outcome_date),
            default="",
        )
        if self.max_outcome_date != expected_max:
            raise ValueError("origin manifest maximum outcome date mismatch")
        if self.outcome_ids_sha256 != content_sha256(
            [stage.outcome_ids_sha256 for stage in self.stages]
        ):
            raise ValueError("origin manifest outcome ledger mismatch")
        if self.outcome_columns_accessed_by_discovery:
            raise ValueError("origin discovery outcome-access ledger must be empty")
        if self.status == "complete" and any(stage.status != "complete" for stage in self.stages):
            raise ValueError("complete origin manifest contains an incomplete stage")
        return self


class FrozenRecurrentOrigin(_ClosedModel):
    protocol_sha256: str
    manifest: OriginRefitManifest
    action_universe: tuple[str, ...]
    field_shares: dict[str, float]
    predictions: tuple[FrozenEvidencePrediction, ...]
    recommendation_actions: dict[EvidenceEstimatorId, str | None]
    candidate_config_sha256: dict[EvidenceEstimatorId, str]
    joint_draws: FrozenJointDraws
    common_pair_universe_sha256: str
    predictions_sha256: str
    code_commit: str

    @model_validator(mode="after")
    def _sealed_identity(self) -> "FrozenRecurrentOrigin":
        _require_sha256("protocol_sha256", self.protocol_sha256)
        actions = tuple(sorted(self.action_universe))
        if self.action_universe != actions or len(actions) < 2 or len(actions) != len(set(actions)):
            raise ValueError("sealed action universe must contain at least two sorted unique actions")
        if set(self.field_shares) != set(actions):
            raise ValueError("sealed field shares must exactly cover the action universe")
        if any(not math.isfinite(value) or value < 0 for value in self.field_shares.values()):
            raise ValueError("sealed field shares must be finite and nonnegative")
        if sum(self.field_shares.values()) > 1 + 1e-12:
            raise ValueError("sealed field shares cannot exceed total field mass")
        expected_pairs = set(_prediction_pairs(actions))
        expected_keys = {
            (estimator, subject, opponent)
            for estimator in EVIDENCE_ESTIMATOR_REGISTRY
            for subject, opponent in expected_pairs
        }
        prediction_keys = {
            (item.estimator_id, item.subject, item.opponent) for item in self.predictions
        }
        if len(self.predictions) != len(expected_keys) or prediction_keys != expected_keys:
            raise ValueError("sealed predictions do not cover the exact estimator/pair grid")
        expected_prediction_sha = content_sha256(
            [item.model_dump(mode="json") for item in self.predictions]
        )
        if self.predictions_sha256 != expected_prediction_sha:
            raise ValueError("sealed prediction digest mismatch")
        expected_pair_sha = content_sha256(
            sorted(f"{left}\0{right}" for left, right in expected_pairs)
        )
        if self.common_pair_universe_sha256 != expected_pair_sha:
            raise ValueError("sealed pair-universe digest mismatch")
        draw_keys = {
            (item.estimator_id, item.subject, item.opponent)
            for item in self.joint_draws.series
        }
        if len(self.joint_draws.series) != len(expected_keys) or draw_keys != expected_keys:
            raise ValueError("sealed draws do not cover the exact estimator/pair grid")
        fits = {
            (item.estimator_id, item.subject, item.opponent): item.fit_id
            for item in self.predictions
        }
        for series in self.joint_draws.series:
            key = (series.estimator_id, series.subject, series.opponent)
            if fits[key] != series.fit_id:
                raise ValueError("sealed draw fit identity differs from prediction")
        if any(
            item.draw_artifact_sha256 != self.joint_draws.artifact_sha256
            for item in self.predictions
        ):
            raise ValueError("sealed prediction draw identity differs from joint draws")
        if set(self.recommendation_actions) != set(EVIDENCE_ESTIMATOR_REGISTRY):
            raise ValueError("sealed recommendations do not cover the exact estimator registry")
        if set(self.candidate_config_sha256) != set(EVIDENCE_ESTIMATOR_REGISTRY):
            raise ValueError("sealed configs do not cover the exact estimator registry")
        for estimator, digest in self.candidate_config_sha256.items():
            _require_sha256(f"candidate_config_sha256[{estimator}]", digest)
        if not self.code_commit:
            raise ValueError("sealed origin requires a code commit identity")
        return self


def _expected_stage_configs(protocol: RecurrentBenchmarkProtocol) -> dict[str, str]:
    return {
        "discovery": protocol.discovery_calibration_sha256,
        "certification": protocol.certification_calibration_sha256,
        "interval": protocol.interval_policy_sha256,
        "structure": protocol.structure_policy_sha256,
        "amplification": protocol.amplification_profile_sha256,
    }


def _prediction_pairs(actions: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((subject, opponent) for subject in actions for opponent in actions if subject != opponent)


def seal_recurrent_origin(
    protocol: RecurrentBenchmarkProtocol,
    fold: RecurrentBenchmarkFold,
    *,
    snapshot_manifest_sha256: str,
    stages: Sequence[RefitStageArtifact],
    forecast: OriginForecastPayload,
    code_commit: str,
) -> FrozenRecurrentOrigin:
    """Validate the complete origin-local chain and seal its immutable forecast."""
    if fold not in protocol.folds:
        raise ValueError("fold is not registered in protocol")
    _require_sha256("snapshot_manifest_sha256", snapshot_manifest_sha256)
    if tuple(stage.stage for stage in stages) != _STAGE_ORDER:
        raise ValueError(f"refit stages must exactly follow {_STAGE_ORDER}")
    expected_configs = _expected_stage_configs(protocol)
    prior = snapshot_manifest_sha256
    invalid_reasons: list[str] = []
    outcome_ids: list[str] = []
    max_dates: list[str] = []
    pair_identity: str | None = None
    for stage in stages:
        if stage.input_sha256 != prior:
            raise ValueError(f"{stage.stage} input digest does not equal prior stage output")
        if stage.config_sha256 != expected_configs[stage.stage]:
            raise ValueError(f"{stage.stage} config digest differs from protocol")
        if stage.data_until != fold.data_until:
            raise ValueError(f"{stage.stage} data clock differs from fold")
        if stage.knowledge_as_of != fold.knowledge_as_of:
            raise ValueError(f"{stage.stage} knowledge clock differs from fold")
        if stage.max_outcome_date is not None:
            if date.fromisoformat(stage.max_outcome_date) >= date.fromisoformat(fold.data_until):
                raise ValueError(f"{stage.stage} selected an outcome at or after the origin")
            max_dates.append(stage.max_outcome_date)
        if stage.stage == "discovery" and stage.outcome_columns_accessed:
            raise ValueError("discovery accessed outcome columns")
        if stage.stage in {"interval", "amplification"}:
            if stage.pair_universe_sha256 is None:
                raise ValueError(f"{stage.stage} omitted its pair-universe identity")
            if pair_identity is not None and stage.pair_universe_sha256 != pair_identity:
                raise ValueError("interval and amplification pair universes differ")
            pair_identity = stage.pair_universe_sha256
        if stage.status != "complete":
            invalid_reasons.extend(stage.reasons or (f"{stage.stage}:{stage.status}",))
        outcome_ids.append(stage.outcome_ids_sha256)
        prior = stage.output_sha256

    actions = tuple(sorted(forecast.action_universe))
    if forecast.action_universe != actions or len(actions) < 2:
        raise ValueError("action universe must contain at least two sorted unique actions")
    if set(forecast.field_shares) != set(actions):
        raise ValueError("field shares must exactly cover the frozen action universe")
    if any(not math.isfinite(value) or value < 0 for value in forecast.field_shares.values()):
        raise ValueError("field shares must be finite and nonnegative")
    if sum(forecast.field_shares.values()) > 1 + 1e-12:
        raise ValueError("field shares cannot exceed total field mass")
    expected_pairs = set(_prediction_pairs(actions))
    prediction_keys = [
        (prediction.estimator_id, prediction.subject, prediction.opponent)
        for prediction in forecast.predictions
    ]
    expected_keys = {
        (estimator, subject, opponent)
        for estimator in protocol.estimator_ids
        for subject, opponent in expected_pairs
    }
    if len(prediction_keys) != len(set(prediction_keys)) or set(prediction_keys) != expected_keys:
        raise ValueError("each estimator must freeze exactly one all-case forecast per ordered pair")
    for prediction in forecast.predictions:
        if prediction.draw_artifact_sha256 != forecast.joint_draws.artifact_sha256:
            raise ValueError("prediction draw identity differs from frozen joint draws")
        if prediction.fallback_estimator_id is not None and prediction.estimator_id in DIRECT_ESTIMATOR_IDS:
            raise ValueError("direct estimators cannot declare challenger fallback")
    draw_keys = [
        (series.estimator_id, series.subject, series.opponent) for series in forecast.joint_draws.series
    ]
    if len(draw_keys) != len(set(draw_keys)) or set(draw_keys) != expected_keys:
        raise ValueError("joint draws must exactly cover every estimator and ordered pair")
    if forecast.joint_draws.replicate_count != protocol.bootstrap_draws:
        raise ValueError("joint draw count differs from protocol")
    fits = {
        (prediction.estimator_id, prediction.subject, prediction.opponent): prediction.fit_id
        for prediction in forecast.predictions
    }
    if any(fits[key] != series.fit_id for key, series in zip(draw_keys, forecast.joint_draws.series, strict=True)):
        # The zip lookup above is order-sensitive only for traversal; each key indexes the full map.
        raise ValueError("joint draw fit identity differs from frozen prediction")
    if set(forecast.recommendation_actions) != set(protocol.estimator_ids):
        raise ValueError("recommendations must cover the exact estimator registry")
    if any(
        action is not None and action not in actions
        for action in forecast.recommendation_actions.values()
    ):
        raise ValueError("recommendation names an action outside the frozen universe")
    if set(forecast.candidate_config_sha256) != set(protocol.estimator_ids):
        raise ValueError("candidate config identities must cover the exact estimator registry")
    for estimator, digest in forecast.candidate_config_sha256.items():
        _require_sha256(f"candidate_config_sha256[{estimator}]", digest)

    ordered_predictions = tuple(
        sorted(
            forecast.predictions,
            key=lambda item: (
                protocol.estimator_ids.index(item.estimator_id), item.subject, item.opponent
            ),
        )
    )
    pair_sha = content_sha256(sorted(f"{left}\0{right}" for left, right in expected_pairs))
    if pair_identity != pair_sha:
        raise ValueError("refit pair-universe digest differs from sealed action universe")
    prediction_sha = content_sha256(
        [prediction.model_dump(mode="json") for prediction in ordered_predictions]
    )
    stage_map = {stage.stage: stage for stage in stages}
    manifest = OriginRefitManifest(
        fold=fold,
        snapshot_manifest_sha256=snapshot_manifest_sha256,
        replay_mode=protocol.replay_mode,
        stages=tuple(stages),
        discovery_run_id=stage_map["discovery"].run_id,
        certification_run_id=stage_map["certification"].run_id,
        interval_corpus_id=stage_map["interval"].run_id,
        amplification_run_id=stage_map["amplification"].run_id,
        structure_snapshot_id=stage_map["structure"].run_id,
        stage_input_sha256={stage.stage: stage.input_sha256 for stage in stages},
        stage_config_sha256={stage.stage: stage.config_sha256 for stage in stages},
        max_outcome_date=max(max_dates, default=""),
        outcome_ids_sha256=content_sha256(outcome_ids),
        status="invalid" if invalid_reasons else "complete",
        reasons=tuple(dict.fromkeys(invalid_reasons)),
    )
    return FrozenRecurrentOrigin(
        protocol_sha256=recurrent_protocol_sha256(protocol),
        manifest=manifest,
        action_universe=actions,
        field_shares=dict(sorted(forecast.field_shares.items())),
        predictions=ordered_predictions,
        recommendation_actions=dict(forecast.recommendation_actions),
        candidate_config_sha256=dict(forecast.candidate_config_sha256),
        joint_draws=forecast.joint_draws,
        common_pair_universe_sha256=pair_sha,
        predictions_sha256=prediction_sha,
        code_commit=code_commit,
    )


FutureExclusionReason = Literal[
    "outside-fold",
    "mirror",
    "bye-draw-invalid",
    "ambiguous",
    "unclassified",
    "emerging",
    "unresolved-metadata",
    "outside-universe",
]


class FutureCase(_ClosedModel):
    match_id: str
    event_id: str
    event_date: str
    subject_deck_id: str | None = None
    opponent_deck_id: str | None = None
    subject: str
    opponent: str
    subject_won: StrictBool

    @model_validator(mode="after")
    def _case_identity(self) -> "FutureCase":
        if not all((self.match_id, self.event_id, self.event_date, self.subject, self.opponent)):
            raise ValueError("future case identities must be non-empty")
        date.fromisoformat(self.event_date)
        if self.subject == self.opponent:
            raise ValueError("future cases cannot contain structural mirrors")
        return self


class FutureCaseManifest(_ClosedModel):
    protocol_sha256: str
    origin_predictions_sha256: str
    fold_id: str
    data_until: str
    evaluation_until: str
    action_universe: tuple[str, ...]
    action_universe_sha256: str
    eligible_match_ids: tuple[str, ...]
    eligible_event_ids: tuple[str, ...]
    eligible_deck_ids: tuple[str, ...]
    cases: tuple[FutureCase, ...]
    future_field_counts: dict[str, int]
    future_field_shares: dict[str, float]
    eligible_field_mass: float = Field(ge=0, le=1)
    total_future_decks: int = Field(ge=0)
    case_sha256: str
    field_mass_sha256: str
    exclusions: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _manifest_identity(self) -> "FutureCaseManifest":
        for name in (
            "protocol_sha256",
            "origin_predictions_sha256",
            "action_universe_sha256",
            "case_sha256",
            "field_mass_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        actions = tuple(sorted(self.action_universe))
        if self.action_universe != actions or len(actions) < 2 or len(actions) != len(set(actions)):
            raise ValueError("case action universe must contain at least two sorted unique actions")
        if self.action_universe_sha256 != content_sha256(actions):
            raise ValueError("case action universe digest mismatch")
        cases = tuple(sorted(self.cases, key=lambda item: item.match_id))
        if self.cases != cases or len(cases) != len({item.match_id for item in cases}):
            raise ValueError("future cases must have sorted unique match ids")
        if not all(self.data_until <= item.event_date < self.evaluation_until for item in cases):
            raise ValueError("future case lies outside the exact evaluation horizon")
        expected_matches = tuple(item.match_id for item in cases)
        expected_events = tuple(sorted({item.event_id for item in cases}))
        expected_decks = tuple(sorted({
            deck_id
            for item in cases
            for deck_id in (item.subject_deck_id, item.opponent_deck_id)
            if deck_id is not None
        }))
        if self.eligible_match_ids != expected_matches:
            raise ValueError("eligible match ids differ from future cases")
        if self.eligible_event_ids != expected_events:
            raise ValueError("eligible event ids differ from future cases")
        if self.eligible_deck_ids != expected_decks:
            raise ValueError("eligible deck ids differ from future cases")
        if self.case_sha256 != content_sha256(
            [item.model_dump(mode="json") for item in cases]
        ):
            raise ValueError("future case manifest digest mismatch")
        if any(not isinstance(count, int) or isinstance(count, bool) or count < 0
               for count in self.future_field_counts.values()):
            raise ValueError("future field counts must be nonnegative integers")
        total = sum(self.future_field_counts.values())
        if self.total_future_decks != total:
            raise ValueError("future field total differs from field counts")
        expected_shares = {
            action: self.future_field_counts.get(action, 0) / total if total else 0.0
            for action in actions
        }
        if self.future_field_shares != expected_shares:
            raise ValueError("future field shares differ from unrenormalized counts")
        if not math.isclose(
            self.eligible_field_mass, sum(expected_shares.values()), abs_tol=1e-12
        ):
            raise ValueError("eligible field mass differs from unrenormalized shares")
        field_payload = {
            "counts": dict(sorted(self.future_field_counts.items())),
            "shares": expected_shares,
            "total": total,
            "action_universe": actions,
        }
        if self.field_mass_sha256 != content_sha256(field_payload):
            raise ValueError("future field-mass digest mismatch")
        if any(
            reason not in FutureExclusionReason.__args__
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
            for reason, count in self.exclusions.items()
        ):
            raise ValueError("future exclusions must use typed reasons and nonnegative counts")
        return self


def _row_identity(row: Mapping[str, object]) -> bytes:
    return json.dumps(
        dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode()


def build_future_case_manifest(
    origin: FrozenRecurrentOrigin,
    rows: Sequence[Mapping[str, object]],
    *,
    protocol: RecurrentBenchmarkProtocol,
    future_field_counts: Mapping[str, int],
) -> FutureCaseManifest:
    """Build one estimator-independent, horizon-bound future-case ledger."""
    if origin.protocol_sha256 != recurrent_protocol_sha256(protocol):
        raise ValueError("origin protocol identity differs from evaluation protocol")
    fold = origin.manifest.fold
    registered = next((item for item in protocol.folds if item.fold_id == fold.fold_id), None)
    if registered != fold:
        raise ValueError("origin fold differs from exact protocol fold")
    seen: dict[str, bytes] = {}
    cases: list[FutureCase] = []
    exclusions: Counter[str] = Counter()
    action_set = set(origin.action_universe)
    for row in sorted(rows, key=lambda item: (str(item.get("match_id", "")), _row_identity(item))):
        match_id = str(row.get("match_id", ""))
        if not match_id:
            raise ValueError("future row is missing match_id")
        identity = _row_identity(row)
        if match_id in seen:
            if seen[match_id] != identity:
                raise ValueError(f"future match id {match_id!r} has conflicting rows")
            raise ValueError(f"future match id {match_id!r} is duplicated")
        seen[match_id] = identity
        event_date = str(row.get("event_date", ""))[:10]
        subject = row.get("subject")
        opponent = row.get("opponent")
        explicit = row.get("exclusion_reason")
        reason: str | None = str(explicit) if explicit else None
        if not reason and (not event_date or not fold.data_until <= event_date < fold.evaluation_until):
            reason = "outside-fold"
        elif not reason and (subject is None or opponent is None):
            reason = "unclassified"
        elif not reason and str(subject) == str(opponent):
            reason = "mirror"
        elif not reason and row.get("subject_won") is None:
            reason = "bye-draw-invalid"
        elif not reason and (str(subject) not in action_set or str(opponent) not in action_set):
            reason = "outside-universe"
        if reason:
            if reason not in FutureExclusionReason.__args__:
                raise ValueError(f"unknown future exclusion reason {reason!r}")
            exclusions[reason] += 1
            continue
        if not isinstance(row["subject_won"], bool):
            raise ValueError("future subject_won must be a boolean for decisive matches")
        cases.append(
            FutureCase(
                match_id=match_id,
                event_id=str(row["event_id"]),
                event_date=event_date,
                subject_deck_id=(
                    None if row.get("subject_deck_id") is None else str(row["subject_deck_id"])
                ),
                opponent_deck_id=(
                    None if row.get("opponent_deck_id") is None else str(row["opponent_deck_id"])
                ),
                subject=str(subject),
                opponent=str(opponent),
                subject_won=bool(row["subject_won"]),
            )
        )
    cases_tuple = tuple(sorted(cases, key=lambda item: item.match_id))
    match_ids = tuple(item.match_id for item in cases_tuple)
    event_ids = tuple(sorted({item.event_id for item in cases_tuple}))
    deck_ids = tuple(
        sorted(
            {
                deck_id
                for item in cases_tuple
                for deck_id in (item.subject_deck_id, item.opponent_deck_id)
                if deck_id is not None
            }
        )
    )
    if any(not isinstance(count, int) or count < 0 for count in future_field_counts.values()):
        raise ValueError("future field counts must be nonnegative integers")
    total_decks = sum(future_field_counts.values())
    shares = {
        action: future_field_counts.get(action, 0) / total_decks if total_decks else 0.0
        for action in origin.action_universe
    }
    field_payload = {
        "counts": dict(sorted(future_field_counts.items())),
        "shares": shares,
        "total": total_decks,
        "action_universe": origin.action_universe,
    }
    case_payload = [item.model_dump(mode="json") for item in cases_tuple]
    return FutureCaseManifest(
        protocol_sha256=origin.protocol_sha256,
        origin_predictions_sha256=origin.predictions_sha256,
        fold_id=fold.fold_id,
        data_until=fold.data_until,
        evaluation_until=fold.evaluation_until,
        action_universe=origin.action_universe,
        action_universe_sha256=content_sha256(origin.action_universe),
        eligible_match_ids=match_ids,
        eligible_event_ids=event_ids,
        eligible_deck_ids=deck_ids,
        cases=cases_tuple,
        future_field_counts=dict(sorted(future_field_counts.items())),
        future_field_shares=shares,
        eligible_field_mass=sum(shares.values()),
        total_future_decks=total_decks,
        case_sha256=content_sha256(case_payload),
        field_mass_sha256=content_sha256(field_payload),
        exclusions=dict(sorted(exclusions.items())),
    )


class PredictiveMetrics(_ClosedModel):
    estimator_id: EvidenceEstimatorId
    common_matches: int
    common_events: int
    log_loss: float | None
    brier: float | None
    calibration_intercept: float | None = None
    calibration_slope: float | None = None
    cumulative_calibration_error: float | None = None
    interval_coverage: float | None = None
    interval_mean_width: float | None = None
    interval_score: float | None = None
    served_match_coverage: float
    served_event_coverage: float
    served_field_coverage: float
    refusal_counts: dict[str, int] = Field(default_factory=dict)
    imputation_counts: dict[str, int] = Field(default_factory=dict)
    evidence_concentration: dict[str, float | None] = Field(default_factory=dict)
    status: EvaluationStatus
    reasons: tuple[str, ...] = ()


class EventPredictiveEvidence(_ClosedModel):
    estimator_id: EvidenceEstimatorId
    event_id: str
    matches: int
    log_loss: float
    brier: float
    calibration_error: float
    interval_covered: bool
    interval_width: float
    interval_score: float
    served: bool


class OriginPredictiveEvaluation(_ClosedModel):
    protocol_sha256: str
    origin_predictions_sha256: str
    future_cases: FutureCaseManifest
    metrics: tuple[PredictiveMetrics, ...]
    event_evidence: tuple[EventPredictiveEvidence, ...]
    paired_event_differences: dict[str, dict[str, tuple[float, ...]]] = Field(
        default_factory=dict
    )
    status: EvaluationStatus
    reasons: tuple[str, ...] = ()


def _calibration(
    probabilities: np.ndarray,
    outcomes: np.ndarray,
    minimum: int,
) -> tuple[float | None, float | None, float | None]:
    order = np.argsort(probabilities, kind="stable")
    cumulative = np.cumsum(outcomes[order] - probabilities[order])
    error = float(np.max(np.abs(cumulative)) / len(probabilities)) if len(probabilities) else None
    if len(probabilities) < minimum or len(set(outcomes.tolist())) < 2:
        return None, None, error
    clipped = np.clip(probabilities, 1e-8, 1 - 1e-8)
    logits = np.log(clipped / (1 - clipped))
    if float(np.ptp(logits)) == 0:
        return None, None, error
    design = np.column_stack((np.ones(len(logits)), logits))
    coefficients = np.array([0.0, 1.0])
    for _ in range(50):
        linear = design @ coefficients
        fitted = 1 / (1 + np.exp(-np.clip(linear, -30, 30)))
        weights = np.clip(fitted * (1 - fitted), 1e-8, None)
        hessian = design.T @ (weights[:, None] * design)
        score = design.T @ (outcomes - fitted)
        try:
            step = np.linalg.solve(hessian, score)
        except np.linalg.LinAlgError:
            return None, None, error
        coefficients += step
        if float(np.max(np.abs(step))) < 1e-10:
            break
    if not np.all(np.isfinite(coefficients)):
        return None, None, error
    return float(coefficients[0]), float(coefficients[1]), error


def _stable_uniform(*parts: object) -> float:
    payload = "\0".join(map(str, parts)).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") / 2**64


def _interval_score(observed: float, low: float, high: float, alpha: float) -> float:
    score = high - low
    if observed < low:
        score += (2 / alpha) * (low - observed)
    elif observed > high:
        score += (2 / alpha) * (observed - high)
    return score


def _support_reasons(cases: FutureCaseManifest, protocol: RecurrentBenchmarkProtocol) -> list[str]:
    reasons: list[str] = []
    if len(cases.cases) < protocol.support.min_common_matches:
        reasons.append(
            f"common decisive matches {len(cases.cases)} < {protocol.support.min_common_matches}"
        )
    if len(cases.eligible_event_ids) < protocol.support.min_events:
        reasons.append(f"events {len(cases.eligible_event_ids)} < {protocol.support.min_events}")
    event_dates = {case.event_date for case in cases.cases}
    if len(event_dates) < protocol.support.min_event_dates:
        reasons.append(f"event dates {len(event_dates)} < {protocol.support.min_event_dates}")
    if cases.eligible_field_mass < protocol.support.min_future_field_coverage:
        reasons.append(
            f"future field coverage {cases.eligible_field_mass:.3f} < "
            f"{protocol.support.min_future_field_coverage:.3f}"
        )
    return reasons


def _validate_evaluation_binding(
    origin: FrozenRecurrentOrigin,
    cases: FutureCaseManifest,
    protocol: RecurrentBenchmarkProtocol,
) -> None:
    # Revalidate serialized values so unchecked ``model_copy`` mutations cannot bypass
    # the content identities at this outcome-opening boundary.
    FutureCaseManifest.model_validate(cases.model_dump(mode="json"))
    if origin.protocol_sha256 != recurrent_protocol_sha256(protocol):
        raise ValueError("origin protocol identity differs from evaluation protocol")
    if cases.protocol_sha256 != origin.protocol_sha256:
        raise ValueError("case protocol identity differs from origin")
    if cases.origin_predictions_sha256 != origin.predictions_sha256:
        raise ValueError("case manifest is bound to different origin predictions")
    fold = origin.manifest.fold
    if (
        cases.fold_id != fold.fold_id
        or cases.data_until != fold.data_until
        or cases.evaluation_until != fold.evaluation_until
    ):
        raise ValueError("case manifest fold or horizon differs from origin")
    if cases.action_universe != origin.action_universe or (
        cases.action_universe_sha256 != content_sha256(origin.action_universe)
    ):
        raise ValueError("case action universe differs from origin")


def evaluate_recurrent_predictions(
    origin: FrozenRecurrentOrigin,
    cases: FutureCaseManifest,
    *,
    protocol: RecurrentBenchmarkProtocol,
) -> OriginPredictiveEvaluation:
    """Score every estimator on the same frozen cases and event blocks."""
    _validate_evaluation_binding(origin, cases, protocol)
    if origin.manifest.status != "complete":
        reason = "origin refit manifest is not complete"
    else:
        reason = ""
    support_reasons = _support_reasons(cases, protocol)
    prediction_lookup = {
        (item.estimator_id, item.subject, item.opponent): item for item in origin.predictions
    }
    draw_lookup = {
        (item.estimator_id, item.subject, item.opponent): item
        for item in origin.joint_draws.series
    }
    by_event: dict[str, list[FutureCase]] = {}
    for case in cases.cases:
        by_event.setdefault(case.event_id, []).append(case)
    metrics: list[PredictiveMetrics] = []
    event_evidence: list[EventPredictiveEvidence] = []
    per_estimator_events: dict[str, dict[str, EventPredictiveEvidence]] = {}
    alpha = 1 - protocol.interval_level
    for estimator in protocol.estimator_ids:
        probabilities: list[float] = []
        outcomes: list[float] = []
        case_predictions: list[FrozenEvidencePrediction] = []
        missing = False
        for case in cases.cases:
            prediction = prediction_lookup.get((estimator, case.subject, case.opponent))
            if prediction is None or prediction.probability is None:
                missing = True
                continue
            probabilities.append(prediction.probability)
            outcomes.append(float(case.subject_won))
            case_predictions.append(prediction)
        invalid_reasons = list(filter(None, (reason,)))
        if missing or len(probabilities) != len(cases.cases):
            invalid_reasons.append("missing-all-case-prediction")
        event_rows: dict[str, EventPredictiveEvidence] = {}
        interval_values: list[tuple[bool, float, float]] = []
        if not invalid_reasons:
            for event_id in sorted(by_event):
                event_cases = by_event[event_id]
                event_p = np.asarray(
                    [prediction_lookup[(estimator, case.subject, case.opponent)].probability for case in event_cases],
                    dtype=float,
                )
                event_y = np.asarray([float(case.subject_won) for case in event_cases])
                clipped = np.clip(event_p, protocol.log_clip_epsilon, 1 - protocol.log_clip_epsilon)
                event_losses = -(event_y * np.log(clipped) + (1 - event_y) * np.log(1 - clipped))
                event_brier = (event_p - event_y) ** 2
                predictive_rates: list[float] = []
                for replicate in range(protocol.bootstrap_draws):
                    wins = 0
                    for case in event_cases:
                        draws = draw_lookup[(estimator, case.subject, case.opponent)].probabilities
                        p = draws[replicate]
                        wins += _stable_uniform(protocol.seed, estimator, event_id, replicate, case.match_id) < p
                    predictive_rates.append(wins / len(event_cases))
                low, high = np.quantile(predictive_rates, [alpha / 2, 1 - alpha / 2])
                observed = float(np.mean(event_y))
                covered = bool(low <= observed <= high)
                width = float(high - low)
                score = _interval_score(observed, float(low), float(high), alpha)
                served = all(
                    prediction_lookup[(estimator, case.subject, case.opponent)].served
                    for case in event_cases
                )
                evidence = EventPredictiveEvidence(
                    estimator_id=estimator,
                    event_id=event_id,
                    matches=len(event_cases),
                    log_loss=float(np.mean(event_losses)),
                    brier=float(np.mean(event_brier)),
                    calibration_error=abs(float(np.mean(event_y - event_p))),
                    interval_covered=covered,
                    interval_width=width,
                    interval_score=score,
                    served=served,
                )
                event_rows[event_id] = evidence
                event_evidence.append(evidence)
                interval_values.append((covered, width, score))
        per_estimator_events[estimator] = event_rows
        if invalid_reasons:
            metrics.append(
                PredictiveMetrics(
                    estimator_id=estimator,
                    common_matches=len(probabilities),
                    common_events=len(event_rows),
                    log_loss=None,
                    brier=None,
                    served_match_coverage=0.0,
                    served_event_coverage=0.0,
                    served_field_coverage=0.0,
                    status="invalid",
                    reasons=tuple(invalid_reasons),
                )
            )
            continue
        p = np.asarray(probabilities, dtype=float)
        y = np.asarray(outcomes, dtype=float)
        clipped = np.clip(p, protocol.log_clip_epsilon, 1 - protocol.log_clip_epsilon)
        log_loss = float(np.mean(-(y * np.log(clipped) + (1 - y) * np.log(1 - clipped))))
        brier = float(np.mean((p - y) ** 2))
        intercept, slope, calibration_error = _calibration(
            p, y, protocol.support.min_calibration_matches
        )
        served_cases = [prediction.served for prediction in case_predictions]
        served_actions = {
            action
            for action in origin.action_universe
            if all(
                prediction_lookup[(estimator, action, opponent)].served
                for opponent in origin.action_universe
                if opponent != action
            )
        }
        refusals = Counter(
            reason
            for prediction in case_predictions
            if not prediction.served
            for reason in (prediction.reasons or ("unserved",))
        )
        imputation = Counter(prediction.imputation for prediction in case_predictions)
        concentration: dict[str, float | None] = {}
        for name in (
            "event_concentration",
            "source_concentration",
            "component_concentration",
            "donor_concentration",
            "effective_support",
        ):
            values = [getattr(prediction, name) for prediction in case_predictions]
            finite = [value for value in values if value is not None]
            concentration[name] = max(finite) if finite and name != "effective_support" else (
                min(finite) if finite else None
            )
        metric_reasons = list(support_reasons)
        if intercept is None or slope is None:
            metric_reasons.append("calibration-support-insufficient")
        status: EvaluationStatus = "support-censored" if metric_reasons else "complete"
        metrics.append(
            PredictiveMetrics(
                estimator_id=estimator,
                common_matches=len(cases.cases),
                common_events=len(event_rows),
                log_loss=log_loss,
                brier=brier,
                calibration_intercept=intercept,
                calibration_slope=slope,
                cumulative_calibration_error=calibration_error,
                interval_coverage=(
                    sum(value[0] for value in interval_values) / len(interval_values)
                    if interval_values
                    else None
                ),
                interval_mean_width=(
                    sum(value[1] for value in interval_values) / len(interval_values)
                    if interval_values
                    else None
                ),
                interval_score=(
                    sum(value[2] for value in interval_values) / len(interval_values)
                    if interval_values
                    else None
                ),
                served_match_coverage=(sum(served_cases) / len(served_cases) if served_cases else 0.0),
                served_event_coverage=(
                    sum(row.served for row in event_rows.values()) / len(event_rows)
                    if event_rows
                    else 0.0
                ),
                served_field_coverage=sum(
                    cases.future_field_shares.get(action, 0.0) for action in served_actions
                ),
                refusal_counts=dict(sorted(refusals.items())),
                imputation_counts=dict(sorted(imputation.items())),
                evidence_concentration=concentration,
                status=status,
                reasons=tuple(metric_reasons),
            )
        )
    metric_lookup = {metric.estimator_id: metric for metric in metrics}
    paired: dict[str, dict[str, tuple[float, ...]]] = {}
    for candidate in EVIDENCE_ESTIMATOR_REGISTRY[2:]:
        for comparator in _comparators_for(candidate):
            key = f"{candidate}|{comparator}"
            candidate_events = per_estimator_events[candidate]
            comparator_events = per_estimator_events[comparator]
            common_events = sorted(set(candidate_events) & set(comparator_events))
            paired[key] = {
                "log_loss": tuple(
                    candidate_events[event].log_loss - comparator_events[event].log_loss
                    for event in common_events
                ),
                "brier": tuple(
                    candidate_events[event].brier - comparator_events[event].brier
                    for event in common_events
                ),
                "calibration": tuple(
                    candidate_events[event].calibration_error
                    - comparator_events[event].calibration_error
                    for event in common_events
                ),
                "interval_score": tuple(
                    candidate_events[event].interval_score
                    - comparator_events[event].interval_score
                    for event in common_events
                ),
                "served_event_coverage": tuple(
                    float(candidate_events[event].served) - float(comparator_events[event].served)
                    for event in common_events
                ),
                "served_field_coverage": (
                    metric_lookup[candidate].served_field_coverage
                    - metric_lookup[comparator].served_field_coverage,
                ),
                "interval_coverage": tuple(
                    float(candidate_events[event].interval_covered) for event in common_events
                ),
            }
    status: EvaluationStatus
    if any(metric.status == "invalid" for metric in metrics):
        status = "invalid"
    elif any(metric.status == "support-censored" for metric in metrics):
        status = "support-censored"
    else:
        status = "complete"
    return OriginPredictiveEvaluation(
        protocol_sha256=origin.protocol_sha256,
        origin_predictions_sha256=origin.predictions_sha256,
        future_cases=cases,
        metrics=tuple(metrics),
        event_evidence=tuple(
            sorted(event_evidence, key=lambda item: (protocol.estimator_ids.index(item.estimator_id), item.event_id))
        ),
        paired_event_differences=paired,
        status=status,
        reasons=tuple(dict.fromkeys(reason for metric in metrics for reason in metric.reasons)),
    )


DecisionCensor = Literal[
    "insufficient-support",
    "practical-tie",
    "unstable-oracle",
    "missing-action",
    "invalid-joint-draws",
]


class DecisionEvaluation(_ClosedModel):
    estimator_id: EvidenceEstimatorId
    requested_action: str | None = None
    frozen_action: str | None
    fallback_used: bool
    future_oracle_actions: tuple[str, ...]
    realized_utility: float | None
    regret: float | None
    regret_interval: tuple[float, float] | None = None
    top_k_hit: bool | None = None
    event_blocks: int
    censor_reason: DecisionCensor | None = None
    regret_draws: tuple[float, ...] = ()
    reasons: tuple[str, ...] = ()


class OriginDecisionEvaluation(_ClosedModel):
    protocol_sha256: str
    origin_predictions_sha256: str
    case_sha256: str
    fold_id: str
    field_mass_sha256: str
    action_universe_sha256: str
    evaluations: tuple[DecisionEvaluation, ...]
    paired_regret_differences: dict[str, dict[str, tuple[float, ...]]] = Field(
        default_factory=dict
    )
    status: EvaluationStatus
    reasons: tuple[str, ...] = ()


def _realized_utilities(
    cases: Sequence[FutureCase],
    actions: Sequence[str],
    field_shares: Mapping[str, float],
) -> tuple[dict[str, float], dict[str, int]]:
    wins: Counter[tuple[str, str]] = Counter()
    totals: Counter[tuple[str, str]] = Counter()
    action_matches: Counter[str] = Counter()
    for case in cases:
        for subject, opponent, won in (
            (case.subject, case.opponent, case.subject_won),
            (case.opponent, case.subject, not case.subject_won),
        ):
            totals[(subject, opponent)] += 1
            wins[(subject, opponent)] += int(won)
            action_matches[subject] += 1
    utilities: dict[str, float] = {}
    for action in actions:
        utility = 0.5 * field_shares.get(action, 0.0)
        for opponent in actions:
            if opponent == action:
                continue
            count = totals[(action, opponent)]
            if count:
                utility += field_shares.get(opponent, 0.0) * wins[(action, opponent)] / count
        utilities[action] = utility
    return utilities, dict(action_matches)


def _action_is_served(
    origin: FrozenRecurrentOrigin,
    estimator: EvidenceEstimatorId,
    action: str | None,
) -> bool:
    if action is None:
        return False
    return all(
        prediction.served
        for prediction in origin.predictions
        if prediction.estimator_id == estimator and prediction.subject == action
    )


def evaluate_recurrent_decisions(
    origin: FrozenRecurrentOrigin,
    cases: FutureCaseManifest,
    *,
    protocol: RecurrentBenchmarkProtocol,
) -> OriginDecisionEvaluation:
    """Replay one frozen action rule and shared whole-event oracle for every estimator."""
    _validate_evaluation_binding(origin, cases, protocol)
    support_reasons = _support_reasons(cases, protocol)
    if origin.joint_draws.replicate_count != protocol.bootstrap_draws:
        draw_invalid = True
    else:
        draw_invalid = False
    current_action = origin.recommendation_actions.get("current-only-v1")
    requested_actions = dict(origin.recommendation_actions)
    executed: dict[EvidenceEstimatorId, str | None] = {}
    fallback: dict[EvidenceEstimatorId, bool] = {}
    for estimator in protocol.estimator_ids:
        requested = requested_actions.get(estimator)
        use_fallback = estimator != "current-only-v1" and not _action_is_served(
            origin, estimator, requested
        )
        executed[estimator] = current_action if use_fallback else requested
        fallback[estimator] = use_fallback
    point_utilities, action_matches = _realized_utilities(
        cases.cases, origin.action_universe, cases.future_field_shares
    )
    supported = {
        action: value
        for action, value in point_utilities.items()
        if action_matches.get(action, 0) >= protocol.support.min_action_matches
    }
    ordered = tuple(sorted(supported, key=lambda action: (-supported[action], action)))
    practical_tie = (
        len(ordered) > 1
        and supported[ordered[0]] - supported[ordered[1]]
        <= protocol.margins.oracle_practical_tie_margin
    )
    event_blocks: dict[str, list[FutureCase]] = {}
    for case in cases.cases:
        event_blocks.setdefault(case.event_id, []).append(case)
    event_ids = tuple(sorted(event_blocks))
    rng = np.random.default_rng(protocol.seed)
    sampled_blocks = tuple(
        tuple(str(value) for value in rng.choice(event_ids, size=len(event_ids), replace=True))
        if event_ids
        else ()
        for _ in range(protocol.bootstrap_draws)
    )
    replicate_oracles: list[str] = []
    regret_draws: dict[EvidenceEstimatorId, list[float]] = {
        estimator: [] for estimator in protocol.estimator_ids
    }
    for block in sampled_blocks:
        sample = [case for event_id in block for case in event_blocks[event_id]]
        utilities, matches = _realized_utilities(
            sample, origin.action_universe, cases.future_field_shares
        )
        sample_supported = {
            action: value
            for action, value in utilities.items()
            if matches.get(action, 0) >= protocol.support.min_action_matches
        }
        if len(sample_supported) < protocol.support.min_supported_actions:
            continue
        oracle = min(sample_supported, key=lambda action: (-sample_supported[action], action))
        replicate_oracles.append(oracle)
        for estimator, action in executed.items():
            if action in sample_supported:
                regret_draws[estimator].append(sample_supported[oracle] - sample_supported[action])
    stable_share = (
        Counter(replicate_oracles).most_common(1)[0][1] / len(replicate_oracles)
        if replicate_oracles
        else 0.0
    )
    evaluations: list[DecisionEvaluation] = []
    for estimator in protocol.estimator_ids:
        action = executed[estimator]
        censor: DecisionCensor | None = None
        reasons = list(support_reasons)
        if draw_invalid:
            censor = "invalid-joint-draws"
        elif action is None or current_action is None and fallback[estimator]:
            censor = "missing-action"
        elif reasons or len(supported) < protocol.support.min_supported_actions:
            censor = "insufficient-support"
        elif practical_tie:
            censor = "practical-tie"
        elif stable_share < protocol.margins.min_oracle_stability:
            censor = "unstable-oracle"
        draws = tuple(regret_draws[estimator])
        if not draws and censor is None:
            censor = "unstable-oracle"
        if censor is not None:
            regret = realized = interval = top_k = None
            reasons.append(censor)
        else:
            oracle = ordered[0]
            realized = supported[action]  # type: ignore[index]
            regret = supported[oracle] - realized
            low, high = np.quantile(draws, [protocol.margins.alpha / 2, 1 - protocol.margins.alpha / 2])
            interval = (float(low), float(high))
            top_k = action in ordered[: min(3, len(ordered))]
        if fallback[estimator]:
            reasons.append(
                f"refused {requested_actions.get(estimator)!r}; executed current-only action {current_action!r}"
            )
        evaluations.append(
            DecisionEvaluation(
                estimator_id=estimator,
                requested_action=requested_actions.get(estimator),
                frozen_action=action,
                fallback_used=fallback[estimator],
                future_oracle_actions=tuple(replicate_oracles),
                realized_utility=realized,
                regret=regret,
                regret_interval=interval,
                top_k_hit=top_k,
                event_blocks=len(event_ids),
                censor_reason=censor,
                regret_draws=draws,
                reasons=tuple(dict.fromkeys(reasons)),
            )
        )
    by_estimator = {item.estimator_id: item for item in evaluations}
    paired: dict[str, dict[str, tuple[float, ...]]] = {}
    for candidate in EVIDENCE_ESTIMATOR_REGISTRY[2:]:
        for comparator in _comparators_for(candidate):
            left = by_estimator[candidate].regret_draws
            right = by_estimator[comparator].regret_draws
            count = min(len(left), len(right))
            paired[f"{candidate}|{comparator}"] = {
                "regret": tuple(left[index] - right[index] for index in range(count))
            }
    if draw_invalid or origin.manifest.status == "invalid":
        status: EvaluationStatus = "invalid"
    elif any(item.censor_reason for item in evaluations):
        status = "support-censored"
    else:
        status = "complete"
    return OriginDecisionEvaluation(
        protocol_sha256=origin.protocol_sha256,
        origin_predictions_sha256=origin.predictions_sha256,
        case_sha256=cases.case_sha256,
        fold_id=origin.manifest.fold.fold_id,
        field_mass_sha256=cases.field_mass_sha256,
        action_universe_sha256=content_sha256(origin.action_universe),
        evaluations=tuple(evaluations),
        paired_regret_differences=paired,
        status=status,
        reasons=tuple(dict.fromkeys(reason for item in evaluations for reason in item.reasons)),
    )


class GateClause(_ClosedModel):
    clause_id: str
    comparator_id: EvidenceEstimatorId
    metric: str
    estimate: float | None
    lower_bound: float | None
    upper_bound: float | None
    threshold: float
    status: Literal["pass", "fail", "inconclusive", "censored", "invalid"]
    reasons: tuple[str, ...] = ()


class PromotionAssessment(_ClosedModel):
    protocol_sha256: str
    candidate_id: EvidenceEstimatorId
    candidate_config_sha256: str
    comparator_ids: tuple[EvidenceEstimatorId, ...]
    origin_evaluation_ids: tuple[str, ...]
    clauses: tuple[GateClause, ...]
    useful_coverage: bool | None
    predictive_non_degradation: bool | None
    interval_non_degradation: bool | None
    decision_non_degradation: bool | None
    status: PromotionStatus
    authority: Literal["evidence-only"] = "evidence-only"
    reasons: tuple[str, ...] = ()


class OperatorPromotionProposal(_ClosedModel):
    proposal_id: str
    protocol_sha256: str
    candidate_id: EvidenceEstimatorId
    candidate_config_sha256: str
    assessment_sha256: str
    target_config_version: str
    authority: Literal["operator-review-required"] = "operator-review-required"


def _comparators_for(candidate: EvidenceEstimatorId) -> tuple[EvidenceEstimatorId, ...]:
    if candidate == "recurrent-expanded-v1":
        return ("current-only-v1", "contiguous-era-v1")
    if candidate in AMPLIFICATION_METHOD_IDS:
        return ("current-only-v1", "recurrent-expanded-v1")
    return ()


def _quantile_bounds(values: Sequence[float], alpha: float) -> tuple[float, float, float]:
    array = np.asarray(tuple(values), dtype=float)
    if not len(array) or not np.all(np.isfinite(array)):
        raise ValueError("paired evidence must contain finite values")
    return (
        float(np.mean(array)),
        float(np.quantile(array, alpha)),
        float(np.quantile(array, 1 - alpha)),
    )


def _classify_clause(
    *,
    clause_id: str,
    comparator: EvidenceEstimatorId,
    metric: str,
    values: Sequence[float],
    threshold: float,
    direction: Literal["minimum", "maximum"],
    alpha: float,
    forced: Literal["invalid", "censored"] | None = None,
) -> GateClause:
    if forced is not None:
        return GateClause(
            clause_id=clause_id,
            comparator_id=comparator,
            metric=metric,
            estimate=None,
            lower_bound=None,
            upper_bound=None,
            threshold=threshold,
            status=forced,
            reasons=(f"{forced} evidence",),
        )
    if not values:
        return GateClause(
            clause_id=clause_id,
            comparator_id=comparator,
            metric=metric,
            estimate=None,
            lower_bound=None,
            upper_bound=None,
            threshold=threshold,
            status="censored",
            reasons=("paired evidence is absent",),
        )
    estimate, low, high = _quantile_bounds(values, alpha)
    if direction == "minimum":
        status = "pass" if low >= threshold else "fail" if high < threshold else "inconclusive"
    else:
        status = "pass" if high <= threshold else "fail" if low > threshold else "inconclusive"
    return GateClause(
        clause_id=clause_id,
        comparator_id=comparator,
        metric=metric,
        estimate=estimate,
        lower_bound=low,
        upper_bound=high,
        threshold=threshold,
        status=status,
    )


def _category_value(clauses: Sequence[GateClause]) -> bool | None:
    if any(clause.status == "fail" for clause in clauses):
        return False
    if clauses and all(clause.status == "pass" for clause in clauses):
        return True
    return None


def aggregate_recurrent_validation(
    predictive_evaluations: Sequence[OriginPredictiveEvaluation],
    decision_evaluations: Sequence[OriginDecisionEvaluation],
    *,
    protocol: RecurrentBenchmarkProtocol,
    candidate_id: EvidenceEstimatorId,
    candidate_config_sha256: str,
) -> PromotionAssessment:
    """Evaluate the complete simultaneous useful-coverage/non-degradation conjunction."""
    comparators = _comparators_for(candidate_id)
    if not comparators:
        raise ValueError(f"{candidate_id!r} is not a challenger candidate")
    _require_sha256("candidate_config_sha256", candidate_config_sha256)
    protocol_hash = recurrent_protocol_sha256(protocol)
    predictive_by_fold = {item.future_cases.fold_id: item for item in predictive_evaluations}
    decision_by_fold = {item.fold_id: item for item in decision_evaluations}
    if len(predictive_by_fold) != len(predictive_evaluations) or len(decision_by_fold) != len(decision_evaluations):
        raise ValueError("each outer outcome may be consumed exactly once")
    if set(predictive_by_fold) != set(decision_by_fold):
        raise ValueError("predictive and decision evaluations must cover identical folds")
    for fold_id in predictive_by_fold:
        predictive = predictive_by_fold[fold_id]
        decision = decision_by_fold[fold_id]
        if predictive.origin_predictions_sha256 != decision.origin_predictions_sha256:
            raise ValueError(f"predictive and decision origin identities differ for {fold_id}")
        if predictive.future_cases.case_sha256 != decision.case_sha256:
            raise ValueError(f"predictive and decision case identities differ for {fold_id}")
        if predictive.future_cases.field_mass_sha256 != decision.field_mass_sha256:
            raise ValueError(f"predictive and decision field identities differ for {fold_id}")
        if predictive.future_cases.action_universe_sha256 != decision.action_universe_sha256:
            raise ValueError(f"predictive and decision action identities differ for {fold_id}")
    invalid = any(
        item.protocol_sha256 != protocol_hash or item.status == "invalid"
        for item in (*predictive_evaluations, *decision_evaluations)
    )
    folds = [fold for fold in protocol.folds if fold.fold_id in predictive_by_fold]
    censored = (
        len(folds) < protocol.support.min_origins
        or len({fold.regime_id for fold in folds}) < protocol.support.min_regimes
        or any(
            item.status == "support-censored"
            for item in (*predictive_evaluations, *decision_evaluations)
        )
    )
    forced: Literal["invalid", "censored"] | None = "invalid" if invalid else "censored" if censored else None
    required_metric_count = len(EVIDENCE_ESTIMATOR_REGISTRY[2:]) * 2 * 8
    simultaneous_alpha = protocol.margins.alpha / required_metric_count
    clauses: list[GateClause] = []
    specifications = (
        ("served-field-gain", "served_field_coverage", protocol.margins.min_served_field_coverage_gain, "minimum", "coverage"),
        ("served-event-gain", "served_event_coverage", protocol.margins.min_served_event_coverage_gain, "minimum", "coverage"),
        ("log-loss-nondegradation", "log_loss", protocol.margins.max_log_loss_delta, "maximum", "predictive"),
        ("brier-nondegradation", "brier", protocol.margins.max_brier_delta, "maximum", "predictive"),
        ("calibration-nondegradation", "calibration", protocol.margins.max_calibration_delta, "maximum", "predictive"),
        ("interval-coverage", "interval_coverage", protocol.margins.min_interval_coverage, "minimum", "interval"),
        ("interval-score-nondegradation", "interval_score", protocol.margins.max_interval_score_delta, "maximum", "interval"),
        ("regret-nondegradation", "regret", protocol.margins.max_regret_delta, "maximum", "decision"),
    )
    categories: dict[str, list[GateClause]] = {
        "coverage": [], "predictive": [], "interval": [], "decision": []
    }
    for comparator in comparators:
        pair_key = f"{candidate_id}|{comparator}"
        predictive_vectors: dict[str, list[float]] = {}
        decision_vectors: dict[str, list[float]] = {}
        for fold_id in sorted(predictive_by_fold):
            for metric, values in predictive_by_fold[fold_id].paired_event_differences.get(pair_key, {}).items():
                predictive_vectors.setdefault(metric, []).extend(values)
            for metric, values in decision_by_fold[fold_id].paired_regret_differences.get(pair_key, {}).items():
                decision_vectors.setdefault(metric, []).extend(values)
        for clause_name, metric, threshold, direction, category in specifications:
            values = (
                decision_vectors.get(metric, []) if category == "decision"
                else predictive_vectors.get(metric, [])
            )
            clause = _classify_clause(
                clause_id=f"{candidate_id}:{comparator}:{clause_name}",
                comparator=comparator,
                metric=metric,
                values=values,
                threshold=threshold,
                direction=direction,  # type: ignore[arg-type]
                alpha=simultaneous_alpha,
                forced=forced,
            )
            clauses.append(clause)
            categories[category].append(clause)
    clause_statuses = {clause.status for clause in clauses}
    if "invalid" in clause_statuses:
        status: PromotionStatus = "invalid"
    elif "censored" in clause_statuses:
        status = "support-censored"
    elif "fail" in clause_statuses:
        status = "negative"
    elif "inconclusive" in clause_statuses:
        status = "inconclusive"
    else:
        status = "promotable"
    origin_ids = tuple(
        content_sha256(
            {
                "predictive": predictive_by_fold[fold.fold_id].model_dump(mode="json"),
                "decision": decision_by_fold[fold.fold_id].model_dump(mode="json"),
            }
        )
        for fold in folds
    )
    return PromotionAssessment(
        protocol_sha256=protocol_hash,
        candidate_id=candidate_id,
        candidate_config_sha256=candidate_config_sha256,
        comparator_ids=comparators,
        origin_evaluation_ids=origin_ids,
        clauses=tuple(clauses),
        useful_coverage=_category_value(categories["coverage"]),
        predictive_non_degradation=_category_value(categories["predictive"]),
        interval_non_degradation=_category_value(categories["interval"]),
        decision_non_degradation=_category_value(categories["decision"]),
        status=status,
        reasons=tuple(
            f"{clause.clause_id}:{clause.status}"
            for clause in clauses
            if clause.status != "pass"
        ),
    )


def build_operator_proposal(
    assessment: PromotionAssessment,
    *,
    target_config_version: str,
) -> OperatorPromotionProposal:
    if assessment.status != "promotable" or not assessment.clauses or any(
        clause.status != "pass" for clause in assessment.clauses
    ):
        raise ValueError("only an exact promotable assessment may produce an operator proposal")
    if not target_config_version.strip():
        raise ValueError("target_config_version must be non-empty")
    assessment_sha = content_sha256(assessment.model_dump(mode="json"))
    proposal = OperatorPromotionProposal(
        proposal_id="0" * 64,
        protocol_sha256=assessment.protocol_sha256,
        candidate_id=assessment.candidate_id,
        candidate_config_sha256=assessment.candidate_config_sha256,
        assessment_sha256=assessment_sha,
        target_config_version=target_config_version,
    )
    return proposal.model_copy(
        update={
            "proposal_id": content_sha256(
                proposal.model_dump(mode="json", exclude={"proposal_id"})
            )
        }
    )


class ValidationBundle(_ClosedModel):
    protocol: RecurrentBenchmarkProtocol
    origins: tuple[FrozenRecurrentOrigin, ...]
    cases: tuple[FutureCaseManifest, ...]
    predictive_evaluations: tuple[OriginPredictiveEvaluation, ...]
    decision_evaluations: tuple[OriginDecisionEvaluation, ...]
    assessments: tuple[PromotionAssessment, ...]
    authority: Literal["evidence-only"] = "evidence-only"

    @model_validator(mode="after")
    def _bound_artifacts(self) -> "ValidationBundle":
        protocol_hash = recurrent_protocol_sha256(self.protocol)
        fold_ids = tuple(origin.manifest.fold.fold_id for origin in self.origins)
        if len(fold_ids) != len(set(fold_ids)):
            raise ValueError("validation bundle contains duplicate origins")
        canonical_fold_ids = tuple(
            fold.fold_id for fold in self.protocol.folds if fold.fold_id in set(fold_ids)
        )
        if fold_ids != canonical_fold_ids:
            raise ValueError("validation bundle origins must follow protocol fold order")
        if any(origin.protocol_sha256 != protocol_hash for origin in self.origins):
            raise ValueError("bundle origin protocol mismatch")
        if tuple(case.fold_id for case in self.cases) != fold_ids:
            raise ValueError("bundle cases must align exactly with origins")
        if tuple(item.future_cases.fold_id for item in self.predictive_evaluations) != fold_ids:
            raise ValueError("bundle predictive evaluations must align exactly with origins")
        if tuple(item.fold_id for item in self.decision_evaluations) != fold_ids:
            raise ValueError("bundle decision evaluations must align exactly with origins")
        expected_candidates = tuple(EVIDENCE_ESTIMATOR_REGISTRY[2:])
        if tuple(item.candidate_id for item in self.assessments) != expected_candidates:
            raise ValueError("bundle assessments must cover the exact challenger registry")
        if any(assessment.protocol_sha256 != protocol_hash for assessment in self.assessments):
            raise ValueError("bundle assessment protocol mismatch")
        for origin, cases, predictive, decision in zip(
            self.origins,
            self.cases,
            self.predictive_evaluations,
            self.decision_evaluations,
            strict=True,
        ):
            if predictive.future_cases != cases:
                raise ValueError("bundle predictive case manifest differs from bundle cases")
            if predictive.origin_predictions_sha256 != origin.predictions_sha256:
                raise ValueError("bundle predictive origin identity mismatch")
            if decision.origin_predictions_sha256 != origin.predictions_sha256:
                raise ValueError("bundle decision origin identity mismatch")
            if decision.case_sha256 != cases.case_sha256:
                raise ValueError("bundle decision case identity mismatch")
            if decision.field_mass_sha256 != cases.field_mass_sha256:
                raise ValueError("bundle decision field identity mismatch")
            if decision.action_universe_sha256 != cases.action_universe_sha256:
                raise ValueError("bundle decision action identity mismatch")
        for assessment in self.assessments:
            configs = {
                origin.candidate_config_sha256[assessment.candidate_id]
                for origin in self.origins
            }
            if configs and configs != {assessment.candidate_config_sha256}:
                raise ValueError("bundle assessment candidate-config identity mismatch")
            expected_origin_ids = tuple(
                content_sha256({
                    "predictive": predictive.model_dump(mode="json"),
                    "decision": decision.model_dump(mode="json"),
                })
                for predictive, decision in zip(
                    self.predictive_evaluations,
                    self.decision_evaluations,
                    strict=True,
                )
            )
            if assessment.origin_evaluation_ids != expected_origin_ids:
                raise ValueError("bundle assessment origin-evaluation identity mismatch")
        return self


def _bundle_markdown(bundle: ValidationBundle, digest: str) -> str:
    lines = [
        "# Recurrent validation evidence bundle",
        "",
        f"- Bundle: `{digest}`",
        f"- Protocol: `{recurrent_protocol_sha256(bundle.protocol)}`",
        f"- Origins: {len(bundle.origins)}",
        "- Authority: evidence-only; no configuration is changed by this artifact.",
        "",
        "## Assessments",
        "",
    ]
    lines.extend(
        f"- `{assessment.candidate_id}`: **{assessment.status}**"
        for assessment in bundle.assessments
    )
    return "\n".join(lines) + "\n"


def write_recurrent_validation_bundle(path: Path, bundle: ValidationBundle) -> str:
    """Write an append-only content-addressed bundle and derived Markdown summary."""
    digest = content_sha256(bundle.model_dump(mode="json"))
    directory = path / digest
    atomic_write_canonical(directory / "bundle.json", bundle)
    summary = _bundle_markdown(bundle, digest).encode()
    summary_path = directory / "summary.md"
    if summary_path.exists():
        if summary_path.read_bytes() != summary:
            raise FileExistsError(f"refusing divergent bundle summary collision: {summary_path}")
    else:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = summary_path.with_name(f".{summary_path.name}.tmp")
        temporary.write_bytes(summary)
        temporary.replace(summary_path)
    return digest


__all__ = [
    "DIRECT_ESTIMATOR_IDS",
    "EVIDENCE_ESTIMATOR_REGISTRY",
    "EvidenceEstimatorId",
    "PromotionMargins",
    "RecurrentEvaluationSupport",
    "RecurrentBenchmarkFold",
    "RecurrentBenchmarkProtocol",
    "load_recurrent_protocol",
    "recurrent_protocol_sha256",
    "validate_base_protocol",
    "RefitStageArtifact",
    "FrozenEvidencePrediction",
    "FrozenDrawSeries",
    "FrozenJointDraws",
    "OriginForecastPayload",
    "OriginRefitManifest",
    "FrozenRecurrentOrigin",
    "seal_recurrent_origin",
    "FutureCase",
    "FutureCaseManifest",
    "PredictiveMetrics",
    "EventPredictiveEvidence",
    "OriginPredictiveEvaluation",
    "build_future_case_manifest",
    "evaluate_recurrent_predictions",
    "DecisionEvaluation",
    "OriginDecisionEvaluation",
    "evaluate_recurrent_decisions",
    "GateClause",
    "PromotionAssessment",
    "OperatorPromotionProposal",
    "aggregate_recurrent_validation",
    "build_operator_proposal",
    "ValidationBundle",
    "write_recurrent_validation_bundle",
]

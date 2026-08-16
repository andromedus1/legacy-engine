"""Immutable, evaluation-only recurrent-era validation contracts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal, TypeAlias

from pydantic import Field, model_validator

from legacy_engine.analytics.amplification import AMPLIFICATION_METHOD_IDS, MethodId
from legacy_engine.advisory.ranking_benchmark import content_sha256
from legacy_engine.models.base import LegacyEngineModel

DirectEstimatorId = Literal["current-only-v1", "contiguous-era-v1", "recurrent-expanded-v1"]
EvidenceEstimatorId: TypeAlias = DirectEstimatorId | MethodId
DIRECT_ESTIMATOR_IDS = ("current-only-v1", "contiguous-era-v1", "recurrent-expanded-v1")
EVIDENCE_ESTIMATOR_REGISTRY = DIRECT_ESTIMATOR_IDS + AMPLIFICATION_METHOD_IDS
ReplayMode = Literal["contemporaneous", "retrospective-policy-replay"]


class PromotionMargins(LegacyEngineModel):
    alpha: float = Field(gt=0, lt=1)
    min_served_field_coverage_gain: float
    min_served_event_coverage_gain: float
    max_log_loss_delta: float
    max_brier_delta: float
    max_calibration_delta: float
    min_interval_coverage: float = Field(ge=0, le=1)
    max_interval_score_delta: float
    max_regret_delta: float


class RecurrentEvaluationSupport(LegacyEngineModel):
    min_common_matches: int = Field(ge=1)
    min_events: int = Field(ge=1)
    min_event_dates: int = Field(ge=1)
    min_origins: int = Field(ge=1)
    min_regimes: int = Field(ge=1)
    min_calibration_matches: int = Field(ge=1)
    min_supported_actions: int = Field(ge=1)
    min_action_matches: int = Field(ge=1)
    min_future_field_coverage: float = Field(ge=0, le=1)


class RecurrentBenchmarkFold(LegacyEngineModel):
    fold_id: str
    data_until: str
    knowledge_as_of: datetime
    evaluation_until: str
    regime_id: str

    @model_validator(mode="after")
    def _clock(self) -> "RecurrentBenchmarkFold":
        if self.knowledge_as_of.tzinfo is None:
            raise ValueError("knowledge_as_of must be timezone-aware")
        if self.evaluation_until <= self.data_until:
            raise ValueError("evaluation_until must follow data_until")
        return self


class RecurrentBenchmarkProtocol(LegacyEngineModel):
    model_config = {"extra": "forbid"}
    protocol_id: Literal["recurrent-evidence-future-v1"]
    registered_at: datetime
    authority: Literal["evaluation-only"]
    replay_mode: ReplayMode
    base_benchmark_protocol_sha256: str
    estimator_ids: tuple[EvidenceEstimatorId, ...]
    discovery_calibration_sha256: str
    certification_calibration_sha256: str
    amplification_profile_sha256: str
    structure_policy_sha256: str
    folds: tuple[RecurrentBenchmarkFold, ...]
    log_clip_epsilon: float = Field(gt=0, lt=0.5)
    interval_level: float = Field(gt=0, lt=1)
    bootstrap_draws: int = Field(ge=1)
    seed: int
    support: RecurrentEvaluationSupport
    margins: PromotionMargins

    @model_validator(mode="after")
    def _closed(self) -> "RecurrentBenchmarkProtocol":
        if tuple(self.estimator_ids) != EVIDENCE_ESTIMATOR_REGISTRY:
            raise ValueError("estimator_ids must exactly equal the frozen recurrent registry")
        for name in ("base_benchmark_protocol_sha256", "discovery_calibration_sha256", "certification_calibration_sha256", "amplification_profile_sha256", "structure_policy_sha256"):
            value = getattr(self, name)
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")
        if tuple(f.fold_id for f in self.folds) != tuple(dict.fromkeys(f.fold_id for f in self.folds)):
            raise ValueError("fold ids must be unique")
        if self.registered_at.tzinfo is None:
            raise ValueError("registered_at must be timezone-aware")
        return self


class OriginRefitManifest(LegacyEngineModel):
    fold: RecurrentBenchmarkFold
    snapshot_manifest_sha256: str
    replay_mode: ReplayMode
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


class FrozenEvidencePrediction(LegacyEngineModel):
    estimator_id: EvidenceEstimatorId
    subject: str
    opponent: str
    probability: float | None
    interval: tuple[float, float] | None = None
    draw_artifact_sha256: str | None = None
    served: bool
    fallback_estimator_id: Literal["current-only-v1"] | None = None
    evidence_kind: Literal["current-only", "contiguous-era", "certified-expanded", "amplified"]
    current_match_ids_sha256: str
    historical_match_ids_sha256: str | None = None
    borrowed_match_ids_sha256: str | None = None
    imputation: Literal["none", "partial", "full"]
    fit_id: str
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _probability(self) -> "FrozenEvidencePrediction":
        if self.probability is not None and not 0 <= self.probability <= 1:
            raise ValueError("probability must be in [0,1]")
        return self


class FrozenRecurrentOrigin(LegacyEngineModel):
    protocol_sha256: str
    manifest: OriginRefitManifest
    action_universe: tuple[str, ...]
    field_shares: dict[str, float]
    predictions: tuple[FrozenEvidencePrediction, ...]
    recommendation_actions: dict[EvidenceEstimatorId, str | None]
    common_pair_universe_sha256: str
    predictions_sha256: str
    code_commit: str


class FutureCaseManifest(LegacyEngineModel):
    fold_id: str
    eligible_match_ids: tuple[str, ...]
    eligible_event_ids: tuple[str, ...]
    eligible_deck_ids: tuple[str, ...]
    case_sha256: str
    field_mass_sha256: str
    exclusions: dict[str, int] = {}


class PredictiveMetrics(LegacyEngineModel):
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
    refusal_counts: dict[str, int] = {}
    imputation_counts: dict[str, int] = {}
    evidence_concentration: dict[str, float | None] = {}
    status: Literal["complete", "support-censored", "invalid"]
    reasons: tuple[str, ...] = ()


class OriginPredictiveEvaluation(LegacyEngineModel):
    protocol_sha256: str
    origin_predictions_sha256: str
    future_cases: FutureCaseManifest
    metrics: tuple[PredictiveMetrics, ...]
    paired_event_differences: dict[str, dict[str, tuple[float, ...]]] = {}
    status: Literal["complete", "support-censored", "invalid"]
    reasons: tuple[str, ...] = ()


def load_recurrent_protocol(path: Path | str) -> RecurrentBenchmarkProtocol:
    payload = json.loads(Path(path).read_text())
    return RecurrentBenchmarkProtocol.model_validate(payload)


def recurrent_protocol_sha256(protocol: RecurrentBenchmarkProtocol) -> str:
    return content_sha256(protocol.model_dump(mode="json"))


def freeze_origin(
    protocol: RecurrentBenchmarkProtocol,
    fold: RecurrentBenchmarkFold,
    *,
    stage_artifacts: dict[str, str],
    action_universe: tuple[str, ...] = (),
    field_shares: dict[str, float] | None = None,
    predictions: tuple[FrozenEvidencePrediction, ...] = (),
    code_commit: str = "unknown",
) -> FrozenRecurrentOrigin:
    """Seal an injected, origin-refit stage bundle without consulting latest state."""
    if fold not in protocol.folds:
        raise ValueError("fold is not registered in protocol")
    required = ("snapshot", "discovery", "certification", "interval", "amplification", "structure")
    missing = [name for name in required if name not in stage_artifacts]
    status: Literal["complete", "not-evaluable", "invalid"] = "complete" if not missing else "not-evaluable"
    reasons = (f"missing stage artifacts: {','.join(missing)}",) if missing else ()
    manifest = OriginRefitManifest(
        fold=fold, snapshot_manifest_sha256=stage_artifacts.get("snapshot", ""),
        replay_mode=protocol.replay_mode, discovery_run_id=stage_artifacts.get("discovery", ""),
        certification_run_id=stage_artifacts.get("certification", ""), interval_corpus_id=stage_artifacts.get("interval", ""),
        amplification_run_id=stage_artifacts.get("amplification", ""), structure_snapshot_id=stage_artifacts.get("structure", ""),
        stage_input_sha256=dict(stage_artifacts), stage_config_sha256={}, max_outcome_date=fold.data_until,
        outcome_ids_sha256=content_sha256(()), status=status, reasons=reasons,
    )
    pairs = tuple(sorted({f"{p.subject}:{p.opponent}" for p in predictions}))
    return FrozenRecurrentOrigin(
        protocol_sha256=recurrent_protocol_sha256(protocol), manifest=manifest,
        action_universe=action_universe, field_shares=field_shares or {}, predictions=predictions,
        recommendation_actions={}, common_pair_universe_sha256=content_sha256(pairs),
        predictions_sha256=content_sha256([p.model_dump(mode="json") for p in predictions]), code_commit=code_commit,
    )


def refit_and_freeze_origin(source_db, *, protocol, fold, taxonomy_snapshot=None, knowledge_inputs=None):
    """Boundary adapter for workflows; production callers inject stage artifacts explicitly."""
    artifacts = getattr(knowledge_inputs, "stage_artifacts", None) if knowledge_inputs is not None else None
    if artifacts is None and isinstance(knowledge_inputs, dict):
        artifacts = knowledge_inputs.get("stage_artifacts")
    return freeze_origin(protocol, fold, stage_artifacts=artifacts or {})


def build_future_case_manifest(fold_id: str, rows, *, exclusions: dict[str, int] | None = None) -> FutureCaseManifest:
    eligible = tuple(sorted(row for row in rows if row.get("eligible", True)))
    match_ids = tuple(str(row["match_id"]) for row in eligible)
    event_ids = tuple(sorted({str(row["event_id"]) for row in eligible}))
    deck_ids = tuple(sorted({str(value) for row in eligible for value in (row.get("subject_deck_id"), row.get("opponent_deck_id")) if value is not None}))
    return FutureCaseManifest(
        fold_id=fold_id, eligible_match_ids=match_ids, eligible_event_ids=event_ids,
        eligible_deck_ids=deck_ids, case_sha256=content_sha256(match_ids),
        field_mass_sha256=content_sha256({str(row["match_id"]): row.get("field_mass", 0.0) for row in eligible}),
        exclusions=exclusions or {},
    )


def evaluate_recurrent_predictions(origin: FrozenRecurrentOrigin, cases: FutureCaseManifest, *, protocol: RecurrentBenchmarkProtocol, outcomes) -> OriginPredictiveEvaluation:
    by_id = {str(row["match_id"]): row for row in outcomes if str(row["match_id"]) in cases.eligible_match_ids}
    metrics: list[PredictiveMetrics] = []
    for estimator in protocol.estimator_ids:
        predictions = {(p.subject, p.opponent): p for p in origin.predictions if p.estimator_id == estimator}
        values: list[tuple[float, int, str]] = []
        invalid = False
        for row in by_id.values():
            prediction = predictions.get((str(row["subject"]), str(row["opponent"])))
            if prediction is None or prediction.probability is None:
                invalid = True
                continue
            values.append((min(1 - protocol.log_clip_epsilon, max(protocol.log_clip_epsilon, prediction.probability)), int(bool(row["subject_won"])), str(row["event_id"])))
        if invalid or len(values) != len(by_id):
            metrics.append(PredictiveMetrics(estimator_id=estimator, common_matches=len(values), common_events=len({v[2] for v in values}), log_loss=None, brier=None, served_match_coverage=0.0, served_event_coverage=0.0, served_field_coverage=0.0, status="invalid", reasons=("missing-all-case-prediction",)))
            continue
        log_loss = sum(-(y * __import__("math").log(p) + (1 - y) * __import__("math").log(1 - p)) for p, y, _ in values) / len(values)
        brier = sum((p - y) ** 2 for p, y, _ in values) / len(values)
        served = [p for p in origin.predictions if p.estimator_id == estimator and p.served]
        metrics.append(PredictiveMetrics(estimator_id=estimator, common_matches=len(values), common_events=len({v[2] for v in values}), log_loss=log_loss, brier=brier, served_match_coverage=len(served) / max(1, len(predictions)), served_event_coverage=0.0, served_field_coverage=0.0, status="complete"))
    status = "invalid" if any(metric.status == "invalid" for metric in metrics) else "complete"
    return OriginPredictiveEvaluation(protocol_sha256=recurrent_protocol_sha256(protocol), origin_predictions_sha256=origin.predictions_sha256, future_cases=cases, metrics=tuple(metrics), status=status)


__all__ = [
    "DIRECT_ESTIMATOR_IDS", "EVIDENCE_ESTIMATOR_REGISTRY", "EvidenceEstimatorId",
    "PromotionMargins", "RecurrentEvaluationSupport", "RecurrentBenchmarkFold",
    "RecurrentBenchmarkProtocol", "load_recurrent_protocol", "recurrent_protocol_sha256",
    "OriginRefitManifest", "FrozenEvidencePrediction", "FrozenRecurrentOrigin", "freeze_origin", "refit_and_freeze_origin", "FutureCaseManifest", "PredictiveMetrics", "OriginPredictiveEvaluation", "build_future_case_manifest", "evaluate_recurrent_predictions",
]

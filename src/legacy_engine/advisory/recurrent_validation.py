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


def load_recurrent_protocol(path: Path | str) -> RecurrentBenchmarkProtocol:
    payload = json.loads(Path(path).read_text())
    return RecurrentBenchmarkProtocol.model_validate(payload)


def recurrent_protocol_sha256(protocol: RecurrentBenchmarkProtocol) -> str:
    return content_sha256(protocol.model_dump(mode="json"))


__all__ = [
    "DIRECT_ESTIMATOR_IDS", "EVIDENCE_ESTIMATOR_REGISTRY", "EvidenceEstimatorId",
    "PromotionMargins", "RecurrentEvaluationSupport", "RecurrentBenchmarkFold",
    "RecurrentBenchmarkProtocol", "load_recurrent_protocol", "recurrent_protocol_sha256",
]

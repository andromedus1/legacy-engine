"""Closed, serializable contracts shared by amplification challengers."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import ConfigDict, Field, field_validator, model_validator

from legacy_engine.analytics.eras.consume import (
    AnalysisClock,
    EvidenceConcentration,
    MatchupEvidenceView,
)
from legacy_engine.confidence import ConfidenceMetadata
from legacy_engine.models.base import LegacyEngineModel

AMPLIFICATION_METHOD_IDS = (
    "component-hierarchical-v1",
    "composition-kernel-v1",
    "strategic-family-ladder-v1",
    "skew-low-rank-r1-v1",
    "skew-low-rank-r2-v1",
    "skew-low-rank-r4-v1",
)
MethodId = Literal[
    "component-hierarchical-v1",
    "composition-kernel-v1",
    "strategic-family-ladder-v1",
    "skew-low-rank-r1-v1",
    "skew-low-rank-r2-v1",
    "skew-low-rank-r4-v1",
]
EvidenceOrigin = Literal["current-direct", "certified-history"]
ServiceState = Literal[
    "directly-supported",
    "model-supported-lean",
    "prior-dominated",
    "concentrated",
    "family-inconsistent",
    "selection-sensitive",
    "unidentified",
    "computationally-unreliable",
    "not-assessed",
]


class _ClosedModel(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")


class EligibleOutcome(_ClosedModel):
    match_id: str
    unordered_pair_id: str
    subject: str
    opponent: str
    subject_won: bool
    event_id: str
    event_date: date
    provenance: str
    pair_component_id: str
    subject_component_id: str
    opponent_component_id: str
    subject_certificate_ids: tuple[str, ...]
    opponent_certificate_ids: tuple[str, ...]
    origin: EvidenceOrigin


class IntervalEvidenceCorpus(_ClosedModel):
    corpus_id: str
    clock: AnalysisClock
    certificate_run_id: str | None
    entities: tuple[str, ...]
    outcomes: tuple[EligibleOutcome, ...]
    pair_evidence_sha256: str
    entity_eligibility_sha256: str
    source_rows_sha256: str


class StructureSnapshot(_ClosedModel):
    snapshot_id: str
    knowledge_as_of: datetime
    taxonomy_id: str
    superarchetype_registry_sha256: str
    composition_features_sha256: str
    entities: tuple[str, ...]
    composition_features: dict[str, tuple[str, ...]] = {}
    strategic_families: dict[str, str] = {}
    outcome_columns_accessed: tuple[()] = ()

    @field_validator("knowledge_as_of")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("knowledge_as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _frozen_inputs(self) -> "StructureSnapshot":
        if set(self.composition_features) - set(self.entities):
            raise ValueError("composition features contain unknown entities")
        if set(self.strategic_families) - set(self.entities):
            raise ValueError("strategic families contain unknown entities")
        return self


class _FiniteParameters(_ClosedModel):
    @model_validator(mode="after")
    def _finite(self):
        for value in self.__dict__.values():
            values = value if isinstance(value, tuple) else (value,)
            if any(
                isinstance(item, float) and not math.isfinite(item) for item in values
            ):
                raise ValueError("method parameters must be finite")
        return self


class ComponentMethodParameters(_FiniteParameters):
    sigma_pair: float = Field(default=2.0, gt=0)
    tau_min: float = Field(default=0.05, gt=0)
    tau_max: float = Field(default=2.0, gt=0)
    sensitivity_tau: tuple[float, ...] = (0.1, 0.5, 1.0)

    @model_validator(mode="after")
    def _bounds(self):
        if self.tau_min > self.tau_max or any(x <= 0 for x in self.sensitivity_tau):
            raise ValueError("component scale bounds must be positive and ordered")
        return self


class CompositionMethodParameters(_FiniteParameters):
    bandwidth: float = Field(default=0.5, gt=0)
    min_similarity: float = Field(default=0.5, ge=0, le=1)
    min_weight: float = Field(default=0.05, ge=0)
    prior_strength_cap: float = Field(default=20.0, ge=0)


class FamilyMethodParameters(_FiniteParameters):
    prior_strength_cap: float = Field(default=20.0, ge=0)
    min_member_matches: int = Field(default=5, ge=1)
    sensitivity_strengths: tuple[float, ...] = (0.5, 1.0, 2.0)

    @field_validator("sensitivity_strengths")
    @classmethod
    def _positive_strengths(cls, value):
        if not value or any(item <= 0 for item in value):
            raise ValueError("sensitivity strengths must be positive")
        return value


class LowRankMethodParameters(_FiniteParameters):
    rank: Literal[1, 2, 4]
    l2_strength: float = Field(default=1.0, gt=0)
    multistarts: int = Field(default=2, ge=1)
    max_iterations: int = Field(default=200, ge=1)


class _MethodSpec(_ClosedModel):
    enabled: bool = True
    seed_offset: int = 0


class ComponentMethodSpec(_MethodSpec):
    method_id: Literal["component-hierarchical-v1"]
    parameters: ComponentMethodParameters


class CompositionMethodSpec(_MethodSpec):
    method_id: Literal["composition-kernel-v1"]
    parameters: CompositionMethodParameters


class FamilyMethodSpec(_MethodSpec):
    method_id: Literal["strategic-family-ladder-v1"]
    parameters: FamilyMethodParameters


class LowRankR1MethodSpec(_MethodSpec):
    method_id: Literal["skew-low-rank-r1-v1"]
    parameters: LowRankMethodParameters

    @model_validator(mode="after")
    def _rank(self):
        if self.parameters.rank != 1:
            raise ValueError("rank-one method requires rank=1")
        return self


class LowRankR2MethodSpec(_MethodSpec):
    method_id: Literal["skew-low-rank-r2-v1"]
    parameters: LowRankMethodParameters

    @model_validator(mode="after")
    def _rank(self):
        if self.parameters.rank != 2:
            raise ValueError("rank-two method requires rank=2")
        return self


class LowRankR4MethodSpec(_MethodSpec):
    method_id: Literal["skew-low-rank-r4-v1"]
    parameters: LowRankMethodParameters

    @model_validator(mode="after")
    def _rank(self):
        if self.parameters.rank != 4:
            raise ValueError("rank-four method requires rank=4")
        return self


MethodSpec: TypeAlias = Annotated[
    ComponentMethodSpec
    | CompositionMethodSpec
    | FamilyMethodSpec
    | LowRankR1MethodSpec
    | LowRankR2MethodSpec
    | LowRankR4MethodSpec,
    Field(discriminator="method_id"),
]


class ServiceGates(_FiniteParameters):
    min_effective_events: float = Field(default=3.0, ge=0)
    min_effective_components: float = Field(default=2.0, ge=0)
    min_effective_donor_pairs: float = Field(default=2.0, ge=0)
    max_event_share: float = Field(default=0.8, ge=0, le=1)
    max_component_share: float = Field(default=0.8, ge=0, le=1)
    max_donor_share: float = Field(default=0.8, ge=0, le=1)
    max_ablation_delta: float = Field(default=0.35, ge=0, le=1)
    min_bootstrap_success_fraction: float = Field(default=0.8, ge=0, le=1)


class AmplificationProfile(_ClosedModel):
    profile_id: Literal["amplification-diagnostic-v1"]
    authority: Literal["diagnostic-only"]
    method_specs: tuple[MethodSpec, ...]
    bootstrap_replicates: int = Field(default=100, ge=1)
    seed: int
    service_gates: ServiceGates

    @field_validator("method_specs")
    @classmethod
    def _methods(cls, value):
        ids = tuple(item.method_id for item in value)
        if len(ids) != len(set(ids)) or set(ids) != set(AMPLIFICATION_METHOD_IDS):
            raise ValueError("profile must contain each registered method exactly once")
        return value


class DirectBaseline(_ClosedModel):
    current_only: MatchupEvidenceView
    certified_expanded: MatchupEvidenceView
    current_sha256: str
    expanded_sha256: str


class EffectiveSupport(_ClosedModel):
    direct_matches: int = 0
    historical_matches: int = 0
    borrowed_matches: int = 0
    distinct_events: int = 0
    effective_events: float = 0.0
    effective_components: float = 0.0
    effective_donor_pairs: float = 0.0
    effective_members: float = 0.0
    comparison_graph_degree: int = 0


class BorrowingConcentration(_ClosedModel):
    evidence: EvidenceConcentration
    donor_pair_counts: dict[str, int] = {}
    member_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    donor_pair_weights: dict[str, float] = {}
    member_weights: dict[str, float] = {}
    family_weights: dict[str, float] = {}
    max_donor_pair_share: float | None = None
    max_member_share: float | None = None
    max_family_share: float | None = None
    effective_donor_pairs: float = 0.0
    effective_members: float = 0.0


class PredictionSummary(_ClosedModel):
    mean: float = Field(ge=0, le=1)
    median: float = Field(ge=0, le=1)
    ci_low: float = Field(ge=0, le=1)
    ci_high: float = Field(ge=0, le=1)
    draws: int = Field(ge=0)

    @model_validator(mode="after")
    def _ordered(self):
        if not self.ci_low <= self.median <= self.ci_high:
            raise ValueError("prediction interval and median must be ordered")
        return self


class EvidenceAblations(_ClosedModel):
    direct_baseline: float | None = None
    without_certified_history: float | None = None
    without_borrowing: float | None = None
    leave_target_pair_out: float | None = None
    full: float | None = None
    history_delta: float | None = None
    borrowing_delta: float | None = None
    nonadditive_remainder: float | None = None
    additive_attribution: Literal[False] = False


class ChallengerPrediction(_ClosedModel):
    method_id: MethodId
    subject: str
    opponent: str
    all_case: PredictionSummary | None = None
    served: PredictionSummary | None = None
    confidence: ConfidenceMetadata
    service_state: ServiceState
    imputation: Literal["none", "partial", "full"]
    current_match_ids_sha256: str
    historical_match_ids_sha256: str
    borrowed_match_ids_sha256: str | None = None
    support: EffectiveSupport
    borrowing_concentration: BorrowingConcentration | None = None
    ablations: EvidenceAblations
    fit_id: str
    reasons: tuple[str, ...] = ()


class EventBootstrapPlan(_ClosedModel):
    plan_id: str
    origin_snapshot_id: str
    seed: int
    event_blocks: tuple[tuple[str, ...], ...]


class AlignedDrawSeries(_ClosedModel):
    method_id: MethodId
    subject: str
    opponent: str
    fit_id: str
    probabilities: tuple[float, ...]

    @field_validator("probabilities")
    @classmethod
    def _probabilities(cls, value):
        if any(not math.isfinite(item) or item < 0 or item > 1 for item in value):
            raise ValueError("aligned draw probabilities must be finite probabilities")
        return value


class JointPredictiveDraws(_ClosedModel):
    """Origin-frozen, cross-cell aligned whole-event refit draws."""

    artifact_id: str
    origin_snapshot_id: str
    seed: int
    replicate_count: int
    replay_plan: EventBootstrapPlan
    event_blocks_sha256: str
    method_ids: tuple[MethodId, ...]
    series: tuple[AlignedDrawSeries, ...]
    draws_sha256: str

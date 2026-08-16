"""Stable, serializable contracts shared by amplification challengers."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from legacy_engine.analytics.eras.consume import AnalysisClock, EvidenceConcentration, MatchupEvidenceView
from legacy_engine.confidence import ConfidenceMetadata
from legacy_engine.models.base import LegacyEngineModel

MethodId = Literal["component-hierarchical-v1", "composition-kernel-v1", "strategic-family-ladder-v1", "skew-low-rank-r1-v1", "skew-low-rank-r2-v1", "skew-low-rank-r4-v1"]
EvidenceOrigin = Literal["current-direct", "certified-history"]
ServiceState = Literal["directly-supported", "model-supported-lean", "prior-dominated", "concentrated", "family-inconsistent", "selection-sensitive", "unidentified", "computationally-unreliable", "not-assessed"]

class EligibleOutcome(LegacyEngineModel):
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

class IntervalEvidenceCorpus(LegacyEngineModel):
    corpus_id: str
    clock: AnalysisClock
    certificate_run_id: str | None
    entities: tuple[str, ...]
    outcomes: tuple[EligibleOutcome, ...]
    pair_evidence_sha256: str
    entity_eligibility_sha256: str
    source_rows_sha256: str

class StructureSnapshot(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: str
    knowledge_as_of: datetime
    taxonomy_id: str
    superarchetype_registry_sha256: str
    composition_features_sha256: str
    entities: tuple[str, ...]
    outcome_columns_accessed: tuple[()] = ()

    @field_validator("knowledge_as_of")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("knowledge_as_of must be timezone-aware")
        return value

class ComponentMethodParameters(LegacyEngineModel):
    sigma_pair: float = 2.0
    tau_min: float = 0.05
    tau_max: float = 2.0
    sensitivity_tau: tuple[float, ...] = (0.1, 0.5, 1.0)

class CompositionMethodParameters(LegacyEngineModel):
    bandwidth: float = 0.5
    min_similarity: float = 0.5
    min_weight: float = 0.05
    prior_strength_cap: float = 20.0

class FamilyMethodParameters(LegacyEngineModel):
    prior_strength_cap: float = 20.0
    min_member_matches: int = 5
    sensitivity_strengths: tuple[float, ...] = (0.5, 1.0, 2.0)

class LowRankMethodParameters(LegacyEngineModel):
    rank: Literal[1, 2, 4]
    l2_strength: float = 1.0
    multistarts: int = 2
    max_iterations: int = 200

class MethodSpec(LegacyEngineModel):
    method_id: MethodId
    enabled: bool = True
    seed_offset: int = 0
    parameters: ComponentMethodParameters | CompositionMethodParameters | FamilyMethodParameters | LowRankMethodParameters

class ServiceGates(LegacyEngineModel):
    min_effective_events: float = 3.0
    min_effective_components: float = 2.0
    min_effective_donor_pairs: float = 2.0
    max_event_share: float = 0.8
    max_component_share: float = 0.8
    max_donor_share: float = 0.8
    max_ablation_delta: float = 0.35
    min_bootstrap_success_fraction: float = 0.8

class AmplificationProfile(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: Literal["amplification-diagnostic-v1"]
    authority: Literal["diagnostic-only"]
    method_specs: tuple[MethodSpec, ...]
    bootstrap_replicates: int = Field(default=100, ge=0)
    seed: int
    service_gates: ServiceGates

    @field_validator("method_specs")
    @classmethod
    def _methods(cls, value: tuple[MethodSpec, ...]) -> tuple[MethodSpec, ...]:
        ids = [item.method_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate amplification method ids")
        required = {"component-hierarchical-v1", "composition-kernel-v1", "strategic-family-ladder-v1", "skew-low-rank-r1-v1", "skew-low-rank-r2-v1", "skew-low-rank-r4-v1"}
        if set(ids) != required:
            raise ValueError(f"profile methods must be exactly {sorted(required)}")
        return value

class DirectBaseline(LegacyEngineModel):
    current_only: MatchupEvidenceView
    certified_expanded: MatchupEvidenceView
    current_sha256: str
    expanded_sha256: str

class EffectiveSupport(LegacyEngineModel):
    direct_matches: int = 0
    historical_matches: int = 0
    borrowed_matches: int = 0
    distinct_events: int = 0
    effective_events: float = 0.0
    effective_components: float = 0.0
    effective_donor_pairs: float = 0.0
    effective_members: float = 0.0
    comparison_graph_degree: int = 0

class BorrowingConcentration(LegacyEngineModel):
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

class PredictionSummary(LegacyEngineModel):
    mean: float
    median: float
    ci_low: float
    ci_high: float
    draws: int

class EvidenceAblations(LegacyEngineModel):
    direct_baseline: float | None = None
    without_certified_history: float | None = None
    without_borrowing: float | None = None
    leave_target_pair_out: float | None = None
    full: float | None = None
    history_delta: float | None = None
    borrowing_delta: float | None = None
    nonadditive_remainder: float | None = None
    additive_attribution: Literal[False] = False

class ChallengerPrediction(LegacyEngineModel):
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

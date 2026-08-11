"""Pure contracts and chronological planning for the future-only ranking benchmark."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.advisory.ranking_measurement import (
    MethodologyVariantSpec,
    RankingCellMeasurement,
)

BenchmarkEstimatorId = Literal[
    "coin-50", "recent-raw-wr", "field-share", "top-finish-conversion",
    "simple-jeffreys-shrinkage", "production-raw", "production-ci-gated",
    "production-ban-scoped", "production-era-only", "production-lean",
]
TaxonomyReplayMode = Literal["contemporaneous", "retrospective-fixed-parent"]

ESTIMATOR_REGISTRY: tuple[BenchmarkEstimatorId, ...] = (
    "coin-50", "recent-raw-wr", "field-share", "top-finish-conversion",
    "simple-jeffreys-shrinkage", "production-raw", "production-ci-gated",
    "production-ban-scoped", "production-era-only", "production-lean",
)
PRODUCTION_ESTIMATORS = frozenset({
    "production-raw", "production-ci-gated", "production-ban-scoped",
    "production-era-only", "production-lean",
})


class EvaluationSupport(LegacyEngineModel):
    min_common_matches: int = 250
    min_events: int = 10
    min_event_dates: int = 4
    min_calibration_matches: int = 500
    min_supported_actions: int = 5
    min_action_matches: int = 8
    min_future_field_coverage: float = 0.80
    min_claim_folds: int = 6
    min_claim_regimes: int = 2


class BenchmarkProtocol(LegacyEngineModel):
    protocol_id: str
    created_at: str
    taxonomy_mode: TaxonomyReplayMode
    first_cutoff: str
    final_evaluation_until: str
    horizon_days: int = 28
    step_days: int = 28
    primary_estimator: BenchmarkEstimatorId = "production-ci-gated"
    estimator_ids: tuple[BenchmarkEstimatorId, ...] = ESTIMATOR_REGISTRY
    action_min_share: float = 0.001
    log_clip_epsilon: float = 1e-6
    bootstrap_draws: int = 2_000
    seed: int = 730_021
    support: EvaluationSupport = Field(default_factory=EvaluationSupport)

    @model_validator(mode="after")
    def _validate_protocol(self) -> "BenchmarkProtocol":
        first = date.fromisoformat(self.first_cutoff)
        final = date.fromisoformat(self.final_evaluation_until)
        datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        if final <= first:
            raise ValueError("final_evaluation_until must be after first_cutoff")
        if self.horizon_days < 1 or self.step_days < 1:
            raise ValueError("horizon_days and step_days must be positive")
        if self.bootstrap_draws < 1:
            raise ValueError("bootstrap_draws must be positive")
        if not 0.0 <= self.action_min_share <= 1.0:
            raise ValueError("action_min_share must be in [0, 1]")
        if not 0.0 < self.log_clip_epsilon < 0.5:
            raise ValueError("log_clip_epsilon must be in (0, 0.5)")
        if tuple(self.estimator_ids) != ESTIMATOR_REGISTRY:
            raise ValueError("estimator_ids must equal the preregistered estimator registry")
        if self.primary_estimator != "production-ci-gated":
            raise ValueError("primary_estimator must be production-ci-gated")
        return self


class BenchmarkFold(LegacyEngineModel):
    fold_id: str
    cutoff: str
    evaluation_until: str
    regime_start: str
    regime_end: str | None
    event_dates: tuple[str, ...]


class TaxonomySnapshotManifest(LegacyEngineModel):
    source: str
    effective_at: str
    action_level: Literal["parent"] = "parent"
    rules_manifest: str
    rules_sha256: str
    labels_sha256: str | None = None


class SnapshotManifest(LegacyEngineModel):
    protocol_hash: str
    fold: BenchmarkFold
    training_source_fingerprint: str
    training_facts_sha256: str
    training_event_ids_sha256: str
    training_events: int
    training_decks: int
    training_decisive_matches: int
    max_training_event_date: str
    ban_ledger_sha256: str
    ban_events_as_of: tuple[tuple[str, str, str], ...]
    taxonomy_mode: TaxonomyReplayMode
    taxonomy_effective_at: str | None
    taxonomy_sha256: str
    rules_sha256: str
    card_availability_sha256: str
    degraded: bool
    reasons: tuple[str, ...]


class FrozenMatchupPrediction(LegacyEngineModel):
    estimator: BenchmarkEstimatorId
    subject: str
    opponent: str
    probability: float
    served: bool
    source_kind: str
    imputed: bool
    refusal_reason: str | None


class FrozenRecommendation(LegacyEngineModel):
    estimator: BenchmarkEstimatorId
    chosen_action: str | None
    ranked_actions: tuple[str, ...]
    scores: dict[str, float | None]
    served: bool
    refusal_reason: str | None


class FrozenOriginPredictions(LegacyEngineModel):
    protocol_hash: str
    snapshot_manifest_sha256: str
    fold: BenchmarkFold
    generated_at: str
    code_commit: str
    estimator_registry: tuple[BenchmarkEstimatorId, ...]
    action_universe: tuple[str, ...]
    field_shares: dict[str, float]
    matchup_predictions: tuple[FrozenMatchupPrediction, ...]
    recommendations: tuple[FrozenRecommendation, ...]
    methodology: dict[str, dict[str, object]]
    seeds: dict[str, int]


def canonical_json_bytes(value: object) -> bytes:
    """Stable, finite JSON encoding used by every benchmark hash boundary."""
    if isinstance(value, LegacyEngineModel):
        value = value.model_dump(mode="json")
    return (json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ) + "\n").encode()


def content_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def protocol_sha256(protocol: BenchmarkProtocol) -> str:
    return content_sha256(protocol)


_VARIANT_ESTIMATOR: dict[str, BenchmarkEstimatorId] = {
    "raw": "production-raw",
    "ci-gated": "production-ci-gated",
    "ban-scoped": "production-ban-scoped",
    "era-only": "production-era-only",
}


def project_matchup_probability(
    cell: RankingCellMeasurement,
    *,
    spec: MethodologyVariantSpec,
    unresolved_center: float = 0.5,
) -> FrozenMatchupPrediction:
    """Project one typed production cell without turning imputation into serving authority."""
    if not 0.0 <= unresolved_center <= 1.0:
        raise ValueError("unresolved_center must be in [0, 1]")
    source = {
        "selected": cell.selected,
        "fallback": cell.fallback,
        "era": cell.era,
    }[spec.source_policy]
    estimator = _VARIANT_ESTIMATOR[spec.id]
    value = None
    if source is not None:
        value = source.cell.p_raw if spec.rate_basis == "raw" else source.cell.p_shrunk
    resolved = source is not None and source.cell.n > 0 and value is not None
    served = resolved and source.cell.n >= spec.evidence_n
    return FrozenMatchupPrediction(
        estimator=estimator, subject=cell.subject, opponent=cell.opponent,
        probability=float(value) if resolved else unresolved_center,
        served=served,
        source_kind=source.kind if source is not None else "unresolved",
        imputed=not resolved,
        refusal_reason=None if served else (
            f"source evidence n={source.cell.n} below n={spec.evidence_n}"
            if resolved else "no frozen matchup evidence; explicit 0.5 forecast"
        ),
    )


def write_frozen_predictions(path: Path, predictions: FrozenOriginPredictions) -> str:
    return atomic_write_canonical(path, predictions)


def _fold_id(cutoff: date, until: date) -> str:
    return f"{cutoff.isoformat()}--{until.isoformat()}"


def plan_walk_forward_folds(
    event_dates: Sequence[str],
    ban_dates: Sequence[str],
    protocol: BenchmarkProtocol,
) -> tuple[BenchmarkFold, ...]:
    """Plan non-overlapping, whole-date folds reset and truncated at B&R boundaries."""
    first = date.fromisoformat(protocol.first_cutoff)
    final = date.fromisoformat(protocol.final_evaluation_until)
    events = tuple(sorted({date.fromisoformat(value) for value in event_dates}))
    bans = tuple(sorted({date.fromisoformat(value) for value in ban_dates if first < date.fromisoformat(value) < final}))

    folds: list[BenchmarkFold] = []
    origin = first
    while origin < final:
        next_ban = next((ban for ban in bans if ban > origin), None)
        until = min(origin + timedelta(days=protocol.horizon_days), final)
        if next_ban is not None and next_ban < until:
            until = next_ban
        regime_start = max((ban for ban in bans if ban <= origin), default=first)
        regime_end = next((ban for ban in bans if ban > origin), None)
        heldout_dates = tuple(d.isoformat() for d in events if origin <= d < until)
        folds.append(BenchmarkFold(
            fold_id=_fold_id(origin, until), cutoff=origin.isoformat(),
            evaluation_until=until.isoformat(), regime_start=regime_start.isoformat(),
            regime_end=regime_end.isoformat() if regime_end is not None else None,
            event_dates=heldout_dates,
        ))
        if next_ban is not None and until == next_ban:
            origin = next_ban
        else:
            origin += timedelta(days=protocol.step_days)
            if next_ban is not None and origin > next_ban:
                origin = next_ban
    return tuple(folds)


def validate_snapshot_manifest(manifest: SnapshotManifest) -> None:
    cutoff = date.fromisoformat(manifest.fold.cutoff)
    if manifest.training_events < 1:
        raise ValueError("origin snapshot has no training events")
    if date.fromisoformat(manifest.max_training_event_date) >= cutoff:
        raise ValueError("origin snapshot contains an event at or after cutoff")
    if any(date.fromisoformat(event[0]) > cutoff for event in manifest.ban_events_as_of):
        raise ValueError("origin snapshot contains a future ban event")


def atomic_write_canonical(path: Path, value: object) -> str:
    """Write canonical JSON atomically and return its digest."""
    payload = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        import os
        os.fsync(handle.fileno())
    temporary.replace(path)
    return hashlib.sha256(payload).hexdigest()


def load_hashed_model(path: Path, model_type: type[LegacyEngineModel], expected_sha256: str | None = None):
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError(f"artifact hash mismatch for {path}: expected {expected_sha256}, got {digest}")
    return model_type.model_validate_json(payload), digest

"""File-backed orchestration and immutable storage for recurrent validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
from typing import Protocol

from pydantic import ConfigDict

from legacy_engine.advisory.ranking_benchmark import (
    BenchmarkFold,
    BenchmarkProtocol,
    atomic_write_canonical,
    content_sha256,
)
from legacy_engine.advisory.recurrent_validation import (
    EVIDENCE_ESTIMATOR_REGISTRY,
    FrozenRecurrentOrigin,
    FutureCaseManifest,
    OperatorPromotionProposal,
    OriginDecisionEvaluation,
    OriginForecastPayload,
    OriginPredictiveEvaluation,
    PromotionAssessment,
    RecurrentBenchmarkFold,
    RecurrentBenchmarkProtocol,
    RefitStageArtifact,
    ValidationBundle,
    aggregate_recurrent_validation,
    build_future_case_manifest,
    build_operator_proposal,
    evaluate_recurrent_decisions,
    evaluate_recurrent_predictions,
    recurrent_protocol_sha256,
    seal_recurrent_origin,
    validate_base_protocol,
    write_recurrent_validation_bundle,
)
from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.workflows.ranking_benchmark import build_origin_snapshot

_STAGE_CONFIG_FIELDS = {
    "discovery": "discovery_calibration_sha256",
    "certification": "certification_calibration_sha256",
    "interval": "interval_policy_sha256",
    "structure": "structure_policy_sha256",
    "amplification": "amplification_profile_sha256",
}


class _ClosedModel(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")


class OriginStageRequest(_ClosedModel):
    """Exact input contract presented to one origin-local refit stage."""

    stage: str
    snapshot_db: str
    snapshot_manifest_sha256: str
    prior_output_sha256: str
    expected_config_sha256: str
    fold: RecurrentBenchmarkFold


class OriginRefitExecutor(Protocol):
    """Adapter implemented by a real evidence chain or a hermetic integration fixture."""

    def run_stage(self, request: OriginStageRequest) -> RefitStageArtifact:
        """Run exactly one named stage from the immutable snapshot and prior artifact."""

    def freeze_forecast(
        self,
        snapshot_db: Path,
        *,
        protocol: RecurrentBenchmarkProtocol,
        fold: RecurrentBenchmarkFold,
        stages: tuple[RefitStageArtifact, ...],
    ) -> OriginForecastPayload:
        """Freeze the complete estimator grid only after every refit stage succeeds."""


class FrozenOriginArtifact(_ClosedModel):
    artifact_sha256: str
    snapshot_manifest_sha256: str
    snapshot_file_sha256: str
    origin: FrozenRecurrentOrigin


class OriginEvaluationArtifact(_ClosedModel):
    artifact_sha256: str
    cases: FutureCaseManifest
    predictive: OriginPredictiveEvaluation
    decision: OriginDecisionEvaluation


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _base_fold(
    base_protocol: BenchmarkProtocol,
    fold: RecurrentBenchmarkFold,
) -> BenchmarkFold:
    try:
        return next(item for item in base_protocol.planned_folds if item.fold_id == fold.fold_id)
    except StopIteration as exc:
        raise ValueError(f"fold {fold.fold_id!r} is absent from the base benchmark") from exc


def _code_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def plan_recurrent_validation(
    protocol: RecurrentBenchmarkProtocol,
    base_protocol: BenchmarkProtocol,
    *,
    artifact_root: Path,
) -> str:
    """Validate and store the exact protocol without creating a mutable alias."""
    validate_base_protocol(protocol, base_protocol)
    digest = recurrent_protocol_sha256(protocol)
    atomic_write_canonical(artifact_root / "protocols" / digest / "protocol.json", protocol)
    return digest


def refit_and_freeze_origin(
    source_db: Path,
    *,
    protocol: RecurrentBenchmarkProtocol,
    base_protocol: BenchmarkProtocol,
    fold: RecurrentBenchmarkFold,
    executor: OriginRefitExecutor,
    artifact_root: Path,
    taxonomy_snapshot: Path | None = None,
    code_commit: str | None = None,
) -> FrozenOriginArtifact:
    """Build a real cutoff snapshot, execute the typed chain, and seal one origin."""
    validate_base_protocol(protocol, base_protocol)
    if fold not in protocol.folds:
        raise ValueError("fold is not registered in recurrent protocol")
    base_fold = _base_fold(base_protocol, fold)
    protocol_hash = recurrent_protocol_sha256(protocol)
    with tempfile.TemporaryDirectory(prefix="legacy-recurrent-origin-") as temporary:
        temporary_snapshot = Path(temporary) / "origin.duckdb"
        snapshot_manifest = build_origin_snapshot(
            source_db,
            temporary_snapshot,
            fold=base_fold,
            protocol_hash=protocol_hash,
            taxonomy_mode=base_protocol.taxonomy_mode,
            taxonomy_snapshot=taxonomy_snapshot,
            ban_events=base_protocol.ban_events_as_of,
            card_metadata_policy=base_protocol.card_metadata,
        )
        if (
            snapshot_manifest.max_training_event_date
            and snapshot_manifest.max_training_event_date >= fold.data_until
        ):
            raise ValueError("snapshot contains an outcome at or after the exclusive origin")
        snapshot_sha = content_sha256(snapshot_manifest.model_dump(mode="json"))
        stages: list[RefitStageArtifact] = []
        prior = snapshot_sha
        for stage, field in _STAGE_CONFIG_FIELDS.items():
            request = OriginStageRequest(
                stage=stage,
                snapshot_db=str(temporary_snapshot),
                snapshot_manifest_sha256=snapshot_sha,
                prior_output_sha256=prior,
                expected_config_sha256=getattr(protocol, field),
                fold=fold,
            )
            artifact = executor.run_stage(request)
            if artifact.stage != stage:
                raise ValueError(f"executor returned {artifact.stage!r} for requested {stage!r}")
            if artifact.input_sha256 != prior:
                raise ValueError(f"executor returned a disconnected {stage} input digest")
            if artifact.config_sha256 != request.expected_config_sha256:
                raise ValueError(f"executor returned a drifted {stage} config digest")
            if artifact.status != "complete":
                raise ValueError(f"origin refit stopped at {stage}: {'; '.join(artifact.reasons)}")
            stages.append(artifact)
            prior = artifact.output_sha256
        forecast = executor.freeze_forecast(
            temporary_snapshot,
            protocol=protocol,
            fold=fold,
            stages=tuple(stages),
        )
        origin = seal_recurrent_origin(
            protocol,
            fold,
            snapshot_manifest_sha256=snapshot_sha,
            stages=stages,
            forecast=forecast,
            code_commit=code_commit or _code_commit(),
        )
        origin_digest = content_sha256(origin.model_dump(mode="json"))
        directory = artifact_root / "origins" / origin_digest
        snapshot_path = directory / "snapshot.duckdb"
        if snapshot_path.exists():
            if _file_sha256(snapshot_path) != _file_sha256(temporary_snapshot):
                raise FileExistsError(f"refusing divergent origin snapshot collision: {snapshot_path}")
        else:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(temporary_snapshot, snapshot_path)
        snapshot_file_sha = _file_sha256(snapshot_path)
        artifact = FrozenOriginArtifact(
            artifact_sha256="0" * 64,
            snapshot_manifest_sha256=snapshot_sha,
            snapshot_file_sha256=snapshot_file_sha,
            origin=origin,
        )
        artifact = artifact.model_copy(
            update={
                "artifact_sha256": content_sha256(
                    artifact.model_dump(mode="json", exclude={"artifact_sha256"})
                )
            }
        )
        atomic_write_canonical(directory / "origin.json", artifact)
        return artifact


def evaluate_recurrent_origin(
    origin: FrozenRecurrentOrigin,
    rows: Sequence[Mapping[str, object]],
    *,
    protocol: RecurrentBenchmarkProtocol,
    future_field_counts: Mapping[str, int],
    artifact_root: Path,
) -> OriginEvaluationArtifact:
    """Build the common ledger once, then evaluate prediction and decision branches."""
    cases = build_future_case_manifest(
        origin,
        rows,
        protocol=protocol,
        future_field_counts=future_field_counts,
    )
    predictive = evaluate_recurrent_predictions(origin, cases, protocol=protocol)
    decision = evaluate_recurrent_decisions(origin, cases, protocol=protocol)
    artifact = OriginEvaluationArtifact(
        artifact_sha256="0" * 64,
        cases=cases,
        predictive=predictive,
        decision=decision,
    )
    artifact = artifact.model_copy(
        update={
            "artifact_sha256": content_sha256(
                artifact.model_dump(mode="json", exclude={"artifact_sha256"})
            )
        }
    )
    atomic_write_canonical(
        artifact_root / "evaluations" / artifact.artifact_sha256 / "evaluation.json",
        artifact,
    )
    return artifact


def aggregate_recurrent_evidence(
    protocol: RecurrentBenchmarkProtocol,
    origins: Sequence[FrozenRecurrentOrigin],
    evaluations: Sequence[OriginEvaluationArtifact],
    *,
    artifact_root: Path,
) -> tuple[ValidationBundle, str]:
    """Assess every frozen challenger and write the complete content-addressed bundle."""
    if len(origins) != len(evaluations):
        raise ValueError("origins and evaluations must align one-to-one")
    configs: dict[str, str] = {}
    for estimator in EVIDENCE_ESTIMATOR_REGISTRY:
        values = {origin.candidate_config_sha256[estimator] for origin in origins}
        if len(values) != 1:
            raise ValueError(f"candidate config drift across origins for {estimator}")
        configs[estimator] = values.pop()
    assessments: list[PromotionAssessment] = []
    for candidate in EVIDENCE_ESTIMATOR_REGISTRY[2:]:
        assessments.append(
            aggregate_recurrent_validation(
                [item.predictive for item in evaluations],
                [item.decision for item in evaluations],
                protocol=protocol,
                candidate_id=candidate,
                candidate_config_sha256=configs[candidate],
            )
        )
    bundle = ValidationBundle(
        protocol=protocol,
        origins=tuple(origins),
        cases=tuple(item.cases for item in evaluations),
        predictive_evaluations=tuple(item.predictive for item in evaluations),
        decision_evaluations=tuple(item.decision for item in evaluations),
        assessments=tuple(assessments),
    )
    return bundle, write_recurrent_validation_bundle(artifact_root / "bundles", bundle)


def write_operator_proposal(
    assessment: PromotionAssessment,
    *,
    target_config_version: str,
    artifact_root: Path,
) -> OperatorPromotionProposal:
    """Write an inert proposal; this module intentionally has no apply operation."""
    proposal = build_operator_proposal(
        assessment,
        target_config_version=target_config_version,
    )
    atomic_write_canonical(
        artifact_root / "proposals" / proposal.proposal_id / "proposal.json",
        proposal,
    )
    return proposal


__all__ = [
    "OriginStageRequest",
    "OriginRefitExecutor",
    "FrozenOriginArtifact",
    "OriginEvaluationArtifact",
    "plan_recurrent_validation",
    "refit_and_freeze_origin",
    "evaluate_recurrent_origin",
    "aggregate_recurrent_evidence",
    "write_operator_proposal",
]

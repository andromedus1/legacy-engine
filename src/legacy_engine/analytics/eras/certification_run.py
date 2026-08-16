"""Composition root for immutable recurrent-era certification runs."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Literal

import duckdb

from legacy_engine.analytics.eras.certification import (
    CandidateCertificationInput,
    CertificationCalibration,
    CertificationReason,
    CandidateDecision,
    ContextOverlapEvidence,
    EquivalenceEvidence,
    HalfOpenInterval,
    PartitionManifest,
    SemanticFact,
    SemanticGuardEvidence,
    SupportEvidence,
    build_candidate_inputs,
    certify_candidate_family,
    load_certification_corpus,
)
from legacy_engine.analytics.eras.discovery import DiscoveryBoundary, DiscoveryStatus, OutcomeFreeModel, payload_sha256
from legacy_engine.analytics.eras.discovery_run import DiscoveryRun
from legacy_engine.analytics.eras.discovery_store import read_discovery_run
from pydantic import Field, field_validator, model_validator

CertificationRunStatus = Literal["complete", "degraded"]
CertificationRunReason = Literal["no-recurrent-candidates", "all-inconclusive", "format-truth-unresolved"]

CERTIFICATION_FEATURE_ALLOWLIST = (
    "deck.mainboard", "deck.parent_archetype", "deck.pilot_key", "deck.sideboard",
    "event.date", "event.provenance", "event.source", "format.semantic_fact",
    "legality.version", "partition.event_id", "reference.context", "taxonomy.version",
)


class EraCertificate(OutcomeFreeModel):
    certificate_id: str
    entity: str
    candidate_id: str
    historical_segment_id: str
    reference_segment_id: str
    historical_interval: HalfOpenInterval
    reference_interval: HalfOpenInterval
    certification_as_of: date
    discovery_run_id: str
    status: Literal["certified", "rejected", "inconclusive"]
    reasons: tuple[CertificationReason, ...]
    feature_schema_version: str
    calibration_profile_id: str
    partition: PartitionManifest
    semantic: SemanticGuardEvidence
    support: SupportEvidence
    context_overlap: ContextOverlapEvidence
    equivalence: EquivalenceEvidence | None
    outcome_columns_accessed: tuple[()] = ()

    @field_validator("certificate_id", "entity", "candidate_id", "historical_segment_id", "reference_segment_id")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("certificate identity text must be non-empty")
        return value

    @model_validator(mode="after")
    def _outcome_free(self) -> "EraCertificate":
        if self.outcome_columns_accessed != ():
            raise ValueError("outcome_columns_accessed must be empty")
        return self


class EntityCertificationResult(OutcomeFreeModel):
    entity: str
    reference_segment_id: str | None
    reference_interval: HalfOpenInterval | None
    discovery_status: DiscoveryStatus
    candidate_id: str | None
    certificates: tuple[EraCertificate, ...]
    reasons: tuple[str, ...]


class CertificationManifest(OutcomeFreeModel):
    discovery_run_id: str
    discovery_results_sha256: str
    certification_as_of: date
    certification_source_sha256: str
    feature_schema_version: str
    calibration_profile_id: str
    calibration_sha256: str
    partition_sha256: str
    semantic_facts_sha256: str
    format_observation_sha256: str | None
    outcome_feature_allowlist: tuple[str, ...]
    seed: int

    @model_validator(mode="after")
    def _closed(self) -> "CertificationManifest":
        if self.outcome_feature_allowlist != CERTIFICATION_FEATURE_ALLOWLIST:
            raise ValueError("outcome_feature_allowlist must equal the shipped certification allowlist")
        for name in (
            "discovery_results_sha256", "certification_source_sha256", "calibration_sha256",
            "partition_sha256", "semantic_facts_sha256",
        ):
            value = getattr(self, name)
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")
        if self.format_observation_sha256 is not None and (
            len(self.format_observation_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.format_observation_sha256)
        ):
            raise ValueError("format_observation_sha256 must be a lowercase SHA-256 digest")
        return self


class CertificationRun(OutcomeFreeModel):
    run_id: str
    manifest: CertificationManifest
    results_sha256: str
    status: CertificationRunStatus
    reasons: tuple[CertificationRunReason, ...]
    results: tuple[EntityCertificationResult, ...]


def _as_boundary(fact: SemanticFact) -> DiscoveryBoundary:
    kind = "legality" if fact.kind == "legality" else ("taxonomy" if fact.kind == "taxonomy" else "source-contract")
    return DiscoveryBoundary(
        boundary_id=fact.fact_id, effective_on=fact.effective_on, kind=kind,
        hard=fact.state == "confirmed", detail=fact.detail,
    )


def _certificate_id(run_id: str, decision: CandidateDecision, calibration: CertificationCalibration) -> str:
    return "certificate-" + payload_sha256({
        "run_id": run_id, "candidate": decision.candidate.model_dump(mode="json"),
        "semantic": decision.semantic.model_dump(mode="json"),
        "support": decision.support.model_dump(mode="json"),
        "context": decision.context_overlap.model_dump(mode="json"),
        "equivalence": decision.equivalence.model_dump(mode="json") if decision.equivalence else None,
        "profile": calibration.profile_id,
        "status": decision.final_status,
    })[:32]


def run_recurrent_certification(
    con: duckdb.DuckDBPyConnection,
    *,
    discovery_run_id: str,
    calibration: CertificationCalibration,
    semantic_facts: Sequence[SemanticFact],
    format_observation_sha256: str | None,
    seed: int = 0,
) -> CertificationRun:
    """Certify one exact discovery run against its disjoint held-out corpus."""

    discovery_run = read_discovery_run(con, discovery_run_id)
    if discovery_run is None:
        raise ValueError(f"discovery run {discovery_run_id!r} not found")
    # Semantic facts are an independent certification snapshot.  Only reuse
    # them as source boundaries when the discovery run itself recorded a
    # non-empty boundary catalog; pending monitor observations must not alter
    # an otherwise empty discovery corpus identity.
    derived_boundaries = tuple(_as_boundary(fact) for fact in semantic_facts)
    empty_boundary_digest = payload_sha256([])
    boundaries = derived_boundaries if discovery_run.manifest.semantic_boundaries_sha256 != empty_boundary_digest else ()
    corpus, partition = load_certification_corpus(
        con,
        discovery_run=discovery_run,
        calibration=calibration,
        as_of=discovery_run.manifest.as_of,
        taxonomy_version=discovery_run.manifest.taxonomy_version,
        legality_version=discovery_run.manifest.legality_version,
        semantic_boundaries=boundaries,
        provenance=discovery_run.manifest.provenance_filter,
    )
    candidates = build_candidate_inputs(discovery_run, corpus)
    decisions = certify_candidate_family(candidates, semantic_facts, calibration, seed=seed)
    decision_by_entity: dict[str, list[CandidateDecision]] = {}
    for decision in decisions:
        decision_by_entity.setdefault(decision.candidate.entity, []).append(decision)
    segments = {segment.segment_id: segment for result in discovery_run.results for segment in result.segments}
    manifest = CertificationManifest(
        discovery_run_id=discovery_run.run_id,
        discovery_results_sha256=discovery_run.results_sha256,
        certification_as_of=discovery_run.manifest.as_of,
        certification_source_sha256=corpus.source_sha256,
        feature_schema_version=calibration.feature_schema_version,
        calibration_profile_id=calibration.profile_id,
        calibration_sha256=payload_sha256(calibration.model_dump(mode="json")),
        partition_sha256=payload_sha256(partition.model_dump(mode="json")),
        semantic_facts_sha256=payload_sha256([fact.model_dump(mode="json") for fact in sorted(semantic_facts, key=lambda fact: fact.fact_id)]),
        format_observation_sha256=format_observation_sha256,
        outcome_feature_allowlist=CERTIFICATION_FEATURE_ALLOWLIST,
        seed=seed,
    )
    run_id = payload_sha256(manifest.model_dump(mode="json"))
    results: list[EntityCertificationResult] = []
    for result in sorted(discovery_run.results, key=lambda item: item.entity):
        reference = segments.get(result.reference_segment_id) if result.reference_segment_id else None
        entity_certificates: list[EraCertificate] = []
        for decision in sorted(decision_by_entity.get(result.entity, []), key=lambda item: item.candidate.historical_interval.start):
            candidate = decision.candidate
            entity_certificates.append(EraCertificate(
                certificate_id=_certificate_id(run_id, decision, calibration),
                entity=candidate.entity,
                candidate_id=candidate.candidate_id,
                historical_segment_id=candidate.historical_segment_id,
                reference_segment_id=candidate.reference_segment_id,
                historical_interval=candidate.historical_interval,
                reference_interval=candidate.reference_interval,
                certification_as_of=manifest.certification_as_of,
                discovery_run_id=discovery_run.run_id,
                status=decision.final_status,
                reasons=decision.reasons,
                feature_schema_version=calibration.feature_schema_version,
                calibration_profile_id=calibration.profile_id,
                partition=partition,
                semantic=decision.semantic,
                support=decision.support,
                context_overlap=decision.context_overlap,
                equivalence=decision.equivalence,
            ))
        reasons = list(result.reasons)
        if not entity_certificates and result.candidate is not None:
            reasons.append("no-certification-input")
        results.append(EntityCertificationResult(
            entity=result.entity,
            reference_segment_id=result.reference_segment_id,
            reference_interval=HalfOpenInterval(start=reference.start, end=reference.end) if reference else None,
            discovery_status=result.status,
            candidate_id=result.candidate.candidate_id if result.candidate else None,
            certificates=tuple(entity_certificates),
            reasons=tuple(dict.fromkeys(reasons)),
        ))
    results_payload = [result.model_dump(mode="json") for result in results]
    results_sha256 = payload_sha256(results_payload)
    all_certificates = [certificate for result in results for certificate in result.certificates]
    run_reasons: list[CertificationRunReason] = []
    if not candidates:
        run_reasons.append("no-recurrent-candidates")
    elif all(certificate.status != "certified" for certificate in all_certificates):
        run_reasons.append("all-inconclusive")
    if any("pending-format-truth" in result.reasons for result in results):
        run_reasons.append("format-truth-unresolved")
    status: CertificationRunStatus = "degraded" if run_reasons else "complete"
    return CertificationRun(
        run_id=run_id,
        manifest=manifest,
        results_sha256=results_sha256,
        status=status,
        reasons=tuple(dict.fromkeys(run_reasons)),
        results=tuple(results),
    )


__all__ = [
    "CERTIFICATION_FEATURE_ALLOWLIST", "EraCertificate", "EntityCertificationResult",
    "CertificationManifest", "CertificationRun", "run_recurrent_certification",
]

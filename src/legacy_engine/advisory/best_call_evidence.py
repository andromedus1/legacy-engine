"""Typed, diagnostic-only projection of interval/amplification evidence for Best Call."""

from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from typing import Literal

from legacy_engine.analytics.matchup import IntervalAdaptiveMatrix
from legacy_engine.analytics.amplification import AmplificationRun, MethodId
from legacy_engine.models.base import LegacyEngineModel

EvidenceAttachmentStatus = Literal["available", "degraded", "not-assessed", "invalid"]


class ReportIntervalSource(LegacyEngineModel):
    entity: str
    source: Literal[
        "current-reference", "certified-history", "scalar-current", "camp-current-only"
    ]
    segment_id: str | None = None
    certificate_id: str | None = None


class ReportIntervalComponent(LegacyEngineModel):
    component_id: str
    start: date | None
    end: date
    sources: tuple[ReportIntervalSource, ...]
    views: tuple[str, ...]
    current_match_n: int
    expanded_match_n: int
    added_history_match_n: int


class DirectViewDiagnostic(LegacyEngineModel):
    kind: str
    wins: int
    losses: int
    n: int
    raw: float | None
    estimate: float | None
    ci_low: float | None
    ci_high: float | None
    confidence: str
    status: str
    match_ids_sha256: str
    component_ids: tuple[str, ...]
    certificate_ids: tuple[str, ...]
    concentration: dict
    prior_audit: dict
    reasons: tuple[str, ...]


class AmplifiedDiagnostic(LegacyEngineModel):
    method_id: MethodId
    served: dict | None
    all_case_sha256: str | None
    service_state: str
    confidence: dict
    imputation: Literal["none", "partial", "full"]
    support: dict
    borrowing_concentration: dict | None
    ablations: dict
    fit_id: str
    additive_attribution: Literal[False] = False
    reasons: tuple[str, ...]


class PairEvidenceDiagnostic(LegacyEngineModel):
    subject: str
    opponent: str
    current_only: DirectViewDiagnostic
    certified_expanded: DirectViewDiagnostic
    added_history: DirectViewDiagnostic
    interval_components: tuple[ReportIntervalComponent, ...]
    challengers: tuple[AmplifiedDiagnostic, ...]
    status: EvidenceAttachmentStatus
    reasons: tuple[str, ...]


class ReportEvidenceAttachment(LegacyEngineModel):
    authority: Literal["diagnostic-only"]
    clock: dict
    certificate_run_id: str | None
    amplification_run_id: str | None
    method_ids: tuple[MethodId, ...]
    pairs: dict[str, PairEvidenceDiagnostic]
    interval_corpus_sha256: str
    authority_payload_sha256: str
    status: EvidenceAttachmentStatus
    reasons: tuple[str, ...]


def _digest(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _direct(kind: str, view) -> DirectViewDiagnostic:
    cell = view.cell
    wins = int(getattr(cell, "wins", 0) if cell is not None else 0)
    n = int(getattr(cell, "n", 0) if cell is not None else 0)
    return DirectViewDiagnostic(
        kind=kind,
        wins=wins,
        losses=n - wins,
        n=n,
        raw=getattr(cell, "p_raw", None) if cell is not None else None,
        estimate=getattr(cell, "p_shrunk", None) if cell is not None else None,
        ci_low=getattr(cell, "ci_low", None) if cell is not None else None,
        ci_high=getattr(cell, "ci_high", None) if cell is not None else None,
        confidence=str(getattr(cell, "tier", "speculative")),
        status=view.status,
        match_ids_sha256=_digest(view.match_ids),
        component_ids=view.pair_component_ids,
        certificate_ids=view.certificate_ids,
        concentration=view.concentration.model_dump(mode="json"),
        prior_audit=view.prior.model_dump(mode="json"),
        reasons=view.reasons,
    )


def build_report_evidence(
    interval: IntervalAdaptiveMatrix,
    amplification: AmplificationRun | None,
    *,
    authority_payload: dict,
) -> ReportEvidenceAttachment:
    authority_digest = _digest(authority_payload)
    methods = (
        tuple(item.method_id for item in amplification.candidates)
        if amplification
        else (
            "component-hierarchical-v1",
            "composition-kernel-v1",
            "strategic-family-ladder-v1",
            "skew-low-rank-r1-v1",
            "skew-low-rank-r2-v1",
            "skew-low-r4-v1",
        )
    )
    if amplification is not None and (
        amplification.authority != "diagnostic-only"
        or amplification.corpus.corpus_id != interval.selected_outcomes.content_sha256
    ):
        raise ValueError(
            "amplification run does not match interval corpus or diagnostic authority"
        )
    pairs = {}
    for pair, views in sorted(interval.evidence.items()):
        subject, opponent = pair
        by_method = (
            {item.method_id: item for item in amplification.candidates}
            if amplification
            else {}
        )
        candidates = []
        for method in methods:
            result = next(
                (
                    p
                    for p in by_method.get(method, ()).predictions
                    if p.subject == subject and p.opponent == opponent
                ),
                None,
            )
            if result is None:
                candidates.append(
                    AmplifiedDiagnostic(
                        method_id=method,
                        served=None,
                        all_case_sha256=None,
                        service_state="not-assessed",
                        confidence={},
                        imputation="full",
                        support={},
                        borrowing_concentration=None,
                        ablations={},
                        fit_id="",
                        reasons=("exact amplification run did not provide this pair",),
                    )
                )
            else:
                candidates.append(
                    AmplifiedDiagnostic(
                        method_id=method,
                        served=result.served.model_dump(mode="json")
                        if result.served
                        else None,
                        all_case_sha256=_digest(result.all_case.model_dump(mode="json"))
                        if result.all_case
                        else None,
                        service_state=result.service_state,
                        confidence=result.confidence.model_dump(mode="json"),
                        imputation=result.imputation,
                        support=result.support.model_dump(mode="json"),
                        borrowing_concentration=result.borrowing_concentration.model_dump(
                            mode="json"
                        )
                        if result.borrowing_concentration
                        else None,
                        ablations=result.ablations.model_dump(mode="json"),
                        fit_id=result.fit_id,
                        reasons=result.reasons,
                    )
                )
        pairs[f"{subject}::{opponent}"] = PairEvidenceDiagnostic(
            subject=subject,
            opponent=opponent,
            current_only=_direct("current-only", views.current_only),
            certified_expanded=_direct("certified-expanded", views.certified_expanded),
            added_history=_direct("added-history", views.added_history),
            interval_components=(),
            challengers=tuple(candidates),
            status="available" if amplification else "not-assessed",
            reasons=() if amplification else ("no exact amplification run requested",),
        )
    return ReportEvidenceAttachment(
        authority="diagnostic-only",
        clock=interval.clock.model_dump(mode="json"),
        certificate_run_id=interval.certificate_run_id,
        amplification_run_id=amplification.run_id if amplification else None,
        method_ids=methods,
        pairs=pairs,
        interval_corpus_sha256=interval.selected_outcomes.content_sha256,
        authority_payload_sha256=authority_digest,
        status="available" if amplification else "not-assessed",
        reasons=(),
    )

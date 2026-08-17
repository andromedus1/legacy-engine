"""Typed, diagnostic-only projection of interval/amplification evidence for Best Call."""

from __future__ import annotations

from collections.abc import Collection
from collections import Counter
from datetime import date
from hashlib import sha256
import json
from typing import Literal

from legacy_engine.analytics.amplification import (
    AMPLIFICATION_METHOD_IDS,
    AmplificationRun,
    BorrowingConcentration,
    EffectiveSupport,
    EvidenceAblations,
    MethodId,
    PredictionSummary,
    build_direct_baselines,
    build_interval_evidence_corpus,
    pair_key,
    validate_amplification_run,
)
from legacy_engine.analytics.eras.consume import AnalysisClock
from legacy_engine.analytics.match_results import (
    intersect_pair_eligibility,
    selected_rows_for_pair,
)
from legacy_engine.analytics.matchup import IntervalAdaptiveMatrix
from legacy_engine.confidence import ConfidenceMetadata
from legacy_engine.models.base import LegacyEngineModel

EvidenceAttachmentStatus = Literal["available", "degraded", "not-assessed", "invalid"]
DirectKind = Literal["current-only", "certified-expanded", "added-history"]


class ReportIntervalSource(LegacyEngineModel):
    entity: str
    source: Literal[
        "current-reference",
        "certified-history",
        "scalar-current",
        "camp-current-only",
        "localized-pre-exposure",
        "localized-post-ban",
    ]
    segment_id: str | None = None
    certificate_id: str | None = None
    certificate_run_id: str | None = None
    card: str | None = None
    exposure_start: date | None = None
    ban_date: date | None = None
    boundary_provenance: Literal[
        "released-at", "corpus-first-seen", "first-material-adoption"
    ] | None = None


class ReportIntervalComponent(LegacyEngineModel):
    component_id: str
    start: date | None
    end: date
    sources: tuple[ReportIntervalSource, ...]
    views: tuple[DirectKind, ...]
    current_match_n: int
    expanded_match_n: int
    added_history_match_n: int


class DirectViewDiagnostic(LegacyEngineModel):
    kind: DirectKind
    wins: int
    losses: int
    n: int
    raw: float | None
    estimate: float | None
    ci_low: float | None
    ci_high: float | None
    confidence: Literal["established", "evolving", "speculative"]
    status: Literal["available", "thin", "concentrated", "abstained"]
    match_ids_sha256: str
    component_ids: tuple[str, ...]
    certificate_ids: tuple[str, ...]
    concentration: "ReportEvidenceConcentration"
    prior_audit: dict
    reasons: tuple[str, ...]


class ReportEvidenceConcentration(LegacyEngineModel):
    """Compact report projection; exact count maps remain on the typed interval view."""

    raw_n: int
    distinct_events: int
    distinct_dates: int
    distinct_pilots: int | None
    pilot_identity_available: bool
    effective_events: float
    max_event_id: str | None
    max_event_share: float | None
    max_source: str | None
    max_source_share: float | None
    max_component_id: str | None
    max_component_share: float | None


class AmplifiedDiagnostic(LegacyEngineModel):
    method_id: MethodId
    served: PredictionSummary | None
    all_case_sha256: str | None
    service_state: str
    confidence: ConfidenceMetadata | None
    imputation: Literal["none", "partial", "full"] | None
    support: EffectiveSupport | None
    borrowing_concentration: BorrowingConcentration | None
    ablations: EvidenceAblations | None
    fit_id: str | None
    current_match_ids_sha256: str | None
    historical_match_ids_sha256: str | None
    borrowed_match_ids_sha256: str | None
    additive_attribution: Literal[False] = False
    reasons: tuple[str, ...]


class PairEvidenceDiagnostic(LegacyEngineModel):
    subject: str
    opponent: str
    current_only: DirectViewDiagnostic
    certified_expanded: DirectViewDiagnostic
    added_history: DirectViewDiagnostic
    best_available_direct: DirectViewDiagnostic
    best_available_basis: Literal[
        "localized-clean-direct", "certified-direct", "current-direct", "unavailable"
    ]
    interval_components: tuple[ReportIntervalComponent, ...]
    challengers: tuple[AmplifiedDiagnostic, ...]
    status: EvidenceAttachmentStatus
    reasons: tuple[str, ...]


class ReportEvidenceAttachment(LegacyEngineModel):
    authority: Literal["diagnostic-only"]
    clock: AnalysisClock
    certificate_run_id: str | None
    amplification_run_id: str | None
    amplification_profile_id: str | None
    amplification_profile_sha256: str | None
    structure_snapshot_id: str | None
    method_ids: tuple[MethodId, ...]
    pairs: dict[str, PairEvidenceDiagnostic]
    interval_corpus_sha256: str
    authority_payload_sha256: str
    status: EvidenceAttachmentStatus
    reasons: tuple[str, ...]


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_sha256(value: object) -> str:
    return sha256(canonical_json(value).encode()).hexdigest()


def _amplification_ids_digest(values: tuple[str, ...]) -> str:
    return content_sha256(sorted(set(values)))


def _direct(kind: DirectKind, view) -> DirectViewDiagnostic:
    cell = view.cell
    wins = int(cell.wins if cell is not None else 0)
    n = int(cell.n if cell is not None else 0)
    if view.prior.observation_match_ids_sha256 != sha256(
        "\n".join(sorted(view.match_ids)).encode()
    ).hexdigest():
        raise ValueError(f"{kind} match-set digest differs from exact interval view")
    prior_audit = view.prior.model_dump(mode="json")
    prior_audit["prior_match_n"] = len(prior_audit.pop("prior_match_ids", ()))
    concentration = view.concentration
    return DirectViewDiagnostic(
        kind=kind,
        wins=wins,
        losses=n - wins,
        n=n,
        raw=cell.p_raw if cell is not None else None,
        estimate=cell.p_shrunk if cell is not None else None,
        ci_low=cell.ci_low if cell is not None else None,
        ci_high=cell.ci_high if cell is not None else None,
        confidence=cell.tier if cell is not None else "speculative",
        status=view.status,
        match_ids_sha256=view.prior.observation_match_ids_sha256,
        component_ids=tuple(dict.fromkeys(view.pair_component_ids)),
        certificate_ids=view.certificate_ids,
        concentration=ReportEvidenceConcentration(
            raw_n=concentration.raw_n,
            distinct_events=concentration.distinct_events,
            distinct_dates=concentration.distinct_dates,
            distinct_pilots=concentration.distinct_pilots,
            pilot_identity_available=concentration.pilot_identity_available,
            effective_events=concentration.effective_events,
            max_event_id=concentration.max_event_id,
            max_event_share=concentration.max_event_share,
            max_source=concentration.max_source,
            max_source_share=concentration.max_source_share,
            max_component_id=concentration.max_component_id,
            max_component_share=concentration.max_component_share,
        ),
        prior_audit=prior_audit,
        reasons=view.reasons,
    )


def best_available_direct_view(
    interval: IntervalAdaptiveMatrix, subject: str, opponent: str,
):
    """Return one direct interval view and its report provenance without serializing it."""
    views = interval.evidence.get((subject, opponent))
    if views is None:
        return None, "unavailable"
    best_direct = (
        views.certified_expanded
        if views.certified_expanded.cell is not None
        and views.certified_expanded.cell.n > 0
        else views.current_only
    )
    pair = intersect_pair_eligibility(
        interval.selected_outcomes.entity_eligibility[subject],
        interval.selected_outcomes.entity_eligibility[opponent],
    )
    expanded_sources = {
        source.source for atom in pair.expanded for source in atom.sources
    }
    basis: Literal[
        "localized-clean-direct", "certified-direct", "current-direct", "unavailable"
    ] = (
        "localized-clean-direct"
        if best_direct.cell is not None
        and best_direct.cell.n > 0
        and any(source.startswith("localized-") for source in expanded_sources)
        else "certified-direct"
        if best_direct.cell is not None
        and best_direct.cell.n > 0
        and "certified-history" in expanded_sources
        else "current-direct"
        if best_direct.cell is not None and best_direct.cell.n > 0
        else "unavailable"
    )
    return best_direct, basis


def _components(
    interval: IntervalAdaptiveMatrix, subject: str, opponent: str, views
) -> tuple[ReportIntervalComponent, ...]:
    ledger = interval.selected_outcomes
    pair = intersect_pair_eligibility(
        ledger.entity_eligibility[subject], ledger.entity_eligibility[opponent]
    )
    current_atoms = {atom.component_id: atom for atom in pair.current}
    expanded_atoms = {atom.component_id: atom for atom in pair.expanded}
    rows = selected_rows_for_pair(ledger, subject, opponent)
    current_counts = Counter(
        row.pair_component_id for row in rows if row.view == "current-only"
    )
    expanded_counts = Counter(
        row.pair_component_id for row in rows if row.view == "certified-expanded"
    )
    current_ids = {row.match.match_id for row in rows if row.view == "current-only"}
    added_counts = Counter(
        row.pair_component_id
        for row in rows
        if row.view == "certified-expanded" and row.match.match_id not in current_ids
    )
    required = {
        *views.current_only.pair_component_ids,
        *views.certified_expanded.pair_component_ids,
        *views.added_history.pair_component_ids,
    }
    atoms = {**expanded_atoms, **current_atoms}
    missing = required - set(atoms)
    if missing:
        raise ValueError(f"direct component ids do not resolve to eligibility: {sorted(missing)!r}")
    result = []
    for component_id, atom in sorted(
        atoms.items(), key=lambda item: (item[1].start or date.min, item[1].end, item[0])
    ):
        component_views: list[DirectKind] = []
        if component_id in current_atoms:
            component_views.append("current-only")
        if component_id in expanded_atoms:
            component_views.append("certified-expanded")
        if added_counts[component_id]:
            component_views.append("added-history")
        result.append(
            ReportIntervalComponent(
                component_id=component_id,
                start=atom.start,
                end=atom.end,
                sources=tuple(
                    ReportIntervalSource.model_validate(source.model_dump(mode="json"))
                    for source in atom.sources
                ),
                views=tuple(component_views),
                current_match_n=current_counts[component_id],
                expanded_match_n=expanded_counts[component_id],
                added_history_match_n=added_counts[component_id],
            )
        )
    return tuple(result)


def _validate_exact_run(interval: IntervalAdaptiveMatrix, run: AmplificationRun) -> None:
    """Validate the public run and every identity tying it to this exact interval wrapper."""
    validate_amplification_run(run)
    if run.status == "failed":
        raise ValueError("failed amplification runs cannot be attached to Best Call")
    corpus = build_interval_evidence_corpus(interval)
    baselines = build_direct_baselines(interval)
    if run.authority != "diagnostic-only" or run.profile.authority != "diagnostic-only":
        raise ValueError("amplification run is not diagnostic-only")
    if run.corpus != corpus:
        raise ValueError("amplification run corpus/clock/certificate differs from report interval")
    if run.baselines != baselines:
        raise ValueError("amplification direct baselines differ from interval evidence views")
    if tuple(spec.method_id for spec in run.profile.method_specs) != AMPLIFICATION_METHOD_IDS:
        raise ValueError("amplification profile registry/order differs from the public registry")
    if not all(spec.enabled for spec in run.profile.method_specs):
        raise ValueError("Best Call requires every registered challenger method")
    if tuple(candidate.method_id for candidate in run.candidates) != AMPLIFICATION_METHOD_IDS:
        raise ValueError("amplification candidate registry/order differs from the public registry")
    if not run.comparison.fair or run.comparison.reasons:
        raise ValueError("amplification comparison audit is not fair")
    if run.structure.knowledge_as_of > interval.clock.knowledge_as_of:
        raise ValueError("amplification structure postdates the report knowledge clock")


def _challenger(candidate, prediction, views) -> AmplifiedDiagnostic:
    if prediction is None:
        if candidate.status != "failed":
            raise ValueError(
                f"method {candidate.method_id} omitted an exact pair without typed failure"
            )
        return AmplifiedDiagnostic(
            method_id=candidate.method_id,
            served=None,
            all_case_sha256=None,
            service_state="not-assessed",
            confidence=None,
            imputation=None,
            support=None,
            borrowing_concentration=None,
            ablations=None,
            fit_id=None,
            current_match_ids_sha256=None,
            historical_match_ids_sha256=None,
            borrowed_match_ids_sha256=None,
            reasons=tuple(dict.fromkeys((*candidate.reasons, "method-level-failure"))),
        )
    expected_current = _amplification_ids_digest(views.current_only.match_ids)
    expected_history = _amplification_ids_digest(views.added_history.match_ids)
    if prediction.current_match_ids_sha256 != expected_current:
        raise ValueError("challenger current match-set digest differs from interval view")
    if prediction.historical_match_ids_sha256 != expected_history:
        raise ValueError("challenger history match-set digest differs from interval view")
    if prediction.method_id != candidate.method_id or prediction.fit_id != candidate.fit_id:
        raise ValueError("challenger method/fit identity differs from candidate result")
    return AmplifiedDiagnostic(
        method_id=candidate.method_id,
        served=prediction.served,
        all_case_sha256=(
            content_sha256(prediction.all_case.model_dump(mode="json"))
            if prediction.all_case is not None
            else None
        ),
        service_state=prediction.service_state,
        confidence=prediction.confidence,
        imputation=prediction.imputation,
        support=prediction.support,
        borrowing_concentration=prediction.borrowing_concentration,
        ablations=prediction.ablations,
        fit_id=prediction.fit_id,
        current_match_ids_sha256=prediction.current_match_ids_sha256,
        historical_match_ids_sha256=prediction.historical_match_ids_sha256,
        borrowed_match_ids_sha256=prediction.borrowed_match_ids_sha256,
        reasons=prediction.reasons,
    )


def build_report_evidence(
    interval: IntervalAdaptiveMatrix,
    amplification: AmplificationRun | None,
    *,
    authority_payload: dict,
    pair_keys: Collection[tuple[str, str]] | None = None,
) -> ReportEvidenceAttachment:
    """Project exact diagnostics while proving the caller's authority payload is untouched."""
    authority_json = canonical_json(authority_payload)
    authority_digest = sha256(authority_json.encode()).hexdigest()
    # This also validates the selected ledger and exact evidence memberships on the no-run path.
    build_interval_evidence_corpus(interval)
    if amplification is not None:
        _validate_exact_run(interval, amplification)
    candidate_by_method = (
        {candidate.method_id: candidate for candidate in amplification.candidates}
        if amplification is not None
        else {}
    )
    requested_pairs = frozenset(pair_keys) if pair_keys is not None else None
    pairs: dict[str, PairEvidenceDiagnostic] = {}
    for (subject, opponent), views in sorted(interval.evidence.items()):
        if requested_pairs is not None and (subject, opponent) not in requested_pairs:
            continue
        challengers = []
        pair_reasons: list[str] = []
        for method in AMPLIFICATION_METHOD_IDS:
            candidate = candidate_by_method.get(method)
            if candidate is None:
                challengers.append(
                    AmplifiedDiagnostic(
                        method_id=method,
                        served=None,
                        all_case_sha256=None,
                        service_state="not-assessed",
                        confidence=None,
                        imputation=None,
                        support=None,
                        borrowing_concentration=None,
                        ablations=None,
                        fit_id=None,
                        current_match_ids_sha256=None,
                        historical_match_ids_sha256=None,
                        borrowed_match_ids_sha256=None,
                        reasons=("no exact amplification run requested",),
                    )
                )
                continue
            prediction = next(
                (
                    value
                    for value in candidate.predictions
                    if value.subject == subject and value.opponent == opponent
                ),
                None,
            )
            diagnostic = _challenger(candidate, prediction, views)
            challengers.append(diagnostic)
            pair_reasons.extend(candidate.reasons)
        components = _components(interval, subject, opponent, views)
        pair_reasons.extend(views.certified_expanded.reasons)
        is_camp = any(
            source.source == "camp-current-only"
            for component in components
            for source in component.sources
        )
        if is_camp and (
            views.current_only.match_ids != views.certified_expanded.match_ids
            or views.added_history.match_ids
            or views.certified_expanded.certificate_ids
        ):
            raise ValueError("camp observations must remain current-only")
        if is_camp:
            pair_reasons.append("camp-current-only")
        pair_status: EvidenceAttachmentStatus
        if amplification is None:
            pair_status = "not-assessed"
            pair_reasons.append("no exact amplification run requested")
        elif amplification.status == "degraded" or any(
            candidate.status != "complete" for candidate in amplification.candidates
        ):
            pair_status = "degraded"
        else:
            pair_status = "available"
        best_direct, best_basis = best_available_direct_view(
            interval, subject, opponent,
        )
        assert best_direct is not None
        pairs[pair_key(subject, opponent)] = PairEvidenceDiagnostic(
            subject=subject,
            opponent=opponent,
            current_only=_direct("current-only", views.current_only),
            certified_expanded=_direct("certified-expanded", views.certified_expanded),
            added_history=_direct("added-history", views.added_history),
            best_available_direct=_direct(
                "certified-expanded"
                if best_direct is views.certified_expanded
                else "current-only",
                best_direct,
            ),
            best_available_basis=best_basis,
            interval_components=components,
            challengers=tuple(challengers),
            status=pair_status,
            reasons=tuple(dict.fromkeys(pair_reasons)),
        )
    if canonical_json(authority_payload) != authority_json:
        raise RuntimeError("evidence projection mutated the authoritative ranking payload")
    status: EvidenceAttachmentStatus = (
        "not-assessed"
        if amplification is None
        else "degraded"
        if amplification.status == "degraded"
        or any(candidate.status != "complete" for candidate in amplification.candidates)
        else "available"
    )
    reasons = (
        ("no exact amplification run requested",)
        if amplification is None
        else tuple(
            dict.fromkeys(
                (*amplification.reasons, *(reason for c in amplification.candidates for reason in c.reasons))
            )
        )
    )
    return ReportEvidenceAttachment(
        authority="diagnostic-only",
        clock=interval.clock,
        certificate_run_id=interval.certificate_run_id,
        amplification_run_id=amplification.run_id if amplification else None,
        amplification_profile_id=amplification.profile_id if amplification else None,
        amplification_profile_sha256=amplification.profile_sha256 if amplification else None,
        structure_snapshot_id=amplification.structure_snapshot_id if amplification else None,
        method_ids=AMPLIFICATION_METHOD_IDS,
        pairs=pairs,
        interval_corpus_sha256=interval.selected_outcomes.content_sha256,
        authority_payload_sha256=authority_digest,
        status=status,
        reasons=reasons,
    )

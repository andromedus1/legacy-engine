"""Outcome-free recurrent-era certification contracts and pure gates.

The module is deliberately free of DuckDB access.  ``certification_source``
owns reconstruction of the held-out corpus and the run/ledger modules own
persistence; this keeps the statistical boundary usable with deterministic
hand-built corpora and makes accidental outcome access difficult.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import Field, field_validator, model_validator

from legacy_engine.analytics.eras.discovery import (
    DiscoveryDeck,
    OutcomeFreeCorpus,
    OutcomeFreeModel,
    canonical_json,
    payload_sha256,
)
from legacy_engine.analytics.eras.discovery_run import DiscoveryRun

PartitionRole = Literal["discovery", "certification"]
ProfileState = Literal["candidate", "promoted"]


class EventPartitionPlan(OutcomeFreeModel):
    plan_id: str
    salt: str
    modulus: int = Field(gt=1)
    discovery_buckets: tuple[int, ...]

    @field_validator("plan_id", "salt")
    @classmethod
    def _nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("partition plan text must be non-empty")
        return value

    @model_validator(mode="after")
    def _valid_buckets(self) -> "EventPartitionPlan":
        buckets = tuple(self.discovery_buckets)
        if not buckets:
            raise ValueError("discovery_buckets must be non-empty")
        if len(set(buckets)) != len(buckets):
            raise ValueError("discovery_buckets must be unique")
        if any(bucket < 0 or bucket >= self.modulus for bucket in buckets):
            raise ValueError("discovery_buckets must be inside [0, modulus)")
        if len(buckets) >= self.modulus:
            raise ValueError("discovery_buckets must be a proper subset of partition buckets")
        return self


class PartitionManifest(OutcomeFreeModel):
    plan_id: str
    rule_sha256: str
    discovery_event_ids_sha256: str
    certification_event_ids_sha256: str
    discovery_events: int = Field(ge=0)
    certification_events: int = Field(ge=0)

    @field_validator("plan_id")
    @classmethod
    def _plan_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("partition manifest plan_id must be non-empty")
        return value

    @field_validator("rule_sha256", "discovery_event_ids_sha256", "certification_event_ids_sha256")
    @classmethod
    def _sha(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("partition manifest digests must be lowercase SHA-256 values")
        return value


class EquivalenceMargins(OutcomeFreeModel):
    main_js: float = Field(gt=0)
    side_js: float = Field(gt=0)
    mixture_energy: float = Field(gt=0)
    field_js: float = Field(gt=0)
    source_js: float = Field(gt=0)
    omnibus_mmd2: float = Field(gt=0)

    @model_validator(mode="after")
    def _finite(self) -> "EquivalenceMargins":
        for name, value in self.model_dump().items():
            if not math.isfinite(value):
                raise ValueError(f"equivalence margin {name} must be finite")
        return self


class CertificationCalibration(OutcomeFreeModel):
    profile_id: str
    profile_state: ProfileState
    method_id: Literal["cluster-bootstrap-equivalence-v1"]
    feature_schema_version: Literal["recurrent-certification-features-v1"]
    control_evidence_sha256: str
    partition: EventPartitionPlan
    family_alpha: float = Field(gt=0, lt=1)
    bootstrap_replicates: int = Field(gt=0)
    min_candidate_events: int = Field(gt=0)
    min_reference_events: int = Field(gt=0)
    min_time_buckets: int = Field(gt=0)
    min_effective_events: float = Field(gt=0)
    max_event_share: float = Field(gt=0, le=1)
    max_source_share: float = Field(gt=0, le=1)
    max_context_weight: float = Field(gt=0)
    max_unsupported_context_share: float = Field(ge=0, le=1)
    context_smoothing: float = Field(gt=0)
    rbf_bandwidth: float = Field(gt=0)
    margins: EquivalenceMargins

    @field_validator("profile_id")
    @classmethod
    def _profile_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("profile_id must be non-empty")
        return value

    @field_validator("control_evidence_sha256")
    @classmethod
    def _control_digest(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("control_evidence_sha256 must be a lowercase SHA-256 digest")
        if value == "0" * 64:
            raise ValueError("control_evidence_sha256 must identify checked-in controls")
        return value

    @model_validator(mode="after")
    def _finite(self) -> "CertificationCalibration":
        for name, value in self.model_dump().items():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"calibration {name} must be finite")
        return self


class PartitionedOutcomeFreeCorpus(OutcomeFreeModel):
    manifest: PartitionManifest
    discovery: OutcomeFreeCorpus
    certification: OutcomeFreeCorpus


GateDisposition = Literal["pass", "reject", "abstain"]
CertificationStatus = Literal["certified", "rejected", "inconclusive"]
CertificationReason = Literal[
    "unpromoted-calibration", "confirmed-affectedness", "legality-incompatible",
    "taxonomy-incompatible", "source-contract-incompatible", "pending-format-truth",
    "format-truth-unavailable", "insufficient-candidate-events", "insufficient-reference-events",
    "insufficient-time-buckets", "effective-support-below-floor", "event-concentration",
    "source-concentration", "context-overlap-failed",
    "equivalence-straddles-margin", "component-non-equivalent", "omnibus-non-equivalent",
]
SemanticFactState = Literal["confirmed", "pending", "unavailable"]
SemanticFactKind = Literal["affectedness", "legality", "taxonomy", "source-contract"]


class HalfOpenInterval(OutcomeFreeModel):
    start: date
    end: date

    @model_validator(mode="after")
    def _ordered(self) -> "HalfOpenInterval":
        if self.end <= self.start:
            raise ValueError("half-open interval end must be after start")
        return self


class SemanticFact(OutcomeFreeModel):
    fact_id: str
    kind: SemanticFactKind
    state: SemanticFactState
    effective_on: date
    affected_entities: tuple[str, ...]
    source: Literal["curated-ban-ledger", "frozen-contract", "format-monitor"]
    evidence_sha256: str
    detail: str

    @field_validator("fact_id", "detail")
    @classmethod
    def _fact_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("semantic fact text must be non-empty")
        return value

    @field_validator("evidence_sha256")
    @classmethod
    def _fact_digest(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("semantic fact evidence_sha256 must be lowercase SHA-256")
        return value


class CandidateCertificationInput(OutcomeFreeModel):
    entity: str
    candidate_id: str
    historical_segment_id: str
    reference_segment_id: str
    historical_interval: HalfOpenInterval
    reference_interval: HalfOpenInterval
    candidate_decks: tuple[DiscoveryDeck, ...]
    reference_decks: tuple[DiscoveryDeck, ...]
    candidate_context_decks: tuple[DiscoveryDeck, ...]
    reference_context_decks: tuple[DiscoveryDeck, ...]


class SemanticGuardEvidence(OutcomeFreeModel):
    disposition: GateDisposition
    crossed_fact_ids: tuple[str, ...]
    confirmed_veto_ids: tuple[str, ...]
    unresolved_fact_ids: tuple[str, ...]
    reasons: tuple[CertificationReason, ...]


class SupportEvidence(OutcomeFreeModel):
    disposition: GateDisposition
    candidate_decks: int = Field(ge=0)
    reference_decks: int = Field(ge=0)
    candidate_events: int = Field(ge=0)
    reference_events: int = Field(ge=0)
    time_buckets: int = Field(ge=0)
    effective_events: float = Field(ge=0)
    max_event_share: float | None = Field(default=None, ge=0, le=1)
    max_source_share: float | None = Field(default=None, ge=0, le=1)
    reasons: tuple[CertificationReason, ...]


class ContextOverlapEvidence(OutcomeFreeModel):
    disposition: GateDisposition
    effective_events: float | None = Field(default=None, ge=0)
    max_stabilized_weight: float | None = Field(default=None, ge=0)
    unsupported_reference_share: float | None = Field(default=None, ge=0, le=1)
    vocabulary_sha256: str
    reasons: tuple[CertificationReason, ...]


EquivalenceChannel = Literal[
    "main-js", "side-js", "mixture-energy", "field-js", "source-js", "omnibus-mmd2"
]


class EquivalenceBand(OutcomeFreeModel):
    channel: EquivalenceChannel
    estimate: float = Field(ge=0)
    margin: float = Field(gt=0)
    normalized_estimate: float = Field(ge=0)
    simultaneous_lower: float = Field(ge=0)
    simultaneous_upper: float = Field(ge=0)
    disposition: GateDisposition


class EquivalenceEvidence(OutcomeFreeModel):
    disposition: GateDisposition
    family_id: str
    method_id: str
    family_alpha: float
    bootstrap_replicates: int
    critical_value: float = Field(ge=0)
    channels: tuple[EquivalenceBand, ...]
    reasons: tuple[CertificationReason, ...]


class CandidateDecision(OutcomeFreeModel):
    candidate: CandidateCertificationInput
    semantic: SemanticGuardEvidence
    support: SupportEvidence
    context_overlap: ContextOverlapEvidence
    equivalence: EquivalenceEvidence | None
    statistical_status: CertificationStatus
    final_status: CertificationStatus
    reasons: tuple[CertificationReason, ...]


def _partition_rule_sha256(plan: EventPartitionPlan) -> str:
    return payload_sha256({"plan_id": plan.plan_id, "salt": plan.salt, "modulus": plan.modulus,
                           "discovery_buckets": tuple(sorted(plan.discovery_buckets))})


def _event_ids_sha256(event_ids: Sequence[str]) -> str:
    return payload_sha256(tuple(sorted(set(str(event_id) for event_id in event_ids))))


def load_certification_calibration(path: Path | str) -> CertificationCalibration:
    import json
    import hashlib

    calibration_path = Path(path)
    try:
        raw = json.loads(calibration_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid certification calibration {calibration_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"invalid certification calibration {calibration_path}: expected object")
    try:
        calibration = CertificationCalibration.model_validate(raw)
        controls_path = calibration_path.with_name("certification-controls-v1.json")
        if not controls_path.exists():
            raise ValueError(f"checked-in control fixture missing beside {calibration_path}")
        observed = hashlib.sha256(controls_path.read_bytes()).hexdigest()
        if observed != calibration.control_evidence_sha256:
            raise ValueError(
                f"control evidence digest mismatch: profile names {calibration.control_evidence_sha256}, "
                f"checked-in controls hash to {observed}"
            )
        return calibration
    except Exception as exc:
        raise ValueError(f"invalid certification calibration {calibration_path}: {exc}") from exc


def partition_role(event_id: str, plan: EventPartitionPlan) -> PartitionRole:
    """Return an atomic event role using canonical plan/event bytes."""

    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("event_id must be non-empty")
    payload = canonical_json((plan.plan_id, plan.salt, event_id.strip())).encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(payload).digest(), "big") % plan.modulus
    return "discovery" if bucket in plan.discovery_buckets else "certification"


def partition_outcome_free_corpus(
    corpus: OutcomeFreeCorpus,
    plan: EventPartitionPlan,
) -> PartitionedOutcomeFreeCorpus:
    """Split a corpus by whole event, preserving all corpus metadata."""

    from legacy_engine.analytics.eras.discovery import _canonical_corpus_payload

    roles: dict[str, PartitionRole] = {}
    for deck in corpus.decks:
        role = partition_role(deck.event_id, plan)
        prior = roles.setdefault(deck.event_id, role)
        if prior != role:  # impossible for a pure function, guards malformed input explicitly
            raise ValueError(f"event {deck.event_id!r} received multiple partition roles")

    def build(role: PartitionRole) -> OutcomeFreeCorpus:
        decks = tuple(sorted((deck for deck in corpus.decks if roles[deck.event_id] == role),
                             key=lambda deck: (deck.event_date, deck.event_id, deck.deck_idx)))
        payload = _canonical_corpus_payload(
            as_of=corpus.as_of,
            taxonomy_version=corpus.taxonomy_version,
            legality_version=corpus.legality_version,
            provenance_filter=corpus.provenance_filter,
            semantic_boundaries=corpus.semantic_boundaries,
            decks=decks,
        )
        return corpus.model_copy(update={"decks": decks, "source_sha256": payload_sha256(payload)})

    discovery = build("discovery")
    certification = build("certification")
    discovery_ids = tuple(sorted({deck.event_id for deck in discovery.decks}))
    certification_ids = tuple(sorted({deck.event_id for deck in certification.decks}))
    if set(discovery_ids) & set(certification_ids):
        raise ValueError("partition event roles overlap")
    all_ids = tuple(sorted({deck.event_id for deck in corpus.decks}))
    if set(discovery_ids) | set(certification_ids) != set(all_ids):
        raise ValueError("partition event roles do not cover the source corpus")
    manifest = PartitionManifest(
        plan_id=plan.plan_id,
        rule_sha256=_partition_rule_sha256(plan),
        discovery_event_ids_sha256=_event_ids_sha256(discovery_ids),
        certification_event_ids_sha256=_event_ids_sha256(certification_ids),
        discovery_events=len(discovery_ids),
        certification_events=len(certification_ids),
    )
    return PartitionedOutcomeFreeCorpus(manifest=manifest, discovery=discovery, certification=certification)


def _decks_unique(decks: Sequence[DiscoveryDeck]) -> tuple[DiscoveryDeck, ...]:
    """Deduplicate at the event/deck boundary before support is counted."""

    return tuple({(deck.event_id, deck.deck_idx): deck for deck in decks}.values())


def _in_interval(deck: DiscoveryDeck, interval: HalfOpenInterval) -> bool:
    return interval.start <= deck.event_date < interval.end


def build_candidate_inputs(
    discovery_run: DiscoveryRun,
    corpus: OutcomeFreeCorpus,
) -> tuple[CandidateCertificationInput, ...]:
    """Materialize held-out candidates from immutable discovery segment ids."""

    by_segment = {
        segment.segment_id: segment
        for result in discovery_run.results
        for segment in result.segments
    }
    discovery_event_ids = {event_id for segment in by_segment.values() for event_id in segment.event_ids}
    leaked_events = discovery_event_ids & {deck.event_id for deck in corpus.decks}
    if leaked_events:
        raise ValueError("certification corpus contains discovery-role events")
    inputs: list[CandidateCertificationInput] = []
    for result in discovery_run.results:
        if result.candidate is None or result.status != "candidate":
            continue
        reference = by_segment.get(result.candidate.reference_segment_id)
        if reference is None:
            raise ValueError(f"discovery result {result.entity} references missing reference segment")
        for historical_id in result.candidate.historical_segment_ids:
            historical = by_segment.get(historical_id)
            if historical is None:
                raise ValueError(f"discovery result {result.entity} references missing historical segment")
            candidate_decks = tuple(sorted(
                (deck for deck in corpus.decks if deck.parent_archetype == result.entity
                 and historical.start <= deck.event_date < historical.end),
                key=lambda deck: (deck.event_date, deck.event_id, deck.deck_idx),
            ))
            reference_decks = tuple(sorted(
                (deck for deck in corpus.decks if deck.parent_archetype == result.entity
                 and reference.start <= deck.event_date < reference.end),
                key=lambda deck: (deck.event_date, deck.event_id, deck.deck_idx),
            ))
            # Context is intentionally the complete labeled field in each
            # interval; it is used only for overlap diagnostics.
            candidate_context = tuple(sorted(
                (deck for deck in corpus.decks if historical.start <= deck.event_date < historical.end),
                key=lambda deck: (deck.event_date, deck.event_id, deck.deck_idx),
            ))
            reference_context = tuple(sorted(
                (deck for deck in corpus.decks if reference.start <= deck.event_date < reference.end),
                key=lambda deck: (deck.event_date, deck.event_id, deck.deck_idx),
            ))
            inputs.append(CandidateCertificationInput(
                entity=result.entity,
                candidate_id=result.candidate.candidate_id,
                historical_segment_id=historical.segment_id,
                reference_segment_id=reference.segment_id,
                historical_interval=HalfOpenInterval(start=historical.start, end=historical.end),
                reference_interval=HalfOpenInterval(start=reference.start, end=reference.end),
                candidate_decks=candidate_decks,
                reference_decks=reference_decks,
                candidate_context_decks=candidate_context,
                reference_context_decks=reference_context,
            ))
    return tuple(sorted(inputs, key=lambda item: (item.entity, item.historical_interval.start, item.historical_segment_id)))


def _fact_crosses(candidate: CandidateCertificationInput, fact: SemanticFact) -> bool:
    # A semantic boundary anywhere from the historical start through the
    # current endpoint breaks the reunion.  This includes the excluded gap
    # between non-contiguous intervals, not only facts observed in either
    # sample.
    return candidate.historical_interval.start <= fact.effective_on < candidate.reference_interval.end


def evaluate_semantic_guards(
    candidate: CandidateCertificationInput,
    facts: Sequence[SemanticFact],
) -> SemanticGuardEvidence:
    crossed = tuple(sorted((fact for fact in facts if _fact_crosses(candidate, fact)), key=lambda fact: fact.fact_id))
    crossed_ids = tuple(fact.fact_id for fact in crossed)
    vetoes: list[str] = []
    unresolved: list[str] = []
    reasons: list[CertificationReason] = []
    reason_by_kind = {
        "affectedness": "confirmed-affectedness",
        "legality": "legality-incompatible",
        "taxonomy": "taxonomy-incompatible",
        "source-contract": "source-contract-incompatible",
    }
    for fact in crossed:
        if candidate.entity not in fact.affected_entities and "*" not in fact.affected_entities:
            continue
        authoritative = fact.source in {"curated-ban-ledger", "frozen-contract"}
        if fact.state == "confirmed" and authoritative:
            vetoes.append(fact.fact_id)
            reasons.append(reason_by_kind[fact.kind])
        else:
            unresolved.append(fact.fact_id)
            reasons.append("pending-format-truth" if fact.state in {"pending", "confirmed"} else "format-truth-unavailable")
    reasons = list(dict.fromkeys(reasons))
    disposition: GateDisposition = "reject" if vetoes else ("abstain" if unresolved else "pass")
    return SemanticGuardEvidence(
        disposition=disposition,
        crossed_fact_ids=crossed_ids,
        confirmed_veto_ids=tuple(vetoes),
        unresolved_fact_ids=tuple(unresolved),
        reasons=tuple(reasons),
    )


def _event_stats(decks: Sequence[DiscoveryDeck]) -> tuple[int, float | None, float | None, float]:
    unique = _decks_unique(decks)
    by_event: dict[str, set[tuple[str, int]]] = {}
    by_source: dict[str, set[tuple[str, int]]] = {}
    for deck in unique:
        key = (deck.event_id, deck.deck_idx)
        by_event.setdefault(deck.event_id, set()).add(key)
        by_source.setdefault(deck.source.casefold(), set()).add(key)
    events = len(by_event)
    weights = [float(len(keys)) for keys in by_event.values()]
    total = sum(weights)
    effective = (total * total / sum(weight * weight for weight in weights)) if weights else 0.0
    return (
        events,
        max((weight / total for weight in weights), default=None),
        max((len(keys) / len(unique) for keys in by_source.values()), default=None),
        effective,
    )


def evaluate_support(
    candidate: CandidateCertificationInput,
    calibration: CertificationCalibration,
    *,
    seed: int,
) -> SupportEvidence:
    del seed  # power is deterministic from frozen support in certification v1
    old = _decks_unique(candidate.candidate_decks)
    ref = _decks_unique(candidate.reference_decks)
    candidate_events, candidate_event_share, candidate_source_share, candidate_effective = _event_stats(old)
    reference_events, reference_event_share, reference_source_share, reference_effective = _event_stats(ref)
    time_buckets = len({
        deck.event_date - timedelta(days=deck.event_date.isoweekday() - 1)
        for deck in (*old, *ref)
    })
    # Whole-event effective support.  Duplicated deck rows are removed before
    # this calculation, so publishing a duplicate cannot manufacture power.
    effective_events = float(min(candidate_effective, reference_effective))
    reasons: list[CertificationReason] = []
    if candidate_events < calibration.min_candidate_events:
        reasons.append("insufficient-candidate-events")
    if reference_events < calibration.min_reference_events:
        reasons.append("insufficient-reference-events")
    if time_buckets < calibration.min_time_buckets:
        reasons.append("insufficient-time-buckets")
    if effective_events < calibration.min_effective_events:
        reasons.append("effective-support-below-floor")
    if candidate_event_share is not None and candidate_event_share > calibration.max_event_share:
        reasons.append("event-concentration")
    if reference_event_share is not None and reference_event_share > calibration.max_event_share:
        reasons.append("event-concentration")
    if candidate_source_share is not None and candidate_source_share > calibration.max_source_share:
        reasons.append("source-concentration")
    if reference_source_share is not None and reference_source_share > calibration.max_source_share:
        reasons.append("source-concentration")
    return SupportEvidence(
        disposition="abstain" if reasons else "pass",
        candidate_decks=len(old), reference_decks=len(ref),
        candidate_events=candidate_events, reference_events=reference_events,
        time_buckets=time_buckets, effective_events=effective_events,
        max_event_share=max(candidate_event_share or 0.0, reference_event_share or 0.0) if old or ref else None,
        max_source_share=max(candidate_source_share or 0.0, reference_source_share or 0.0) if old or ref else None,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def _context_distribution(decks: Sequence[DiscoveryDeck], key: str, smoothing: float) -> dict[str, float]:
    values = [getattr(deck, key).casefold() for deck in _decks_unique(decks)]
    vocabulary = sorted(set(values))
    if not vocabulary:
        return {}
    denominator = len(values) + smoothing * len(vocabulary)
    return {value: (values.count(value) + smoothing) / denominator for value in vocabulary}


def evaluate_context_overlap(
    candidate: CandidateCertificationInput,
    calibration: CertificationCalibration,
) -> ContextOverlapEvidence:
    old = _decks_unique(candidate.candidate_context_decks)
    ref = _decks_unique(candidate.reference_context_decks)
    # Context vocabulary is the cross-product of field parent and source.  A
    # category absent in the candidate gets only smoothing mass, making its
    # stabilized reference weight visible rather than silently clipping it.
    def labels(deck: DiscoveryDeck) -> str:
        return f"{deck.parent_archetype.casefold()}|{deck.source.casefold()}"
    old_labels = [labels(deck) for deck in old]
    ref_labels = [labels(deck) for deck in ref]
    vocabulary = sorted(set(old_labels) | set(ref_labels))
    vocabulary_sha256 = payload_sha256(tuple(vocabulary))
    old_count = {label: old_labels.count(label) for label in vocabulary}
    ref_count = {label: ref_labels.count(label) for label in vocabulary}
    smoothing = calibration.context_smoothing
    old_den = len(old_labels) + smoothing * len(vocabulary)
    ref_den = len(ref_labels) + smoothing * len(vocabulary)
    old_prob = {label: (old_count[label] + smoothing) / old_den if old_den else 0.0 for label in vocabulary}
    ref_prob = {label: (ref_count[label] + smoothing) / ref_den if ref_den else 0.0 for label in vocabulary}
    unsupported = sum(ref_prob[label] for label in vocabulary if old_count[label] == 0)
    ref_by_event: dict[str, list[str]] = {}
    for deck in ref:
        ref_by_event.setdefault(deck.event_id, []).append(labels(deck))
    # Context overlap is event-weighted as well: a large event contributes one
    # cluster weight, while repeated deck rows cannot manufacture effective
    # independent support.
    weights = [sum(ref_prob.get(label, 0.0) / old_prob.get(label, 1.0) for label in labels_for_event)
               for labels_for_event in ref_by_event.values()]
    sum_weights = sum(weights)
    effective = (sum_weights * sum_weights / sum(weight * weight for weight in weights)) if weights else 0.0
    max_weight = max(weights, default=None)
    reasons: list[CertificationReason] = []
    if not old or not ref or effective < calibration.min_effective_events:
        reasons.append("context-overlap-failed")
    if max_weight is not None and max_weight > calibration.max_context_weight:
        reasons.append("context-overlap-failed")
    if unsupported > calibration.max_unsupported_context_share:
        reasons.append("context-overlap-failed")
    return ContextOverlapEvidence(
        disposition="abstain" if reasons else "pass",
        effective_events=effective if weights else None,
        max_stabilized_weight=max_weight,
        unsupported_reference_share=unsupported if ref else None,
        vocabulary_sha256=vocabulary_sha256,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def _mass(decks: Sequence[DiscoveryDeck], board: Literal["main", "side"], smoothing: float) -> dict[str, float]:
    """Return raw board counts; smoothing happens once in ``_js``."""
    counts: dict[str, float] = {}
    for deck in decks:
        cards = deck.mainboard if board == "main" else deck.sideboard
        for card in cards:
            key = card.name.casefold()
            counts[key] = counts.get(key, 0.0) + card.copies
    return counts


def _js(left: dict[str, float], right: dict[str, float], smoothing: float) -> float:
    if not left or not right:
        return float("nan")
    names = sorted(set(left) | set(right))
    # The same union vocabulary and one pseudocount per category are used for
    # both samples.  Smoothing each side's local vocabulary before union would
    # make the result depend on the arbitrary feature dimension.
    p = np.array([left.get(name, 0.0) + smoothing for name in names], dtype=float)
    q = np.array([right.get(name, 0.0) + smoothing for name in names], dtype=float)
    p /= p.sum()
    q /= q.sum()
    midpoint = (p + q) / 2.0
    return float(max(0.0, 0.5 * ((p * np.log2(p / midpoint)).sum() + (q * np.log2(q / midpoint)).sum())))


def _energy(left: Sequence[DiscoveryDeck], right: Sequence[DiscoveryDeck]) -> float:
    decks = (*left, *right)
    vocabulary = sorted({card.name.casefold() for deck in decks for card in (*deck.mainboard, *deck.sideboard)})
    if not vocabulary or not left or not right:
        return float("nan")

    def vector(deck: DiscoveryDeck) -> np.ndarray:
        values = []
        for board in (deck.mainboard, deck.sideboard):
            board_total = sum(card.copies for card in board)
            lookup = {card.name.casefold(): card.copies for card in board}
            values.extend((lookup.get(name, 0) / board_total if board_total else 0.0) for name in vocabulary)
        return np.asarray(values, dtype=float)

    x = np.asarray([vector(deck) for deck in left])
    y = np.asarray([vector(deck) for deck in right])
    cross = np.linalg.norm(x[:, None, :] - y[None, :, :], axis=2).mean()
    within_x = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2).mean()
    within_y = np.linalg.norm(y[:, None, :] - y[None, :, :], axis=2).mean()
    return float(max(0.0, min(1.0, (2.0 * cross - within_x - within_y) / math.sqrt(2.0))))


def _context_mass(decks: Sequence[DiscoveryDeck], key: Literal["parent_archetype", "source"], smoothing: float) -> dict[str, float]:
    values = [getattr(deck, key).casefold() for deck in decks]
    return {value: values.count(value) for value in set(values)}


def _mmd2(left: Sequence[DiscoveryDeck], right: Sequence[DiscoveryDeck], bandwidth: float) -> float:
    decks = (*left, *right)
    vocabulary = sorted({card.name.casefold() for deck in decks for card in (*deck.mainboard, *deck.sideboard)})
    if not vocabulary or not left or not right:
        return float("nan")

    def vector(deck: DiscoveryDeck) -> np.ndarray:
        values = []
        for board in (deck.mainboard, deck.sideboard):
            total = sum(card.copies for card in board)
            lookup = {card.name.casefold(): card.copies for card in board}
            values.extend((lookup.get(name, 0) / total if total else 0.0) for name in vocabulary)
        return np.asarray(values, dtype=float)

    x = np.asarray([vector(deck) for deck in left])
    y = np.asarray([vector(deck) for deck in right])

    def kernel(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        distance = np.sum((a[:, None, :] - b[None, :, :]) ** 2, axis=2)
        return np.exp(-distance / (2.0 * bandwidth * bandwidth))

    value = kernel(x, x).mean() + kernel(y, y).mean() - 2.0 * kernel(x, y).mean()
    return float(max(0.0, value))


def estimate_candidate_discrepancies(
    candidate: CandidateCertificationInput,
    calibration: CertificationCalibration,
) -> dict[EquivalenceChannel, float]:
    """Compute every declared outcome-free discrepancy independently."""

    return {
        "main-js": _js(_mass(candidate.candidate_decks, "main", calibration.context_smoothing),
                       _mass(candidate.reference_decks, "main", calibration.context_smoothing),
                       calibration.context_smoothing),
        "side-js": _js(_mass(candidate.candidate_decks, "side", calibration.context_smoothing),
                       _mass(candidate.reference_decks, "side", calibration.context_smoothing),
                       calibration.context_smoothing),
        "mixture-energy": _energy(candidate.candidate_decks, candidate.reference_decks),
        "field-js": _js(_context_mass(candidate.candidate_context_decks, "parent_archetype", calibration.context_smoothing),
                        _context_mass(candidate.reference_context_decks, "parent_archetype", calibration.context_smoothing),
                        calibration.context_smoothing),
        "source-js": _js(_context_mass(candidate.candidate_context_decks, "source", calibration.context_smoothing),
                         _context_mass(candidate.reference_context_decks, "source", calibration.context_smoothing),
                         calibration.context_smoothing),
        "omnibus-mmd2": _mmd2(candidate.candidate_decks, candidate.reference_decks, calibration.rbf_bandwidth),
    }


_MARGIN_FIELD: dict[EquivalenceChannel, str] = {
    "main-js": "main_js", "side-js": "side_js", "mixture-energy": "mixture_energy",
    "field-js": "field_js", "source-js": "source_js", "omnibus-mmd2": "omnibus_mmd2",
}


def _resample_events(decks: Sequence[DiscoveryDeck], rng: np.random.Generator) -> tuple[DiscoveryDeck, ...]:
    groups: dict[str, list[DiscoveryDeck]] = {}
    for deck in decks:
        groups.setdefault(deck.event_id, []).append(deck)
    if not groups:
        return ()
    event_ids = sorted(groups)
    sampled = rng.choice(len(event_ids), size=len(event_ids), replace=True)
    result: list[DiscoveryDeck] = []
    for index in sampled:
        result.extend(groups[event_ids[int(index)]])
    return tuple(sorted(result, key=lambda deck: (deck.event_date, deck.event_id, deck.deck_idx)))


def certify_candidate_family(
    candidates: Sequence[CandidateCertificationInput],
    facts: Sequence[SemanticFact],
    calibration: CertificationCalibration,
    *,
    seed: int = 0,
) -> tuple[CandidateDecision, ...]:
    """Apply ordered guards and one normalized whole-family bootstrap band."""

    ordered = tuple(sorted(candidates, key=lambda item: (item.entity, item.historical_interval.start, item.historical_segment_id)))
    family_id = "family-" + payload_sha256(tuple(item.candidate_id + ":" + item.historical_segment_id for item in ordered))[:24]
    guards: list[tuple[CandidateCertificationInput, SemanticGuardEvidence, SupportEvidence, ContextOverlapEvidence]] = []
    estimates: dict[str, dict[EquivalenceChannel, float]] = {}
    for candidate in ordered:
        semantic = evaluate_semantic_guards(candidate, facts)
        support = evaluate_support(candidate, calibration, seed=seed)
        context = evaluate_context_overlap(candidate, calibration)
        guards.append((candidate, semantic, support, context))
        # The simultaneous family is frozen before guards are applied.  Even
        # an abstaining member contributes its channels to the max statistic;
        # removing it adaptively would make multiplicity look safer than it is.
        estimates[candidate.historical_segment_id] = estimate_candidate_discrepancies(candidate, calibration)

    # Build a single max-statistic distribution over every eligible candidate
    # and channel.  Canonical candidate ids seed independent resampling, so
    # changing input order cannot alter any evidence.
    maxima: list[float] = []
    reference_by_segment = {}
    context_reference_by_segment = {}
    for candidate in ordered:
        reference_by_segment.setdefault(candidate.reference_segment_id, candidate.reference_decks)
        context_reference_by_segment.setdefault(candidate.reference_segment_id, candidate.reference_context_decks)
    for replicate in range(calibration.bootstrap_replicates):
        maximum = 0.0
        shared_reference: dict[str, tuple[DiscoveryDeck, ...]] = {}
        shared_context_reference: dict[str, tuple[DiscoveryDeck, ...]] = {}
        for candidate, semantic, support, context in guards:
            key = candidate.historical_segment_id
            local_seed = int.from_bytes(hashlib.sha256(
                f"{seed}:{candidate.candidate_id}:{key}:{replicate}".encode("utf-8")
            ).digest()[:8], "big")
            rng = np.random.default_rng(local_seed)
            reference_key = candidate.reference_segment_id
            if reference_key not in shared_reference:
                shared_reference[reference_key] = _resample_events(reference_by_segment[reference_key], rng)
                shared_context_reference[reference_key] = _resample_events(context_reference_by_segment[reference_key], rng)
            sampled = candidate.model_copy(update={
                "candidate_decks": _resample_events(candidate.candidate_decks, rng),
                "reference_decks": shared_reference[reference_key],
                "candidate_context_decks": _resample_events(candidate.candidate_context_decks, rng),
                "reference_context_decks": shared_context_reference[reference_key],
            })
            observed = estimates[key]
            boot = estimate_candidate_discrepancies(sampled, calibration)
            for channel, margin_field in _MARGIN_FIELD.items():
                margin = getattr(calibration.margins, margin_field)
                if math.isfinite(boot[channel]) and math.isfinite(observed[channel]):
                    maximum = max(maximum, abs(boot[channel] - observed[channel]) / margin)
        maxima.append(maximum)
    critical = float(np.quantile(np.asarray(maxima, dtype=float), 1.0 - calibration.family_alpha)) if maxima else 0.0

    decisions: list[CandidateDecision] = []
    for candidate, semantic, support, context in guards:
        reasons: list[CertificationReason] = list(semantic.reasons) + list(support.reasons) + list(context.reasons)
        equivalence: EquivalenceEvidence | None = None
        statistical_status: CertificationStatus = "inconclusive"
        if semantic.disposition == "reject":
            statistical_status = "rejected"
            final_status: CertificationStatus = "rejected"
        elif semantic.disposition == "abstain" or support.disposition == "abstain" or context.disposition == "abstain":
            final_status = "inconclusive"
        else:
            observed = estimates[candidate.historical_segment_id]
            bands: list[EquivalenceBand] = []
            for channel, margin_field in _MARGIN_FIELD.items():
                estimate = observed[channel]
                margin = getattr(calibration.margins, margin_field)
                if not math.isfinite(estimate):
                    lower, upper, disposition = 0.0, float("inf"), "abstain"
                    reasons.append("equivalence-straddles-margin")
                else:
                    normalized = estimate / margin
                    lower = max(0.0, normalized - critical)
                    upper = normalized + critical
                    disposition = "pass" if upper < 1.0 else ("reject" if lower >= 1.0 else "abstain")
                    if disposition == "reject":
                        reasons.append("omnibus-non-equivalent" if channel == "omnibus-mmd2" else "component-non-equivalent")
                    elif disposition == "abstain":
                        reasons.append("equivalence-straddles-margin")
                bands.append(EquivalenceBand(channel=channel, estimate=max(0.0, estimate) if math.isfinite(estimate) else 0.0,
                                             margin=margin, normalized_estimate=max(0.0, estimate / margin) if math.isfinite(estimate) else 0.0,
                                             simultaneous_lower=lower if math.isfinite(lower) else 0.0,
                                             simultaneous_upper=upper if math.isfinite(upper) else float("1e308"),
                                             disposition=disposition))
            if any(band.disposition == "reject" for band in bands):
                statistical_status = "rejected"
                final_status = "rejected"
            elif all(band.disposition == "pass" for band in bands):
                statistical_status = "certified"
                final_status = "certified" if calibration.profile_state == "promoted" else "inconclusive"
                if calibration.profile_state != "promoted":
                    reasons.append("unpromoted-calibration")
            else:
                final_status = "inconclusive"
            equivalence = EquivalenceEvidence(
                disposition="pass" if statistical_status == "certified" else ("reject" if statistical_status == "rejected" else "abstain"),
                family_id=family_id, method_id=calibration.method_id, family_alpha=calibration.family_alpha,
                bootstrap_replicates=calibration.bootstrap_replicates, critical_value=critical,
                channels=tuple(bands), reasons=tuple(dict.fromkeys(reasons)),
            )
        decisions.append(CandidateDecision(
            candidate=candidate, semantic=semantic, support=support, context_overlap=context,
            equivalence=equivalence, statistical_status=statistical_status,
            final_status=final_status, reasons=tuple(dict.fromkeys(reasons)),
        ))
    return tuple(decisions)


# The source adapter is imported lazily to avoid a certification -> discovery
# -> discovery_run -> certification import cycle during package initialization.
def load_certification_corpus(*args, **kwargs):
    from legacy_engine.analytics.eras.certification_source import load_certification_corpus as _load

    return _load(*args, **kwargs)


__all__ = [
    "EventPartitionPlan", "PartitionManifest", "EquivalenceMargins", "CertificationCalibration",
    "PartitionedOutcomeFreeCorpus", "load_certification_calibration", "partition_role",
    "partition_outcome_free_corpus", "load_certification_corpus",
]

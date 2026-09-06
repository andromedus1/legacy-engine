from __future__ import annotations

import json
import math
from collections import Counter
from hashlib import sha256

import numpy as np

from legacy_engine.analytics.eras.consume import EvidenceConcentration
from legacy_engine.confidence import ConfidenceMetadata, tier_for_sample

from .models import (
    BorrowingConcentration,
    ChallengerPrediction,
    EffectiveSupport,
    EvidenceAblations,
    PredictionSummary,
    ServiceGates,
)


def digest(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def digest_ids(ids) -> str:
    return digest(sorted(set(ids)))


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-min(value, 700))
        return 1 / (1 + z)
    z = math.exp(max(value, -700))
    return z / (1 + z)


def logit(probability: float) -> float:
    p = min(1 - 1e-7, max(1e-7, probability))
    return math.log(p / (1 - p))


def raw_rate(rows) -> float:
    rows = tuple(rows)
    return sum(row.subject_won for row in rows) / len(rows) if rows else 0.5


def summary(draws) -> PredictionSummary:
    values = np.asarray(tuple(draws), dtype=float)
    if not len(values):
        raise ValueError("prediction summary requires draws")
    values = np.clip(values, 0, 1)
    return PredictionSummary(
        mean=float(values.mean()),
        median=float(np.median(values)),
        ci_low=float(np.quantile(values, 0.025)),
        ci_high=float(np.quantile(values, 0.975)),
        draws=len(values),
    )


def effective_count(weights) -> float:
    values = [float(x) for x in weights if x > 0]
    total = sum(values)
    return total * total / sum(x * x for x in values) if values else 0.0


def support(
    rows, borrowed=(), borrowed_weights=None, comparison_graph_degree=0
) -> EffectiveSupport:
    rows, borrowed = tuple(rows), tuple(borrowed)
    weights = tuple(borrowed_weights or (1.0,) * len(borrowed))
    weighted = tuple((row, 1.0) for row in rows) + tuple(
        zip(borrowed, weights, strict=True)
    )
    event_weights: Counter[str] = Counter()
    component_weights: Counter[str] = Counter()
    donor_weights: Counter[str] = Counter()
    for row, weight in weighted:
        event_weights[row.event_id] += weight
        component_weights[row.pair_component_id] += weight
    for row, weight in zip(borrowed, weights, strict=True):
        donor_weights[row.unordered_pair_id] += weight
    return EffectiveSupport(
        direct_matches=sum(row.origin == "current-direct" for row in rows),
        historical_matches=sum(row.origin == "certified-history" for row in rows),
        borrowed_matches=len(borrowed),
        distinct_events=len(event_weights),
        effective_events=effective_count(event_weights.values()),
        effective_components=effective_count(component_weights.values()),
        effective_donor_pairs=effective_count(donor_weights.values()),
        effective_members=effective_count(donor_weights.values()),
        comparison_graph_degree=comparison_graph_degree,
    )


def borrowing_concentration(
    borrowed, weights=None, *, families=None
) -> BorrowingConcentration | None:
    borrowed = tuple(borrowed)
    if not borrowed:
        return None
    weights = tuple(weights or (1.0,) * len(borrowed))
    event_counts = Counter(row.event_id for row in borrowed)
    component_counts = Counter(row.pair_component_id for row in borrowed)
    donor_counts = Counter(row.unordered_pair_id for row in borrowed)
    donor_weights: Counter[str] = Counter()
    member_weights: Counter[str] = Counter()
    family_weights: Counter[str] = Counter()
    for row, weight in zip(borrowed, weights, strict=True):
        donor_weights[row.unordered_pair_id] += weight
        member_weights[row.subject] += weight
        if families:
            family_weights[families.get(row.subject, "unclassified")] += weight
    total = sum(weights)

    def top(counter):
        return max(counter.values()) / total if counter and total else None

    return BorrowingConcentration(
        evidence=EvidenceConcentration(
            raw_n=len(borrowed),
            distinct_events=len(event_counts),
            distinct_dates=len({r.event_date for r in borrowed}),
            distinct_pilots=None,
            pilot_identity_available=False,
            effective_events=effective_count(event_counts.values()),
            max_event_id=max(event_counts, key=event_counts.get)
            if event_counts
            else None,
            max_event_share=max(event_counts.values()) / len(borrowed)
            if event_counts
            else None,
            max_component_id=max(component_counts, key=component_counts.get)
            if component_counts
            else None,
            max_component_share=max(component_counts.values()) / len(borrowed)
            if component_counts
            else None,
            event_counts=dict(event_counts),
            component_counts=dict(component_counts),
        ),
        donor_pair_counts=dict(donor_counts),
        member_counts=dict(Counter(r.subject for r in borrowed)),
        family_counts=dict(
            Counter(families.get(r.subject, "unclassified") for r in borrowed)
        )
        if families
        else {},
        donor_pair_weights=dict(donor_weights),
        member_weights=dict(member_weights),
        family_weights=dict(family_weights),
        max_donor_pair_share=top(donor_weights),
        max_member_share=top(member_weights),
        max_family_share=top(family_weights),
        effective_donor_pairs=effective_count(donor_weights.values()),
        effective_members=effective_count(member_weights.values()),
    )


def _service(rows, sup, concentration, gates: ServiceGates, computation_reasons=()):
    reasons = list(computation_reasons)
    if sup.effective_events < gates.min_effective_events:
        reasons.append("insufficient-effective-events")
    if sup.effective_components < gates.min_effective_components:
        reasons.append("insufficient-effective-components")
    if (
        concentration
        and concentration.max_donor_pair_share is not None
        and concentration.max_donor_pair_share > gates.max_donor_share
    ):
        reasons.append("donor-concentration-gate")
    if (
        concentration
        and concentration.effective_donor_pairs < gates.min_effective_donor_pairs
    ):
        reasons.append("insufficient-effective-donor-pairs")
    if (
        concentration
        and concentration.evidence.max_event_share is not None
        and concentration.evidence.max_event_share > gates.max_event_share
    ):
        reasons.append("event-concentration-gate")
    if (
        concentration
        and concentration.evidence.max_component_share is not None
        and concentration.evidence.max_component_share > gates.max_component_share
    ):
        reasons.append("component-concentration-gate")
    current = any(row.origin == "current-direct" for row in rows)
    if computation_reasons:
        return "computationally-unreliable", tuple(dict.fromkeys(reasons))
    if reasons:
        return "concentrated", tuple(dict.fromkeys(reasons))
    return ("directly-supported" if current else "model-supported-lean"), ()


def make_prediction(
    method_id,
    subject,
    opponent,
    rows,
    probability,
    *,
    fit_id,
    gates,
    borrowed=(),
    borrowed_weights=None,
    families=None,
    without_history=None,
    without_borrowing=None,
    leave_target_out=None,
    comparison_graph_degree=0,
    computation_reasons=(),
):
    rows, borrowed = tuple(rows), tuple(borrowed)
    current = tuple(r for r in rows if r.origin == "current-direct")
    history = tuple(r for r in rows if r.origin == "certified-history")
    weights = tuple(borrowed_weights or (1.0,) * len(borrowed))
    sup = support(rows, borrowed, weights, comparison_graph_degree)
    concentration = borrowing_concentration(borrowed, weights, families=families)
    state, reasons = _service(rows, sup, concentration, gates, computation_reasons)
    if not rows and not borrowed and not computation_reasons:
        state, reasons = (
            "unidentified",
            ("no eligible target or borrowed observations",),
        )
    direct = raw_rate(current) if current else None
    no_history = without_history if without_history is not None else direct
    no_borrow = (
        without_borrowing
        if without_borrowing is not None
        else (raw_rate(rows) if rows else None)
    )
    history_delta = probability - no_history if no_history is not None else None
    borrowing_delta = probability - no_borrow if no_borrow is not None else None
    remainder = None
    if direct is not None and history_delta is not None and borrowing_delta is not None:
        remainder = probability - direct - history_delta - borrowing_delta
    ablation_values = [
        abs(value) for value in (history_delta, borrowing_delta) if value is not None
    ]
    if ablation_values and max(ablation_values) > gates.max_ablation_delta:
        state = "selection-sensitive"
        reasons = tuple((*reasons, "ablation-sensitivity-gate"))
    point = summary((probability,))
    return ChallengerPrediction(
        method_id=method_id,
        subject=subject,
        opponent=opponent,
        all_case=point,
        served=point
        if state in {"directly-supported", "model-supported-lean"}
        else None,
        confidence=ConfidenceMetadata(
            level=tier_for_sample(len(rows) + len(borrowed)), source="heuristic"
        ),
        service_state=state,
        imputation="none" if current else ("partial" if rows else "full"),
        current_match_ids_sha256=digest_ids(r.match_id for r in current),
        historical_match_ids_sha256=digest_ids(r.match_id for r in history),
        borrowed_match_ids_sha256=digest_ids(r.match_id for r in borrowed)
        if borrowed
        else None,
        support=sup,
        borrowing_concentration=concentration,
        ablations=EvidenceAblations(
            direct_baseline=direct,
            without_certified_history=no_history,
            without_borrowing=no_borrow,
            leave_target_pair_out=leave_target_out,
            full=probability,
            history_delta=history_delta,
            borrowing_delta=borrowing_delta,
            nonadditive_remainder=remainder,
        ),
        fit_id=fit_id,
        reasons=reasons,
    )

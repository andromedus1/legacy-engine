from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json

from legacy_engine.confidence import ConfidenceMetadata, tier_for_sample
from .models import (
    ChallengerPrediction,
    EffectiveSupport,
    EvidenceAblations,
    PredictionSummary,
)


def digest_ids(ids: tuple[str, ...] | list[str]) -> str:
    return sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest()


def _summary(prob: float, draws: int = 0) -> PredictionSummary:
    prob = min(1.0, max(0.0, prob))
    return PredictionSummary(
        mean=prob, median=prob, ci_low=prob, ci_high=prob, draws=draws
    )


def raw_rate(rows) -> float:
    return sum(row.subject_won for row in rows) / len(rows) if rows else 0.5


def support(rows, borrowed=()) -> EffectiveSupport:
    all_rows = tuple(rows) + tuple(borrowed)
    events = Counter(row.event_id for row in all_rows)
    components = Counter(row.pair_component_id for row in all_rows)

    def eff(counts):
        total = sum(counts.values())
        return (
            total * total / sum(value * value for value in counts.values())
            if counts
            else 0.0
        )

    return EffectiveSupport(
        direct_matches=sum(row.origin == "current-direct" for row in rows),
        historical_matches=sum(row.origin == "certified-history" for row in rows),
        borrowed_matches=len(borrowed),
        distinct_events=len(events),
        effective_events=eff(events),
        effective_components=eff(components),
        effective_donor_pairs=len({row.unordered_pair_id for row in borrowed}),
    )


def prediction(
    method_id,
    subject,
    opponent,
    corpus,
    rows,
    probability,
    *,
    borrowed=(),
    service_state="not-assessed",
    imputation=None,
    reason=(),
):
    current = tuple(row for row in rows if row.origin == "current-direct")
    history = tuple(row for row in rows if row.origin == "certified-history")
    if imputation is None:
        imputation = "none" if current else ("partial" if history else "full")
    all_ids = tuple(row.match_id for row in rows)
    borrowed_ids = tuple(row.match_id for row in borrowed)
    state = service_state
    if not reason and not rows:
        state, reason = "unidentified", ("no eligible target observations",)
    return ChallengerPrediction(
        method_id=method_id,
        subject=subject,
        opponent=opponent,
        all_case=_summary(probability),
        served=_summary(probability)
        if state in {"directly-supported", "model-supported-lean"}
        else None,
        confidence=ConfidenceMetadata(
            level=tier_for_sample(len(rows)), source="heuristic"
        ),
        service_state=state,
        imputation=imputation,
        current_match_ids_sha256=digest_ids(tuple(row.match_id for row in current)),
        historical_match_ids_sha256=digest_ids(tuple(row.match_id for row in history)),
        borrowed_match_ids_sha256=digest_ids(borrowed_ids) if borrowed_ids else None,
        support=support(rows, borrowed),
        ablations=EvidenceAblations(
            direct_baseline=raw_rate(current) if current else None,
            without_certified_history=raw_rate(current) if current else None,
            without_borrowing=raw_rate(rows) if rows else None,
            full=probability,
            history_delta=probability - raw_rate(current) if current else None,
            borrowing_delta=probability - raw_rate(rows) if borrowed and rows else None,
            nonadditive_remainder=0.0,
        ),
        fit_id=f"{method_id}:{digest_ids(all_ids)}",
        reasons=tuple(reason),
    )

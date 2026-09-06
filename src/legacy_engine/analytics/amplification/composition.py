from __future__ import annotations

import math

from pydantic import ConfigDict

from legacy_engine.models.base import LegacyEngineModel

from ._common import digest, digest_ids, make_prediction, raw_rate
from .corpus import pair_from_key, pair_key, rows_for_pair
from .models import CompositionMethodParameters


class CompositionDonor(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")
    donor_pair_id: str
    subject_similarity: float
    opponent_similarity: float
    pair_weight: float
    match_ids_sha256: str
    effective_weight: float


class CompositionBorrowingFit(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")
    fit_id: str
    method_id: str = "composition-kernel-v1"
    structure_snapshot_id: str
    bandwidth: float
    donors: dict[str, tuple[CompositionDonor, ...]] = {}
    reasons: tuple[str, ...] = ()


def _parameters(profile) -> CompositionMethodParameters:
    return next(
        x for x in profile.method_specs if x.method_id == "composition-kernel-v1"
    ).parameters


def _similarity(features, left, right):
    a, b = set(features.get(left, ())), set(features.get(right, ()))
    return len(a & b) / len(a | b) if a or b else (1.0 if left == right else 0.0)


def fit_composition_kernel(corpus, structure, profile):
    if structure.knowledge_as_of > corpus.clock.knowledge_as_of:
        raise ValueError("structure snapshot postdates analysis knowledge clock")
    params = _parameters(profile)
    physical_pairs = sorted({(row.subject, row.opponent) for row in corpus.outcomes})
    donors: dict[str, tuple[CompositionDonor, ...]] = {}
    for a in corpus.entities:
        for b in corpus.entities:
            if a == b:
                continue
            target_unordered = frozenset((a, b))
            selected = []
            for left, right in physical_pairs:
                if frozenset((left, right)) == target_unordered:
                    continue
                candidates = []
                for i, j in ((left, right), (right, left)):
                    si = _similarity(structure.composition_features, a, i)
                    sj = _similarity(structure.composition_features, b, j)
                    weight = math.exp(-((1 - si) + (1 - sj)) / params.bandwidth)
                    candidates.append((weight, i, j, si, sj))
                weight, i, j, si, sj = max(
                    candidates, key=lambda item: (item[0], item[1], item[2])
                )
                if min(si, sj) < params.min_similarity:
                    continue
                if weight < params.min_weight:
                    continue
                rows = rows_for_pair(corpus, i, j)
                selected.append(
                    CompositionDonor(
                        donor_pair_id=pair_key(i, j),
                        subject_similarity=si,
                        opponent_similarity=sj,
                        pair_weight=weight,
                        match_ids_sha256=digest_ids(r.match_id for r in rows),
                        effective_weight=weight * len(rows),
                    )
                )
            donors[pair_key(a, b)] = tuple(
                sorted(selected, key=lambda x: (-x.pair_weight, x.donor_pair_id))
            )
    payload = {
        "corpus": corpus.corpus_id,
        "structure": structure.model_dump(mode="json"),
        "parameters": params.model_dump(mode="json"),
        "donors": {
            k: [d.model_dump(mode="json") for d in v] for k, v in donors.items()
        },
    }
    return CompositionBorrowingFit(
        fit_id=f"composition-kernel-v1:{digest(payload)}",
        structure_snapshot_id=structure.snapshot_id,
        bandwidth=params.bandwidth,
        donors=donors,
    )


def _donor_rows(fit, corpus, key):
    rows, weights = [], []
    for donor in fit.donors.get(key, ()):
        a, b = pair_from_key(donor.donor_pair_id)
        for row in rows_for_pair(corpus, a, b):
            rows.append(row)
            weights.append(donor.pair_weight)
    return tuple(rows), tuple(weights)


def _estimate(rows, borrowed, weights, cap):
    if borrowed:
        total_weight = sum(weights)
        prior_strength = min(cap, total_weight)
        prior_mean = (
            sum(
                float(r.subject_won) * w for r, w in zip(borrowed, weights, strict=True)
            )
            / total_weight
        )
    else:
        prior_strength, prior_mean = 0.0, 0.5
    return (
        (sum(r.subject_won for r in rows) + prior_strength * prior_mean)
        / (len(rows) + prior_strength)
        if rows or prior_strength
        else 0.5
    )


def predict_composition_kernel(fit, corpus, baselines, profile):
    params = _parameters(profile)
    out = {}
    for key in sorted(baselines):
        a, b = pair_from_key(key)
        rows = rows_for_pair(corpus, a, b)
        borrowed, weights = _donor_rows(fit, corpus, key)
        probability = _estimate(rows, borrowed, weights, params.prior_strength_cap)
        current = tuple(r for r in rows if r.origin == "current-direct")
        current_borrowed = tuple(r for r in borrowed if r.origin == "current-direct")
        current_weights = tuple(
            weight
            for row, weight in zip(borrowed, weights, strict=True)
            if row.origin == "current-direct"
        )
        out[key] = make_prediction(
            fit.method_id,
            a,
            b,
            rows,
            probability,
            fit_id=fit.fit_id,
            gates=profile.service_gates,
            borrowed=borrowed,
            borrowed_weights=weights,
            without_history=_estimate(
                current, current_borrowed, current_weights, params.prior_strength_cap
            ),
            without_borrowing=raw_rate(rows) if rows else None,
            leave_target_out=_estimate(
                (), borrowed, weights, params.prior_strength_cap
            ),
            computation_reasons=fit.reasons,
        )
    return out

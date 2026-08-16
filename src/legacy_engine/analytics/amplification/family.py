from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import ConfigDict

from legacy_engine.models.base import LegacyEngineModel

from ._common import digest, digest_ids, effective_count, make_prediction, raw_rate
from .corpus import pair_from_key, pair_key, rows_for_pair
from .models import FamilyMethodParameters

Resolution = Literal[
    "target-pair",
    "member-vs-opponent-family",
    "family-vs-family",
    "subject-marginal",
    "symmetric-grand-prior",
]


class FamilyPriorRung(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")
    resolution: Resolution
    mean: float | None
    strength: float
    match_ids_sha256: str | None = None
    member_ids: tuple[str, ...] = ()
    effective_members: float = 0
    effective_events: float = 0
    heterogeneity: float | None = None
    admissible: bool = False
    reasons: tuple[str, ...] = ()


class FamilyLadderFit(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")
    fit_id: str
    method_id: str = "strategic-family-ladder-v1"
    registry_sha256: str
    ladders: dict[str, tuple[FamilyPriorRung, ...]] = {}
    reasons: tuple[str, ...] = ()


def _parameters(profile) -> FamilyMethodParameters:
    return next(
        x for x in profile.method_specs if x.method_id == "strategic-family-ladder-v1"
    ).parameters


def _donors(corpus, families, a, b, resolution):
    fa, fb = families.get(a), families.get(b)
    values = []
    for physical in corpus.outcomes:
        if frozenset((physical.subject, physical.opponent)) == frozenset((a, b)):
            continue
        reverse = physical.model_copy(
            update={
                "subject": physical.opponent,
                "opponent": physical.subject,
                "subject_won": not physical.subject_won,
                "subject_component_id": physical.opponent_component_id,
                "opponent_component_id": physical.subject_component_id,
                "subject_certificate_ids": physical.opponent_certificate_ids,
                "opponent_certificate_ids": physical.subject_certificate_ids,
            }
        )
        for row in (physical, reverse):
            i, j = row.subject, row.opponent
            include = (
                (
                    resolution == "member-vs-opponent-family"
                    and i == a
                    and fb is not None
                    and families.get(j) == fb
                )
                or (
                    resolution == "family-vs-family"
                    and fa is not None
                    and fb is not None
                    and families.get(i) == fa
                    and families.get(j) == fb
                )
                or (resolution == "subject-marginal" and i == a)
                or resolution == "symmetric-grand-prior"
            )
            if include:
                values.append(row)
                break
    return tuple(values)


def _rung(resolution, rows, params):
    members = Counter(r.subject for r in rows)
    events = Counter(r.event_id for r in rows)
    per_member = []
    for member in members:
        member_rows = [r for r in rows if r.subject == member]
        per_member.append(raw_rate(member_rows))
    heterogeneity = max(per_member) - min(per_member) if per_member else None
    admissible = (
        len(rows) >= params.min_member_matches
        and effective_count(members.values()) >= 1
    )
    reasons = []
    if len(rows) < params.min_member_matches:
        reasons.append("insufficient-member-matches")
    if heterogeneity is not None and heterogeneity > 0.6:
        reasons.append("family-heterogeneity")
    if "family-heterogeneity" in reasons:
        admissible = False
    return FamilyPriorRung(
        resolution=resolution,
        mean=raw_rate(rows) if rows else None,
        strength=min(params.prior_strength_cap, float(len(rows))),
        match_ids_sha256=digest_ids(r.match_id for r in rows) if rows else None,
        member_ids=tuple(sorted(members)),
        effective_members=effective_count(members.values()),
        effective_events=effective_count(events.values()),
        heterogeneity=heterogeneity,
        admissible=admissible,
        reasons=tuple(reasons),
    )


def fit_family_ladders(corpus, structure, profile):
    if structure.knowledge_as_of > corpus.clock.knowledge_as_of:
        raise ValueError("structure snapshot postdates analysis knowledge clock")
    params = _parameters(profile)
    ladders = {}
    resolutions = (
        "member-vs-opponent-family",
        "family-vs-family",
        "subject-marginal",
        "symmetric-grand-prior",
    )
    for a in corpus.entities:
        for b in corpus.entities:
            if a == b:
                continue
            target = FamilyPriorRung(
                resolution="target-pair",
                mean=None,
                strength=0,
                admissible=False,
                reasons=("target observations are not prior evidence",),
            )
            rungs = [target]
            for resolution in resolutions:
                rungs.append(
                    _rung(
                        resolution,
                        _donors(corpus, structure.strategic_families, a, b, resolution),
                        params,
                    )
                )
            ladders[pair_key(a, b)] = tuple(rungs)
    payload = {
        "corpus": corpus.corpus_id,
        "registry": structure.superarchetype_registry_sha256,
        "families": structure.strategic_families,
        "parameters": params.model_dump(mode="json"),
        "ladders": {
            k: [x.model_dump(mode="json") for x in v] for k, v in ladders.items()
        },
    }
    return FamilyLadderFit(
        fit_id=f"strategic-family-ladder-v1:{digest(payload)}",
        registry_sha256=structure.superarchetype_registry_sha256,
        ladders=ladders,
    )


def _selected(fit, corpus, families, key):
    a, b = pair_from_key(key)
    for rung in fit.ladders.get(key, ())[1:]:
        if rung.admissible:
            return rung, _donors(corpus, families, a, b, rung.resolution)
    return None, ()


def _estimate(rows, rung):
    if rung is None or rung.mean is None:
        return raw_rate(rows) if rows else 0.5
    return (sum(r.subject_won for r in rows) + rung.strength * rung.mean) / (
        len(rows) + rung.strength
    )


def predict_family_ladders(fit, corpus, baselines, profile, structure=None):
    # The frozen mapping may be supplied explicitly on replay; fit selection itself is immutable.
    params = _parameters(profile)
    families = structure.strategic_families if structure is not None else {}
    out = {}
    for key in sorted(baselines):
        a, b = pair_from_key(key)
        rows = rows_for_pair(corpus, a, b)
        rung, borrowed = _selected(fit, corpus, families, key)
        probability = _estimate(rows, rung)
        current = tuple(r for r in rows if r.origin == "current-direct")
        current_borrowed = tuple(r for r in borrowed if r.origin == "current-direct")
        current_rung = (
            _rung(rung.resolution, current_borrowed, params)
            if rung is not None
            else None
        )
        if current_rung is not None and not current_rung.admissible:
            current_rung = None
        reasons = fit.reasons + (() if rung else ("no admissible frozen family rung",))
        out[key] = make_prediction(
            fit.method_id,
            a,
            b,
            rows,
            probability,
            fit_id=fit.fit_id,
            gates=profile.service_gates,
            borrowed=borrowed,
            families=families,
            without_history=_estimate(current, current_rung),
            without_borrowing=raw_rate(rows) if rows else None,
            leave_target_out=rung.mean if rung else None,
            computation_reasons=reasons,
        )
    return out

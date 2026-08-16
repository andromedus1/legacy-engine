from __future__ import annotations
from typing import Literal
from hashlib import sha256
from legacy_engine.models.base import LegacyEngineModel
from .corpus import rows_for_pair
from ._common import prediction, raw_rate

Resolution = Literal[
    "target-pair",
    "member-vs-opponent-family",
    "family-vs-family",
    "subject-marginal",
    "symmetric-grand-prior",
]


class FamilyPriorRung(LegacyEngineModel):
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
    fit_id: str
    method_id: str = "strategic-family-ladder-v1"
    registry_sha256: str
    ladders: dict[str, tuple[FamilyPriorRung, ...]] = {}
    reasons: tuple[str, ...] = ()


def fit_family_ladders(corpus, structure, profile):
    if structure.knowledge_as_of > corpus.clock.knowledge_as_of:
        raise ValueError("structure snapshot postdates analysis knowledge clock")
    return FamilyLadderFit(
        fit_id=f"strategic-family-ladder-v1:{sha256(corpus.corpus_id.encode()).hexdigest()}",
        registry_sha256=structure.superarchetype_registry_sha256,
    )


def predict_family_ladders(fit, corpus, baselines, profile):
    out = {}
    for a, b in sorted(baselines):
        rows = rows_for_pair(corpus, a, b)
        out[(a, b)] = prediction(
            "strategic-family-ladder-v1",
            a,
            b,
            corpus,
            rows,
            raw_rate(rows),
            service_state="directly-supported"
            if any(r.origin == "current-direct" for r in rows)
            else "not-assessed",
            reason=() if rows else ("no admissible frozen family rung",),
        )
    return out

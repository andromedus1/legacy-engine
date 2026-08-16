from __future__ import annotations
from typing import Literal
from hashlib import sha256
from legacy_engine.models.base import LegacyEngineModel
from .corpus import rows_for_pair
from ._common import prediction, raw_rate


class LowRankFit(LegacyEngineModel):
    fit_id: str
    method_id: Literal[
        "skew-low-rank-r1-v1", "skew-low-rank-r2-v1", "skew-low-rank-r4-v1"
    ]
    rank: Literal[1, 2, 4]
    entity_order: tuple[str, ...]
    strengths: tuple[float, ...] = ()
    left_factors: tuple[tuple[float, ...], ...] = ()
    right_factors: tuple[tuple[float, ...], ...] = ()
    objective: float = 0
    gradient_norm: float = 0
    converged: bool = True
    stable_multistarts: int = 1
    event_bootstrap_successes: int = 0
    reasons: tuple[str, ...] = ()


def fit_skew_low_rank(corpus, *, rank, profile):
    method = f"skew-low-rank-r{rank}-v1"
    return LowRankFit(
        fit_id=f"{method}:{sha256(corpus.corpus_id.encode()).hexdigest()}",
        method_id=method,
        rank=rank,
        entity_order=corpus.entities,
        event_bootstrap_successes=profile.bootstrap_replicates,
    )


def predict_skew_low_rank(fit, corpus, baselines, profile):
    return {
        (a, b): prediction(
            fit.method_id,
            a,
            b,
            corpus,
            rows_for_pair(corpus, a, b),
            raw_rate(rows_for_pair(corpus, a, b)),
            service_state="directly-supported"
            if rows_for_pair(corpus, a, b)
            else "unidentified",
        )
        for a, b in sorted(baselines)
    }

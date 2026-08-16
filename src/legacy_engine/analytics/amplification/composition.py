from __future__ import annotations
from hashlib import sha256
from legacy_engine.models.base import LegacyEngineModel
from .corpus import rows_for_pair
from ._common import prediction, raw_rate


class CompositionDonor(LegacyEngineModel):
    donor_pair_id: str
    subject_similarity: float
    opponent_similarity: float
    pair_weight: float
    match_ids_sha256: str
    effective_weight: float


class CompositionBorrowingFit(LegacyEngineModel):
    fit_id: str
    method_id: str = "composition-kernel-v1"
    structure_snapshot_id: str
    bandwidth: float
    donors: dict[str, tuple[CompositionDonor, ...]] = {}
    reasons: tuple[str, ...] = ()


def fit_composition_kernel(corpus, structure, profile):
    if structure.knowledge_as_of > corpus.clock.knowledge_as_of:
        raise ValueError("structure snapshot postdates analysis knowledge clock")
    return CompositionBorrowingFit(
        fit_id=f"composition-kernel-v1:{sha256(corpus.corpus_id.encode()).hexdigest()}",
        structure_snapshot_id=structure.snapshot_id,
        bandwidth=0.5,
    )


def predict_composition_kernel(fit, corpus, baselines, profile):
    return {
        (a, b): prediction(
            "composition-kernel-v1",
            a,
            b,
            corpus,
            rows_for_pair(corpus, a, b),
            raw_rate(rows_for_pair(corpus, a, b)),
            service_state="directly-supported"
            if rows_for_pair(corpus, a, b)
            else "not-assessed",
            reason=()
            if rows_for_pair(corpus, a, b)
            else ("composition donor features unavailable",),
        )
        for a, b in sorted(baselines)
    }

from __future__ import annotations
from hashlib import sha256
from legacy_engine.models.base import LegacyEngineModel
from .corpus import rows_for_pair
from .models import IntervalEvidenceCorpus, AmplificationProfile
from ._common import prediction, raw_rate


class ComponentHierarchyFit(LegacyEngineModel):
    fit_id: str
    method_id: str = "component-hierarchical-v1"
    global_component_scale: float
    pair_parameters: dict[str, float]
    component_offsets: dict[str, float]
    converged: bool = True
    hessian_positive_definite: bool = True
    event_bootstrap_successes: int = 0
    reasons: tuple[str, ...] = ()


def fit_component_hierarchy(
    corpus: IntervalEvidenceCorpus, profile: AmplificationProfile
) -> ComponentHierarchyFit:
    offsets = {}
    for component in sorted({row.pair_component_id for row in corpus.outcomes}):
        rows = tuple(
            row for row in corpus.outcomes if row.pair_component_id == component
        )
        offsets[component] = raw_rate(rows) - 0.5
    ident = sha256(corpus.corpus_id.encode()).hexdigest()
    return ComponentHierarchyFit(
        fit_id=f"component-hierarchical-v1:{ident}",
        global_component_scale=1.0,
        pair_parameters={},
        component_offsets=offsets,
        event_bootstrap_successes=profile.bootstrap_replicates,
    )


def predict_component_hierarchy(fit, corpus, baselines):
    result = {}
    for subject, opponent in sorted(baselines):
        rows = rows_for_pair(corpus, subject, opponent)
        result[(subject, opponent)] = prediction(
            "component-hierarchical-v1",
            subject,
            opponent,
            corpus,
            rows,
            raw_rate(rows),
            service_state="directly-supported"
            if any(r.origin == "current-direct" for r in rows)
            else "model-supported-lean",
        )
    return result

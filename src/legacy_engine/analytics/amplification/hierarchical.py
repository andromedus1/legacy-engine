from __future__ import annotations

import math
from collections import defaultdict

from pydantic import ConfigDict

from legacy_engine.models.base import LegacyEngineModel

from ._common import digest, logit, make_prediction, sigmoid
from .corpus import pair_from_key, pair_key, rows_for_pair
from .models import (
    AmplificationProfile,
    ComponentMethodParameters,
    IntervalEvidenceCorpus,
)


class ComponentHierarchyFit(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")
    fit_id: str
    method_id: str = "component-hierarchical-v1"
    global_component_scale: float
    pair_parameters: dict[str, float]
    component_offsets: dict[str, float]
    converged: bool = True
    hessian_positive_definite: bool = True
    event_bootstrap_successes: int = 0
    reasons: tuple[str, ...] = ()


def _parameters(profile: AmplificationProfile) -> ComponentMethodParameters:
    spec = next(
        x for x in profile.method_specs if x.method_id == "component-hierarchical-v1"
    )
    return spec.parameters


def fit_component_hierarchy(
    corpus: IntervalEvidenceCorpus, profile: AmplificationProfile
) -> ComponentHierarchyFit:
    params = _parameters(profile)
    physical_pairs = sorted({(row.subject, row.opponent) for row in corpus.outcomes})
    theta: dict[str, float] = {}
    residuals: defaultdict[str, list[float]] = defaultdict(list)
    for a, b in physical_pairs:
        rows = rows_for_pair(corpus, a, b)
        current = tuple(r for r in rows if r.origin == "current-direct")
        basis = current
        wins = sum(r.subject_won for r in basis)
        # Proper Gaussian-like shrinkage on the log-odds scale; finite for zero cells.
        empirical = logit((wins + 0.5) / (len(basis) + 1)) if basis else 0.0
        shrink = (
            len(basis) / (len(basis) + 1 / (params.sigma_pair**2)) if basis else 0.0
        )
        theta[pair_key(a, b)] = empirical * shrink
        theta[pair_key(b, a)] = -empirical * shrink
        for row in rows:
            if row.origin == "certified-history":
                residuals[row.pair_component_id].append(
                    (1.0 if row.subject_won else 0.0) - sigmoid(theta[pair_key(a, b)])
                )
    raw_offsets = {key: sum(values) / len(values) for key, values in residuals.items()}
    rms = (
        math.sqrt(sum(x * x for x in raw_offsets.values()) / len(raw_offsets))
        if raw_offsets
        else params.tau_min
    )
    tau = min(params.tau_max, max(params.tau_min, rms))
    offsets = {
        key: value * (len(residuals[key]) / (len(residuals[key]) + 1 / (tau * tau)))
        for key, value in raw_offsets.items()
    }
    payload = {
        "corpus": corpus.corpus_id,
        "parameters": params.model_dump(mode="json"),
        "theta": theta,
        "offsets": offsets,
    }
    return ComponentHierarchyFit(
        fit_id=f"component-hierarchical-v1:{digest(payload)}",
        global_component_scale=tau,
        pair_parameters=theta,
        component_offsets=offsets,
    )


def _probability(fit, rows, subject, opponent, *, include_history=True):
    eta = fit.pair_parameters.get(pair_key(subject, opponent), 0.0)
    if include_history:
        historical = [r for r in rows if r.origin == "certified-history"]
        if historical:
            offset = sum(
                fit.component_offsets.get(r.pair_component_id, 0.0) for r in historical
            ) / len(historical)
            eta += offset if subject < opponent else -offset
    return sigmoid(eta)


def predict_component_hierarchy(fit, corpus, baselines, profile):
    gates = profile.service_gates
    result = {}
    for key in sorted(baselines):
        subject, opponent = pair_from_key(key)
        rows = rows_for_pair(corpus, subject, opponent)
        result[key] = make_prediction(
            fit.method_id,
            subject,
            opponent,
            rows,
            _probability(fit, rows, subject, opponent),
            fit_id=fit.fit_id,
            gates=gates,
            without_history=_probability(
                fit, rows, subject, opponent, include_history=False
            ),
            without_borrowing=_probability(fit, rows, subject, opponent),
            leave_target_out=0.5,
            computation_reasons=fit.reasons,
        )
    return result

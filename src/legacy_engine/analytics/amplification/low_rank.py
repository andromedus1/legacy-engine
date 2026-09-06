from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Literal

import numpy as np
from pydantic import ConfigDict
from scipy.optimize import minimize

from legacy_engine.models.base import LegacyEngineModel

from ._common import digest, make_prediction, sigmoid
from .corpus import pair_from_key, rows_for_pair


class LowRankFit(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")
    fit_id: str
    method_id: Literal[
        "skew-low-rank-r1-v1", "skew-low-rank-r2-v1", "skew-low-rank-r4-v1"
    ]
    rank: Literal[1, 2, 4]
    entity_order: tuple[str, ...]
    strengths: tuple[float, ...]
    left_factors: tuple[tuple[float, ...], ...]
    right_factors: tuple[tuple[float, ...], ...]
    objective: float
    gradient_norm: float
    converged: bool
    stable_multistarts: int
    event_bootstrap_successes: int = 0
    reasons: tuple[str, ...] = ()


def _parameters(profile, rank):
    return next(
        x for x in profile.method_specs if x.method_id == f"skew-low-rank-r{rank}-v1"
    ).parameters


def _unpack(vector, n, rank):
    s = vector[:n]
    u = vector[n : n + n * rank].reshape(n, rank)
    v = vector[n + n * rank :].reshape(n, rank)
    return s, u, v


def _objective(vector, observations, n, rank, l2):
    s, u, v = _unpack(vector, n, rank)
    gradient = np.zeros_like(vector)
    gs, gu, gv = _unpack(gradient, n, rank)
    value = 0.0
    for i, j, y in observations:
        eta = s[i] - s[j] + u[i] @ v[j] - v[i] @ u[j]
        value += np.logaddexp(0.0, eta) - y * eta
        delta = sigmoid(float(eta)) - y
        gs[i] += delta
        gs[j] -= delta
        gu[i] += delta * v[j]
        gv[j] += delta * u[i]
        gv[i] -= delta * u[j]
        gu[j] -= delta * v[i]
    value += 0.5 * l2 * float(vector @ vector) + 10.0 * float(s.mean() ** 2)
    gradient += l2 * vector
    gs += 20.0 * s.mean() / n
    return value, gradient


def _graph_reasons(corpus, rank):
    neighbors = defaultdict(set)
    degrees = Counter()
    observed_edges = set()
    for row in corpus.outcomes:
        neighbors[row.subject].add(row.opponent)
        neighbors[row.opponent].add(row.subject)
        observed_edges.add(frozenset((row.subject, row.opponent)))
        degrees[row.subject] += 1
        degrees[row.opponent] += 1
    if not corpus.entities:
        return ("empty-comparison-graph",)
    seen = {corpus.entities[0]}
    queue = deque(seen)
    while queue:
        node = queue.popleft()
        unseen = neighbors[node] - seen
        seen.update(unseen)
        queue.extend(unseen)
    reasons = []
    if len(seen) != len(corpus.entities):
        reasons.append("disconnected-comparison-graph")
    if (
        len(corpus.outcomes) < max(3, rank * len(corpus.entities))
        or len(observed_edges) < rank + 2
    ):
        reasons.append("insufficient-rank-support")
    return tuple(reasons)


def fit_skew_low_rank(corpus, *, rank, profile):
    params = _parameters(profile, rank)
    method = f"skew-low-rank-r{rank}-v1"
    entities = tuple(sorted(corpus.entities))
    index = {x: i for i, x in enumerate(entities)}
    observations = [
        (index[r.subject], index[r.opponent], float(r.subject_won))
        for r in corpus.outcomes
    ]
    size = len(entities) * (1 + 2 * rank)
    spec = next(x for x in profile.method_specs if x.method_id == method)
    rng = np.random.default_rng(profile.seed + spec.seed_offset)
    results = []
    for start in range(params.multistarts):
        initial = np.zeros(size) if start == 0 else rng.normal(0, 0.05, size)
        results.append(
            minimize(
                lambda x: _objective(
                    x, observations, len(entities), rank, params.l2_strength
                ),
                initial,
                jac=True,
                method="L-BFGS-B",
                options={"maxiter": params.max_iterations, "ftol": 1e-10},
            )
        )
    best = min(results, key=lambda x: x.fun)
    s, u, v = _unpack(best.x, len(entities), rank)
    s = s - s.mean()
    induced = [
        [
            sigmoid(float(s[i] - s[j] + u[i] @ v[j] - v[i] @ u[j]))
            for j in range(len(entities))
        ]
        for i in range(len(entities))
    ]
    stable = sum(
        abs(result.fun - best.fun) <= max(1e-5, abs(best.fun) * 1e-4)
        for result in results
    )
    reasons = list(_graph_reasons(corpus, rank))
    if not best.success:
        reasons.append("optimizer-did-not-converge")
    if stable < max(1, params.multistarts // 2):
        reasons.append("unstable-multistart")
    fit_id = f"{method}:{digest({'corpus': corpus.corpus_id, 'parameters': params.model_dump(mode='json'), 'seed': profile.seed + spec.seed_offset, 'induced': induced})}"
    return LowRankFit(
        fit_id=fit_id,
        method_id=method,
        rank=rank,
        entity_order=entities,
        strengths=tuple(float(x) for x in s),
        left_factors=tuple(tuple(float(x) for x in row) for row in u),
        right_factors=tuple(tuple(float(x) for x in row) for row in v),
        objective=float(best.fun),
        gradient_norm=float(np.linalg.norm(best.jac)),
        converged=bool(best.success),
        stable_multistarts=stable,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def low_rank_probability(fit, subject, opponent):
    index = {x: i for i, x in enumerate(fit.entity_order)}
    if subject not in index or opponent not in index:
        return 0.5
    i, j = index[subject], index[opponent]
    u = np.asarray(fit.left_factors)
    v = np.asarray(fit.right_factors)
    return sigmoid(
        fit.strengths[i] - fit.strengths[j] + float(u[i] @ v[j] - v[i] @ u[j])
    )


def predict_skew_low_rank(fit, corpus, baselines, profile, *, diagnostics=True):
    degree = Counter()
    neighbors = defaultdict(set)
    for row in corpus.outcomes:
        degree[row.subject] += 1
        degree[row.opponent] += 1
        neighbors[row.subject].add(row.opponent)
        neighbors[row.opponent].add(row.subject)
    current_fit = None
    leave_out_fits = {}
    if diagnostics:
        current_fit = fit_skew_low_rank(
            corpus.model_copy(
                update={
                    "corpus_id": digest(
                        {"origin": corpus.corpus_id, "ablation": "current-only"}
                    ),
                    "outcomes": tuple(
                        row for row in corpus.outcomes if row.origin == "current-direct"
                    ),
                }
            ),
            rank=fit.rank,
            profile=profile,
        )
        for key in baselines:
            subject, opponent = pair_from_key(key)
            unordered = tuple(sorted((subject, opponent)))
            if unordered in leave_out_fits:
                continue
            leave_out_fits[unordered] = fit_skew_low_rank(
                corpus.model_copy(
                    update={
                        "corpus_id": digest(
                            {"origin": corpus.corpus_id, "leave_pair_out": unordered}
                        ),
                        "outcomes": tuple(
                            row
                            for row in corpus.outcomes
                            if (row.subject, row.opponent) != unordered
                        ),
                    }
                ),
                rank=fit.rank,
                profile=profile,
            )
    return {
        key: make_prediction(
            fit.method_id,
            *pair_from_key(key),
            rows_for_pair(corpus, *pair_from_key(key)),
            low_rank_probability(fit, *pair_from_key(key)),
            fit_id=fit.fit_id,
            gates=profile.service_gates,
            without_history=(
                low_rank_probability(current_fit, *pair_from_key(key))
                if current_fit is not None
                else low_rank_probability(fit, *pair_from_key(key))
            ),
            without_borrowing=low_rank_probability(fit, *pair_from_key(key)),
            leave_target_out=(
                low_rank_probability(
                    leave_out_fits[tuple(sorted(pair_from_key(key)))],
                    *pair_from_key(key),
                )
                if diagnostics
                else None
            ),
            comparison_graph_degree=min(
                degree[pair_from_key(key)[0]], degree[pair_from_key(key)[1]]
            ),
            computation_reasons=(
                *fit.reasons,
                *(
                    ("niche-unsupported",)
                    if min(
                        len(neighbors[pair_from_key(key)[0]]),
                        len(neighbors[pair_from_key(key)[1]]),
                    )
                    <= fit.rank
                    else ()
                ),
            ),
        )
        for key in sorted(baselines)
    }

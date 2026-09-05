"""Current-field deck ranking from coherent matchup-cell posteriors.

This is a separate decision projection from the legacy positioning and benchmark
estimators.  ``RankingCellMeasurement.selected`` is a gate-oriented legacy
projection and is deliberately ignored: an era source wins whenever present,
including when thin or empty, and fallback is used only when era is absent.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from scipy.stats import beta as beta_distribution

from legacy_engine.advisory.ranking_measurement import (
    RankingCellMeasurement,
    RankingCellSource,
)
from legacy_engine.models.matchup import MatchupCell

_DEFAULT_DRAWS = 10_000
_DEFAULT_SEED = 730_021
_MISSING_PRIOR_MEAN = 0.5
_MISSING_PRIOR_STRENGTH = 2.0
_BAD_MATCHUP_THRESHOLD = 0.45

__all__ = ["rank_matchup_rows"]


def _number(value: object, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _validate_cell(cell: MatchupCell, *, subject: str, opponent: str) -> MatchupCell:
    if cell.archetype_a != subject or cell.archetype_b != opponent:
        raise ValueError(f"cell identity does not match ledger for {subject} vs {opponent}")
    if not isinstance(cell.n, int) or cell.n < 0:
        raise ValueError(f"cell n must be a non-negative integer for {subject} vs {opponent}")
    if not isinstance(cell.wins, int) or not 0 <= cell.wins <= cell.n:
        raise ValueError(f"cell wins must be between 0 and n for {subject} vs {opponent}")
    prior_mean = _MISSING_PRIOR_MEAN if cell.prior_mean is None else _number(
        cell.prior_mean, name="cell prior_mean"
    )
    if not 0.0 <= prior_mean <= 1.0:
        raise ValueError(f"cell prior_mean must be between 0 and 1 for {subject} vs {opponent}")
    prior_strength = _number(cell.prior_strength, name="cell prior_strength")
    if prior_strength <= 0.0:
        raise ValueError(f"cell prior_strength must be positive for {subject} vs {opponent}")
    return cell


def _validate_source(
    source: RankingCellSource, *, subject: str, opponent: str
) -> MatchupCell:
    cell = _validate_cell(source.cell, subject=subject, opponent=opponent)
    window = source.pair_window
    if window is not None and (
        window.subject != subject
        or window.opponent != opponent
        or window.effective_since != source.since
    ):
        raise ValueError(f"invalid pair-window provenance for {subject} vs {opponent}")
    return cell


def _beta_draws(
    rng: np.random.Generator, alpha: float, beta: float, draws: int
) -> np.ndarray:
    if alpha <= 0.0:
        return np.zeros(draws, dtype=np.float64)
    if beta <= 0.0:
        return np.ones(draws, dtype=np.float64)
    return rng.beta(alpha, beta, size=draws)


def _beta_interval(alpha: float, beta: float) -> tuple[float, float]:
    if alpha <= 0.0:
        return 0.0, 0.0
    if beta <= 0.0:
        return 1.0, 1.0
    low, high = beta_distribution.ppf([0.025, 0.975], alpha, beta)
    return float(low), float(high)


def _interval(values: np.ndarray) -> list[float]:
    low, high = np.quantile(values, [0.025, 0.975])
    return [float(low), float(high)]


def _resolve_source(
    subject: str,
    opponent: str,
    measurement: RankingCellMeasurement | None,
    overrides: Mapping[tuple[str, str], MatchupCell],
    override_sources: Mapping[tuple[str, str], str],
) -> tuple[MatchupCell | None, str, str | None]:
    key = (subject, opponent)
    if key in overrides:
        cell = overrides[key]
        return cell, override_sources.get(key, "interval-override"), cell.prior_source
    if measurement is None:
        return None, "missing", "weak 50% prior (missing cell)"
    # Source choice is independent of the old selected/gate field.
    source = measurement.era if measurement.era is not None else measurement.fallback
    if source is None:
        return None, "missing", "weak 50% prior (missing cell)"
    return source.cell, source.kind, source.cell.prior_source


def _cell_payload(
    *,
    subject: str,
    opponent: str,
    field_share: float,
    cell: MatchupCell | None,
    source_kind: str,
    prior_source: str | None,
    direct: bool,
    is_mirror: bool,
    mean: float,
    ci_low: float,
    ci_high: float,
) -> dict[str, Any]:
    if cell is None:
        wins = n = 0
        prior_mean = _MISSING_PRIOR_MEAN
        prior_strength = _MISSING_PRIOR_STRENGTH
    else:
        wins = int(cell.wins)
        n = int(cell.n)
        prior_mean = _MISSING_PRIOR_MEAN if cell.prior_mean is None else float(cell.prior_mean)
        prior_strength = float(cell.prior_strength)
    return {
        "subject": subject,
        "opponent": opponent,
        "field_share": float(field_share),
        "mean": float(mean),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "wins": wins,
        "n": n,
        "prior_mean": float(prior_mean),
        "prior_strength": float(prior_strength),
        "prior_source": prior_source,
        "source_kind": source_kind,
        "direct": bool(direct),
        "is_mirror": bool(is_mirror),
    }


def _validate_inputs(
    rows: Mapping[str, Sequence[RankingCellMeasurement]],
    shares: Mapping[str, float],
    counts: Mapping[str, float] | None,
    *,
    draws: int,
    seed: int,
    candidate_presence: Mapping[str, float] | None,
    overrides: Mapping[tuple[str, str], MatchupCell],
    override_sources: Mapping[tuple[str, str], str],
) -> tuple[dict[str, float], dict[str, float] | None]:
    if not isinstance(rows, Mapping) or not isinstance(shares, Mapping):
        raise ValueError("rows and shares must be mappings")
    if not isinstance(draws, int) or draws < 1:
        raise ValueError("draws must be a positive integer")
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    field: dict[str, float] = {}
    for label, value in shares.items():
        if not isinstance(label, str) or not label:
            raise ValueError("field share labels must be non-empty strings")
        share = _number(value, name=f"field share for {label}")
        if share < 0.0:
            raise ValueError("field shares must be non-negative")
        field[label] = share
    total = sum(field.values())
    if total <= 0.0:
        raise ValueError("field shares must have positive total mass")
    field = {label: share / total for label, share in field.items()}

    resolved_counts: dict[str, float] | None = None
    if counts is not None:
        if not isinstance(counts, Mapping) or set(counts) != set(field):
            raise ValueError("counts must cover exactly the field share labels")
        resolved_counts = {}
        for label in field:
            count = _number(counts[label], name=f"field count for {label}")
            if count < 0.0:
                raise ValueError("field counts must be non-negative")
            resolved_counts[label] = count
        if sum(resolved_counts.values()) <= 0.0:
            raise ValueError("field counts must have positive total mass")
        if any(share <= 0.0 for share in field.values()):
            raise ValueError("field shares must be positive when counts are supplied")

    if candidate_presence is not None:
        if not isinstance(candidate_presence, Mapping):
            raise ValueError("candidate presence must be a mapping")
        for label, value in candidate_presence.items():
            if not isinstance(label, str) or not label:
                raise ValueError("candidate presence labels must be non-empty strings")
            if _number(value, name=f"candidate presence for {label}") < 0.0:
                raise ValueError("candidate presence must be non-negative")

    for subject, measurements in rows.items():
        if not isinstance(subject, str) or not subject:
            raise ValueError("row labels must be non-empty strings")
        if isinstance(measurements, (str, bytes)) or not isinstance(measurements, Sequence):
            raise ValueError(f"row measurements must be a sequence for {subject}")
        seen: set[str] = set()
        for measurement in measurements:
            if not isinstance(measurement, RankingCellMeasurement):
                raise ValueError(f"rows must contain RankingCellMeasurement values for {subject}")
            opponent = measurement.opponent
            if measurement.subject != subject:
                raise ValueError(f"ranking cell subject does not match row key for {subject}")
            if not isinstance(opponent, str) or not opponent:
                raise ValueError(f"opponent labels must be non-empty strings for {subject}")
            if opponent in seen:
                raise ValueError(f"duplicate ranking opponent: {subject} vs {opponent}")
            seen.add(opponent)
            if _number(measurement.field_share, name="cell field share") < 0.0:
                raise ValueError("cell field shares must be non-negative")
            # ``selected`` is ignored by this estimator and is therefore not validated.
            for source in (measurement.era, measurement.fallback):
                if source is not None:
                    _validate_source(source, subject=subject, opponent=opponent)

    if not isinstance(overrides, Mapping) or not isinstance(override_sources, Mapping):
        raise ValueError("cell_overrides and override_sources must be mappings")
    for key, cell in overrides.items():
        if not isinstance(key, tuple) or len(key) != 2 or not all(isinstance(part, str) for part in key):
            raise ValueError("cell override keys must be (subject, opponent) string tuples")
        if not isinstance(cell, MatchupCell):
            raise ValueError("cell overrides must contain MatchupCell values")
        _validate_cell(cell, subject=key[0], opponent=key[1])
    for key, label in override_sources.items():
        if key not in overrides or not isinstance(label, str) or not label:
            raise ValueError("override source labels must name a cell override")
    return field, resolved_counts


def rank_matchup_rows(
    rows: Mapping[str, Sequence[RankingCellMeasurement]],
    shares: Mapping[str, float],
    *,
    counts: Mapping[str, float] | None = None,
    draws: int = _DEFAULT_DRAWS,
    seed: int = _DEFAULT_SEED,
    cell_overrides: Mapping[tuple[str, str], MatchupCell] | None = None,
    override_sources: Mapping[tuple[str, str], str] | None = None,
    candidate_presence: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Return full-field posterior performance and non-mirror matchup floor.

    Cell point estimates are analytic Beta posterior means using the cell's
    supplied prior.  Missing cells use a weak 50% Beta(1, 1) prior.  Draws are
    used for row intervals, the minimum's interval, ``P(performance > .5)``,
    and expected bad-matchup exposure.  The empirical-Bayes prior is treated as
    conditional: prior-estimation uncertainty is omitted from intervals, and a
    prior may contain some of the cell's information.
    """
    overrides = {} if cell_overrides is None else dict(cell_overrides)
    override_sources = {} if override_sources is None else dict(override_sources)
    field, field_counts = _validate_inputs(
        rows,
        shares,
        counts,
        draws=draws,
        seed=seed,
        candidate_presence=candidate_presence,
        overrides=overrides,
        override_sources=override_sources,
    )
    labels = tuple(sorted(field))
    measurements_by_row = {
        subject: {measurement.opponent: measurement for measurement in measurements}
        for subject, measurements in rows.items()
    }
    rng = np.random.default_rng(seed)
    base_weights = np.asarray([field[label] for label in labels], dtype=np.float64)
    if field_counts is None:
        field_draws = np.tile(base_weights, (draws, 1))
    else:
        count_total = sum(field_counts.values())
        # Counts provide concentration only.  Shares remain the field posterior
        # center; this avoids a count map silently moving the supplied field.
        field_draws = rng.dirichlet(
            np.asarray([field[label] * count_total for label in labels]), size=draws
        )

    output_rows: dict[str, dict[str, Any]] = {}
    for subject in sorted(rows):
        measurements = measurements_by_row[subject]
        samples = np.empty((draws, len(labels)), dtype=np.float64)
        records: list[dict[str, Any]] = []
        means: list[float] = []
        floor_candidates: list[tuple[float, str, int]] = []
        nonmirror_mass = direct_nonmirror_mass = 0.0
        direct_cells = 0

        for index, opponent in enumerate(labels):
            cell, source_kind, prior_source = _resolve_source(
                subject, opponent, measurements.get(opponent), overrides, override_sources
            )
            if cell is None:
                prior_mean, prior_strength, wins, n = (
                    _MISSING_PRIOR_MEAN,
                    _MISSING_PRIOR_STRENGTH,
                    0,
                    0,
                )
            else:
                _validate_cell(cell, subject=subject, opponent=opponent)
                prior_mean = _MISSING_PRIOR_MEAN if cell.prior_mean is None else float(cell.prior_mean)
                prior_strength = float(cell.prior_strength)
                wins, n = int(cell.wins), int(cell.n)

            # Mirror status is structural: a camp versus its parent is not a mirror.
            is_mirror = subject == opponent
            direct = cell is not None and n > 0
            if is_mirror:
                mean, ci_low, ci_high = 0.5, 0.5, 0.5
                samples[:, index] = 0.5
            else:
                alpha = wins + prior_mean * prior_strength
                beta = n - wins + (1.0 - prior_mean) * prior_strength
                mean = alpha / (alpha + beta) if alpha + beta else prior_mean
                ci_low, ci_high = _beta_interval(alpha, beta)
                samples[:, index] = _beta_draws(rng, alpha, beta, draws)
                if field[opponent] > 0.0:
                    nonmirror_mass += field[opponent]
                    floor_candidates.append((mean, opponent, index))
                    if direct:
                        direct_nonmirror_mass += field[opponent]
                        direct_cells += 1
            means.append(mean)
            records.append(_cell_payload(
                subject=subject,
                opponent=opponent,
                field_share=field[opponent],
                cell=cell,
                source_kind=source_kind,
                prior_source=prior_source,
                direct=direct,
                is_mirror=is_mirror,
                mean=mean,
                ci_low=ci_low,
                ci_high=ci_high,
            ))

        performance_draws = np.sum(field_draws * samples, axis=1)
        performance = float(np.dot(base_weights, np.asarray(means)))
        if floor_candidates:
            floor, worst_opponent, _ = min(floor_candidates, key=lambda item: (item[0], item[1]))
            floor_draws = np.min(samples[:, [item[2] for item in floor_candidates]], axis=1)
            floor_interval = _interval(floor_draws)
        else:
            floor = None
            worst_opponent = None
            floor_interval = None
        bad_exposure_draws = np.sum(
            field_draws * (samples < _BAD_MATCHUP_THRESHOLD), axis=1
        )
        presence = (
            float(candidate_presence[subject])
            if candidate_presence is not None and subject in candidate_presence
            else field.get(subject, 0.0)
        )
        nonmirror_coverage = (
            direct_nonmirror_mass / nonmirror_mass if nonmirror_mass > 0.0 else 1.0
        )
        output_rows[subject] = {
            "subject": subject,
            "subject_field_share": presence,
            "cells": records,
            "performance": performance,
            "performance_interval": _interval(performance_draws),
            "p_performance_gt_0_5": float(np.mean(performance_draws > 0.5)),
            "floor": None if floor is None else float(floor),
            "floor_interval": floor_interval,
            "worst_opponent": worst_opponent,
            "bad_matchup_field_exposure": float(np.mean(bad_exposure_draws)),
            "bad_matchup_field_exposure_interval": _interval(bad_exposure_draws),
            "nonmirror_coverage": float(nonmirror_coverage),
            "direct_support": direct_cells > 0,
            "eligible": direct_cells > 0 and presence > 0.0,
            "pareto": False,
        }

    subjects = sorted(output_rows)
    for subject in subjects:
        row = output_rows[subject]
        floor = row["floor"]
        row["pareto"] = bool(row["eligible"] and floor is not None) and not any(
            other != subject
            and output_rows[other]["eligible"]
            and output_rows[other]["floor"] is not None
            and output_rows[other]["performance"] >= row["performance"]
            and output_rows[other]["floor"] >= floor
            and (
                output_rows[other]["performance"] > row["performance"]
                or output_rows[other]["floor"] > floor
            )
            for other in subjects
        )
    frontier = [
        subject for subject in sorted(
            subjects,
            key=lambda label: (
                -output_rows[label]["performance"],
                -(output_rows[label]["floor"] if output_rows[label]["floor"] is not None else -1.0),
                label,
            ),
        )
        if output_rows[subject]["pareto"] and output_rows[subject]["eligible"]
    ]
    return {
        "rows": output_rows,
        "efficient_frontier": frontier,
        "field": {
            "shares": {label: float(field[label]) for label in labels},
            "counts": None if field_counts is None else {
                label: float(field_counts[label]) for label in labels
            },
        },
        "draws": draws,
        "seed": seed,
        "method": {
            "posterior": "conditional_beta_binomial",
            "missing_prior_mean": _MISSING_PRIOR_MEAN,
            "missing_prior_strength": _MISSING_PRIOR_STRENGTH,
            "bad_matchup_threshold": _BAD_MATCHUP_THRESHOLD,
            "coverage": "positive direct n; non-mirror field share; no threshold",
            "era_preferred": True,
            "overlapping_sources_combined": False,
            "mirror_performance": "structural 0.5 included",
            "mirror_floor": "excluded",
            "prior_uncertainty": "conditional; prior estimation uncertainty omitted",
        },
    }

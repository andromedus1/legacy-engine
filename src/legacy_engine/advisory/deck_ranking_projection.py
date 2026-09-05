"""Shared production projection for current deck-ranking estimates.

The ranking page and the historical evaluator must make the same source choice
before applying the posterior kernel.  This module is the small handoff between
the typed measurement ledger and :func:`rank_matchup_rows`; it deliberately
does not implement a second ranking estimator.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from legacy_engine.advisory.deck_ranking import rank_matchup_rows
from legacy_engine.advisory.ranking_measurement import (
    RankingCellMeasurement,
    RankingCellSource,
)
from legacy_engine.models.matchup import MatchupCell

_MISSING_PRIOR_MEAN = 0.5
_MISSING_PRIOR_STRENGTH = 2.0


def _validate_prior_scale(value: object) -> float:
    try:
        scale = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("prior_scale must be finite and positive") from exc
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("prior_scale must be finite and positive")
    return scale


def _scaled_cell(cell: MatchupCell, scale: float) -> MatchupCell:
    """Return a cell with only its positive prior strength changed."""
    strength = float(cell.prior_strength)
    if not math.isfinite(strength) or strength <= 0.0:
        raise ValueError("selected matchup cell prior_strength must be positive and finite")
    return cell.model_copy(update={"prior_strength": strength * scale})


def _missing_cell(subject: str, opponent: str, scale: float) -> MatchupCell:
    """Materialize the named weak prior so challengers scale n=0 uncertainty too."""
    return MatchupCell(
        archetype_a=subject,
        archetype_b=opponent,
        wins=0,
        n=0,
        p_raw=None,
        p_shrunk=_MISSING_PRIOR_MEAN,
        ci_low=None,
        ci_high=None,
        tier="speculative",
        display=False,
        prior_mean=_MISSING_PRIOR_MEAN,
        prior_source="weak 50% prior (missing cell)",
        prior_strength=_MISSING_PRIOR_STRENGTH * scale,
    )


def _source_identity(
    source: RankingCellSource | None,
    *,
    source_kind: str,
    cell: MatchupCell | None,
) -> dict[str, Any]:
    """Serialize the complete selected source, including its original cell."""
    if source is not None:
        return source.model_dump(mode="json")
    return {
        "kind": source_kind,
        "since": None,
        "cell": None if cell is None else cell.model_dump(mode="json"),
        "pair_window": None,
        "concentration_warning": None,
    }


def project_ranking_rows(
    rows: Mapping[str, Sequence[RankingCellMeasurement]],
    shares: Mapping[str, float],
    *,
    counts: Mapping[str, float] | None = None,
    candidate_presence: Mapping[str, float] | None = None,
    cell_overrides: Mapping[tuple[str, str], MatchupCell] | None = None,
    override_sources: Mapping[tuple[str, str], str] | None = None,
    prior_scale: float = 1.0,
    draws: int = 10_000,
    seed: int = 730_021,
) -> dict[str, Any]:
    """Project the current field with one explicitly selected source per cell.

    ``prior_scale`` is a fixed sensitivity parameter.  It scales the selected
    cell's actual Beta prior strength, including the named weak prior for an
    absent cell.  The default is exactly the production kernel's prior.  The
    input ledger is never mutated; source identity in each output cell refers
    to the unscaled source while ``prior_strength_effective`` records the value
    used by the posterior.
    """
    scale = _validate_prior_scale(prior_scale)
    overrides = {} if cell_overrides is None else dict(cell_overrides)
    sources = {} if override_sources is None else dict(override_sources)
    working: dict[str, tuple[RankingCellMeasurement, ...]] = {}
    resolved: dict[tuple[str, str], tuple[MatchupCell | None, str, RankingCellSource | None]] = {}

    for subject, measurements in rows.items():
        rewritten: list[RankingCellMeasurement] = []
        seen_opponents: set[str] = set()
        for measurement in measurements:
            key = (subject, measurement.opponent)
            seen_opponents.add(measurement.opponent)
            if key in overrides:
                original = overrides[key]
                source_kind = sources.get(key, "interval-override")
                effective = _scaled_cell(original, scale)
                overrides[key] = effective
                resolved[key] = (original, source_kind, None)
                rewritten.append(measurement)
                continue

            source = measurement.era if measurement.era is not None else measurement.fallback
            if source is None:
                # A concrete n=0 cell lets rank_matchup_rows use the same named
                # weak prior while retaining its existing ``missing`` source kind.
                missing = _missing_cell(subject, measurement.opponent, scale)
                overrides[key] = missing
                sources[key] = "missing"
                resolved[key] = (None, "missing", None)
                rewritten.append(measurement)
                continue

            original = source.cell
            effective = _scaled_cell(original, scale)
            replacement = source.model_copy(update={"cell": effective})
            if measurement.era is source:
                rewritten.append(measurement.model_copy(update={"era": replacement}))
            elif measurement.fallback is source:
                rewritten.append(measurement.model_copy(update={"fallback": replacement}))
            else:  # pragma: no cover - defensive for unusual model implementations
                rewritten.append(measurement)
            resolved[key] = (original, source.kind, source)
        for opponent in shares:
            if opponent in seen_opponents or (subject, opponent) in overrides:
                continue
            key = (subject, opponent)
            overrides[key] = _missing_cell(subject, opponent, scale)
            sources[key] = "missing"
            resolved[key] = (None, "missing", None)
        working[subject] = tuple(rewritten)

    # Overrides may include a pair whose measurement exists in another row shape;
    # rank_matchup_rows validates their identity and applies them before sources.
    for key, original in list(overrides.items()):
        if key not in resolved:
            source_kind = sources.get(key, "interval-override")
            resolved[key] = (original, source_kind, None)
            overrides[key] = _scaled_cell(original, scale)

    result = rank_matchup_rows(
        working,
        shares,
        counts=counts,
        candidate_presence=candidate_presence,
        cell_overrides=overrides,
        override_sources=sources,
        draws=draws,
        seed=seed,
    )

    for subject, row in result["rows"].items():
        for cell in row["cells"]:
            key = (subject, cell["opponent"])
            original, source_kind, source = resolved.get(key, (None, "missing", None))
            original_strength = (
                _MISSING_PRIOR_STRENGTH if original is None else float(original.prior_strength)
            )
            effective_strength = float(cell["prior_strength"])
            # Matchup rows include mirrors for field performance; the same
            # posterior weight definition remains useful provenance for them.
            cell.update({
                "prior_strength_original": original_strength,
                "prior_strength_effective": effective_strength,
                "original_prior_strength": original_strength,
                "effective_prior_strength": effective_strength,
                "prior_contribution_fraction": effective_strength / (
                    effective_strength + int(cell["n"])
                ),
                "source_identity": _source_identity(
                    source, source_kind=source_kind, cell=original,
                ),
            })
    result["prior_scale"] = scale
    result["method"] = {
        **result["method"],
        "prior_scale": scale,
        "source_resolution": "era if present, otherwise fallback; explicit override first",
        "prior_contribution": "effective prior strength / (effective prior strength + n)",
    }
    return result


__all__ = ["project_ranking_rows"]

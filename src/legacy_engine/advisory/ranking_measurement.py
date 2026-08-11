"""Typed, replayable measurement ledger for Best Call ranking rows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Literal

import numpy as np

from legacy_engine.analytics.matchup import DISPLAY_GATE_N
from legacy_engine.analytics.eras.consume import PairWindow
from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.models.matchup import MatchupCell

CellSourceKind = Literal["era", "ban-fallback", "full-corpus", "strict-common-era"]
MethodologyVariantId = Literal["raw", "ci-gated", "ban-scoped", "era-only"]
SourcePolicy = Literal["selected", "fallback", "era"]
RateBasis = Literal["raw", "shrunk"]

LEAN_DRAWS = 20_000
LEAN_SEED = 730_021
LEAN_TEMPERATURE = 0.05
LEAN_PRECISION_SCALE = float(DISPLAY_GATE_N)
_NO_DATA_STRENGTH = 2.0
_BETA_JEFFREYS = 0.5


class RankingCellSource(LegacyEngineModel):
    kind: CellSourceKind
    since: str | None
    cell: MatchupCell
    pair_window: PairWindow | None = None
    concentration_warning: str | None = None


class RankingCellMeasurement(LegacyEngineModel):
    subject: str
    opponent: str
    field_share: float
    era: RankingCellSource | None
    fallback: RankingCellSource | None
    selected_kind: CellSourceKind | None
    selected: RankingCellSource | None
    selection_reason: str
    measured: bool
    concentration_warning: str | None


class FloorObservability(LegacyEngineModel):
    opponents_total: int
    opponents_n10: int
    opponents_display_grade: int
    display_grade_field_coverage: float
    floor_observed: bool
    reason: str | None


class RowReconciliation(LegacyEngineModel):
    adaptive_selected: float | None
    serialized_recompute: float | None
    parity_delta: float | None
    strict_common_since: str | None
    strict_common: float | None
    strict_common_contributing_coverage: float
    strict_common_coverage: float
    estimator_delta: float | None
    headline_eligible: bool
    reason: str | None


class RankingRowMeasurement(LegacyEngineModel):
    subject: str
    cells: tuple[RankingCellMeasurement, ...]
    adjusted_field_wr: float | None
    floor: float | None
    floor_opponent: str | None
    agency: float | None
    measured_coverage: float
    top_k_measured: bool
    grounded: bool
    floor_observability: FloorObservability
    reconciliation: RowReconciliation


class MethodologyVariantSpec(LegacyEngineModel):
    id: MethodologyVariantId
    label: str
    source_policy: SourcePolicy
    rate_basis: RateBasis
    evidence_n: int


class VariantRowMeasurement(LegacyEngineModel):
    variant: MethodologyVariantId
    adjusted_field_wr: float | None
    floor: float | None
    agency: float | None
    measured_coverage: float
    top_k_measured: bool
    resolved_cells: int
    valid: bool = True
    reason: str | None = None


class LeanAgencyMeasurement(LegacyEngineModel):
    q25: float
    median: float
    ci_low: float
    ci_high: float
    resolved_share: float
    imputed_share: float
    draws: int
    seed: int
    temperature: float
    precision_scale: float
    source_policy: str


class RankStability(LegacyEngineModel):
    ranks: dict[MethodologyVariantId, int | None]
    rank_min: int | None
    rank_max: int | None
    rank_span: int | None
    missing_variants: tuple[MethodologyVariantId, ...]
    reason: str | None


def methodology_variant_specs(ground_n: int) -> tuple[MethodologyVariantSpec, ...]:
    """The predeclared, outcome-blind perturbations used by Best Call."""
    if ground_n < 1:
        raise ValueError("ground_n must be >= 1")
    return (
        MethodologyVariantSpec(
            id="raw", label="Raw selected", source_policy="selected",
            rate_basis="raw", evidence_n=1,
        ),
        MethodologyVariantSpec(
            id="ci-gated", label="CI-gated headline", source_policy="selected",
            rate_basis="shrunk", evidence_n=ground_n,
        ),
        MethodologyVariantSpec(
            id="ban-scoped", label="Ban-scoped fallback", source_policy="fallback",
            rate_basis="shrunk", evidence_n=ground_n,
        ),
        MethodologyVariantSpec(
            id="era-only", label="Era only", source_policy="era",
            rate_basis="shrunk", evidence_n=ground_n,
        ),
    )


def _concentration_warning(
    source: RankingCellSource | None, *, ground_n: int, warn_share: float,
) -> str | None:
    if source is None or source.cell.n < ground_n or source.cell.concentration is None:
        return None
    evidence = source.cell.concentration
    parts: list[str] = []
    if evidence.event_share >= warn_share:
        parts.append(
            f"event {evidence.event_id} supplies {evidence.event_n}/{source.cell.n} "
            f"matches ({evidence.event_share:.0%})"
        )
    if evidence.month_share >= warn_share:
        parts.append(
            f"month {evidence.month} supplies {evidence.month_n}/{source.cell.n} "
            f"matches ({evidence.month_share:.0%})"
        )
    if not parts:
        return None
    window = source.since or "full corpus"
    return f"concentrated selected window since {window}: " + "; ".join(parts)


def select_ranking_cell(
    subject: str,
    opponent: str,
    field_share: float,
    *,
    era: RankingCellSource | None,
    fallback: RankingCellSource | None,
    ground_n: int,
    concentration_warn_share: float = 0.40,
) -> RankingCellMeasurement:
    """Apply the outcome-blind era/fallback truth table used by the ranking page."""
    if ground_n < 1:
        raise ValueError("ground_n must be >= 1")
    if era is not None and era.cell.n >= ground_n:
        selected, reason = era, f"era cell clears n>={ground_n}"
    elif fallback is not None and fallback.cell.n >= ground_n:
        selected, reason = fallback, f"fallback clears n>={ground_n} after thin/missing era"
    elif era is not None:
        selected, reason = era, f"thin era cell retained below n={ground_n}"
    elif fallback is not None:
        selected, reason = fallback, "era cell absent; thin fallback retained"
    else:
        selected, reason = None, "no era or fallback cell"
    return RankingCellMeasurement(
        subject=subject,
        opponent=opponent,
        field_share=field_share,
        era=era,
        fallback=fallback,
        selected_kind=selected.kind if selected is not None else None,
        selected=selected,
        selection_reason=reason,
        measured=selected is not None and selected.cell.n >= ground_n,
        concentration_warning=(
            selected.concentration_warning
            if selected is not None and selected.cell.n >= ground_n
            and selected.concentration_warning is not None
            else _concentration_warning(
                selected, ground_n=ground_n, warn_share=concentration_warn_share,
            )
        ),
    )


def _weighted_value(sources: Sequence[tuple[float, RankingCellSource]]) -> float | None:
    usable = [(share, source.cell.p_shrunk) for share, source in sources
              if source.cell.n >= 1 and source.cell.p_shrunk is not None]
    mass = sum(share for share, _ in usable)
    return sum(share * value for share, value in usable) / mass if mass else None


def _validate_cells(cells: Sequence[RankingCellMeasurement]) -> str:
    if not cells:
        raise ValueError("ranking cells must not be empty")
    subject = cells[0].subject
    total_share = 0.0
    opponents: set[str] = set()
    for measurement in cells:
        if measurement.subject != subject:
            raise ValueError("ranking cells must share one subject")
        if measurement.opponent in opponents:
            raise ValueError(f"duplicate ranking opponent: {measurement.opponent}")
        opponents.add(measurement.opponent)
        if not math.isfinite(measurement.field_share) or measurement.field_share < 0.0:
            raise ValueError("field shares must be finite and non-negative")
        total_share += measurement.field_share
        for source in (measurement.era, measurement.fallback, measurement.selected):
            if source is None:
                continue
            if (
                source.cell.archetype_a != subject
                or source.cell.archetype_b != measurement.opponent
            ):
                raise ValueError(
                    f"cell identity does not match ledger for {measurement.opponent}"
                )
    if total_share <= 0.0:
        raise ValueError("ranking cells must carry positive field share")
    return subject


def _source_for_policy(
    cell: RankingCellMeasurement, policy: SourcePolicy,
) -> RankingCellSource | None:
    if policy == "selected":
        return cell.selected
    if policy == "fallback":
        return cell.fallback
    return cell.era


def _source_provenance_valid(
    measurement: RankingCellMeasurement, source: RankingCellSource,
) -> bool:
    window = source.pair_window
    return (
        window is not None
        and window.subject == measurement.subject
        and window.opponent == measurement.opponent
        and window.effective_since == source.since
    )


def _summarize_projection(
    cells: Sequence[RankingCellMeasurement],
    *,
    sources: Sequence[RankingCellSource | None],
    values: Sequence[float | None],
    measured: Sequence[bool],
    top_k: int,
) -> tuple[float | None, float | None, float, bool, int]:
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    usable = [
        (cell.field_share, value)
        for cell, source, value in zip(cells, sources, values, strict=True)
        if source is not None and source.cell.n >= 1 and value is not None
    ]
    contributing_mass = sum(share for share, _ in usable)
    adjusted = (
        sum(share * value for share, value in usable) / contributing_mass
        if contributing_mass else None
    )
    floor_values = [
        value
        for source, value, is_measured in zip(sources, values, measured, strict=True)
        if source is not None and is_measured and value is not None
    ]
    floor = min(floor_values) if floor_values else None
    total_share = sum(cell.field_share for cell in cells)
    measured_mass = sum(
        cell.field_share for cell, is_measured in zip(cells, measured, strict=True)
        if is_measured
    )
    measured_coverage = measured_mass / total_share if total_share else 0.0
    top = sorted(range(len(cells)), key=lambda index: cells[index].field_share, reverse=True)[:top_k]
    top_k_measured = bool(top) and all(measured[index] for index in top)
    return adjusted, floor, measured_coverage, top_k_measured, len(usable)


def measure_variant_row(
    cells: Sequence[RankingCellMeasurement],
    *,
    spec: MethodologyVariantSpec,
    top_k: int,
    cover_min: float,
) -> VariantRowMeasurement:
    """Project one row through a predeclared source/rate methodology."""
    _validate_cells(cells)
    if spec.evidence_n < 1:
        raise ValueError("evidence_n must be >= 1")
    if not 0.0 <= cover_min <= 1.0:
        raise ValueError("cover_min must be between 0 and 1")
    sources = [_source_for_policy(cell, spec.source_policy) for cell in cells]
    values = [
        (
            source.cell.p_raw if spec.rate_basis == "raw" else source.cell.p_shrunk
        ) if source is not None else None
        for source in sources
    ]
    measured = [
        source is not None and source.cell.n >= spec.evidence_n
        for source in sources
    ]
    invalid = next((
        cell.opponent
        for cell, source in zip(cells, sources, strict=True)
        if source is not None and not _source_provenance_valid(cell, source)
    ), None)
    adjusted, floor, coverage, top_ok, resolved = _summarize_projection(
        cells, sources=sources, values=values, measured=measured, top_k=top_k,
    )
    if invalid is not None:
        adjusted = floor = None
    valid_values = [value for value in (adjusted, floor) if value is not None]
    return VariantRowMeasurement(
        variant=spec.id,
        adjusted_field_wr=adjusted,
        floor=floor,
        agency=min(valid_values) if valid_values else None,
        measured_coverage=coverage,
        top_k_measured=top_ok,
        resolved_cells=resolved,
        valid=invalid is None,
        reason=(f"invalid pair-window provenance for {invalid}" if invalid is not None else None),
    )


def measure_lean_agency(
    cells: Sequence[RankingCellMeasurement],
    *,
    draws: int = LEAN_DRAWS,
    seed: int = LEAN_SEED,
    temperature: float = LEAN_TEMPERATURE,
    precision_scale: float = LEAN_PRECISION_SCALE,
) -> LeanAgencyMeasurement:
    """Estimate a precision-weighted posterior smooth floor with no sample cliff."""
    _validate_cells(cells)
    if draws < 1:
        raise ValueError("draws must be >= 1")
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("temperature must be finite and > 0")
    if not math.isfinite(precision_scale) or precision_scale <= 0.0:
        raise ValueError("precision_scale must be finite and > 0")

    # Era evidence is always preferred when present. Fallback is used only when
    # the era candidate is absent, avoiding correlated double-counting.
    sources = [cell.era if cell.era is not None else cell.fallback for cell in cells]
    invalid = next((
        cell.opponent
        for cell, source in zip(cells, sources, strict=True)
        if source is not None and not _source_provenance_valid(cell, source)
    ), None)
    if invalid is not None:
        raise ValueError(f"invalid pair-window provenance for {invalid}")

    resolved_rates = [
        source.cell.p_raw
        for source in sources
        if source is not None and source.cell.n > 0 and source.cell.p_raw is not None
    ]
    prior_center = float(np.mean(resolved_rates)) if resolved_rates else 0.5
    total_share = sum(cell.field_share for cell in cells)
    resolved_mass = sum(
        cell.field_share
        for cell, source in zip(cells, sources, strict=True)
        if source is not None and source.cell.n > 0 and source.cell.p_raw is not None
    )

    rng = np.random.default_rng(seed)
    samples = np.empty((draws, len(cells)), dtype=np.float64)
    weights = np.empty(len(cells), dtype=np.float64)
    for index, (measurement, source) in enumerate(zip(cells, sources, strict=True)):
        if source is not None and source.cell.n > 0 and source.cell.p_raw is not None:
            wins = source.cell.wins
            losses = source.cell.n - wins
            if wins < 0 or losses < 0:
                raise ValueError(f"invalid match record for {measurement.opponent}")
            alpha = wins + _BETA_JEFFREYS
            beta = losses + _BETA_JEFFREYS
            strength = source.cell.n + 2.0 * _BETA_JEFFREYS
        else:
            alpha = max(_NO_DATA_STRENGTH * prior_center, 1e-6)
            beta = max(_NO_DATA_STRENGTH * (1.0 - prior_center), 1e-6)
            strength = _NO_DATA_STRENGTH
        samples[:, index] = rng.beta(alpha, beta, size=draws)
        weights[index] = (
            measurement.field_share * strength / (strength + precision_scale)
        )

    weight_sum = float(weights.sum())
    if weight_sum <= 0.0:
        raise ValueError("precision-weighted field share must be positive")
    weights /= weight_sum
    scaled = -samples / temperature
    row_max = scaled.max(axis=1, keepdims=True)
    log_weighted_sum = (
        row_max[:, 0]
        + np.log((np.exp(scaled - row_max) * weights).sum(axis=1))
    )
    agency = np.clip(-temperature * log_weighted_sum, 0.0, 1.0)
    ci_low, q25, median, ci_high = np.quantile(agency, [0.025, 0.25, 0.5, 0.975])
    resolved_share = resolved_mass / total_share
    return LeanAgencyMeasurement(
        q25=float(q25), median=float(median), ci_low=float(ci_low), ci_high=float(ci_high),
        resolved_share=resolved_share, imputed_share=1.0 - resolved_share,
        draws=draws, seed=seed, temperature=temperature, precision_scale=precision_scale,
        source_policy="era-preferred; fallback only when era absent; weak prior when unresolved",
    )


def rank_variant_rows(
    rows: Mapping[str, Mapping[MethodologyVariantId, VariantRowMeasurement]],
    *,
    eligible: Mapping[str, Mapping[MethodologyVariantId, bool]],
) -> dict[str, RankStability]:
    """Assign within-peer competition ranks and complete-only stability spans."""
    variant_ids: tuple[MethodologyVariantId, ...] = (
        "raw", "ci-gated", "ban-scoped", "era-only",
    )
    rank_maps: dict[MethodologyVariantId, dict[str, int]] = {}
    for variant in variant_ids:
        scores = {
            label: measurement[variant].agency
            for label, measurement in rows.items()
            if variant in measurement
            and eligible.get(label, {}).get(variant, False)
            and measurement[variant].agency is not None
        }
        rank_maps[variant] = {
            label: 1 + sum(other > score for other in scores.values())
            for label, score in scores.items()
        }

    result: dict[str, RankStability] = {}
    for label in rows:
        ranks = {variant: rank_maps[variant].get(label) for variant in variant_ids}
        missing = tuple(variant for variant, rank in ranks.items() if rank is None)
        ranked = [rank for rank in ranks.values() if rank is not None]
        complete = not missing
        result[label] = RankStability(
            ranks=ranks,
            rank_min=min(ranked) if complete else None,
            rank_max=max(ranked) if complete else None,
            rank_span=max(ranked) - min(ranked) if complete else None,
            missing_variants=missing,
            reason=(
                None if complete
                else "not ranked by: " + ", ".join(missing)
            ),
        )
    return result


def measure_ranking_row(
    subject: str,
    cells: Sequence[RankingCellMeasurement],
    *,
    top_k: int,
    cover_min: float,
    strict_common_sources: Mapping[str, RankingCellSource],
    strict_common_since: str | None = None,
    display_gate_n: int = DISPLAY_GATE_N,
) -> RankingRowMeasurement:
    """Derive every ranking row metric from the selected-cell ledger once."""
    selected_sources = [cell.selected for cell in cells]
    selected_values = [
        cell.selected.cell.p_shrunk if cell.selected is not None else None
        for cell in cells
    ]
    adaptive, projected_floor, measured_coverage, top_k_measured, _ = _summarize_projection(
        cells,
        sources=selected_sources,
        values=selected_values,
        measured=[cell.measured for cell in cells],
        top_k=top_k,
    )
    measured = [cell for cell in cells if cell.measured]
    total_share = sum(cell.field_share for cell in cells)
    floor_cells = [cell for cell in measured if cell.selected.cell.p_shrunk is not None]
    floor_cell = min(floor_cells, key=lambda cell: cell.selected.cell.p_shrunk) if floor_cells else None
    floor = projected_floor

    projection = [cell.model_dump(mode="json") for cell in cells]
    serialized_sources: list[tuple[float, RankingCellSource]] = []
    for payload in projection:
        source_payload = payload["selected"]
        if source_payload is not None:
            serialized_sources.append(
                (payload["field_share"], RankingCellSource.model_validate(source_payload))
            )
    serialized = _weighted_value(serialized_sources)
    parity_delta = (
        abs(adaptive - serialized) if adaptive is not None and serialized is not None else None
    )

    common = _weighted_value([
        (cell.field_share, strict_common_sources[cell.opponent])
        for cell in cells if cell.opponent in strict_common_sources
    ])
    inferred_common_since = max(
        (source.since for source in strict_common_sources.values() if source.since is not None),
        default=None,
    )
    common_since = strict_common_since if strict_common_since is not None else inferred_common_since
    common_contributing_mass = sum(
        cell.field_share for cell in cells
        if (source := strict_common_sources.get(cell.opponent)) is not None
        and source.cell.n >= 1 and source.cell.p_shrunk is not None
    )
    common_measured_mass = sum(
        cell.field_share for cell in cells
        if (source := strict_common_sources.get(cell.opponent)) is not None
        and source.cell.n >= display_gate_n
    )
    common_coverage = common_measured_mass / total_share if total_share else 0.0

    n10 = sum(
        1 for cell in cells
        if cell.selected is not None and cell.selected.cell.n >= 10
    )
    display_cells = [
        cell for cell in cells
        if cell.selected is not None and cell.selected.cell.n >= display_gate_n
    ]
    display_coverage = (
        sum(cell.field_share for cell in display_cells) / total_share if total_share else 0.0
    )
    observed = bool(display_cells)
    observability = FloorObservability(
        opponents_total=len(cells),
        opponents_n10=n10,
        opponents_display_grade=len(display_cells),
        display_grade_field_coverage=display_coverage,
        floor_observed=observed,
        reason=None if observed else "floor unobserved -- absence of bad cells is not evidence of none",
    )
    parity_ok = (
        (adaptive is None and serialized is None)
        or (parity_delta is not None and parity_delta <= 1e-12)
    )
    invalid_window = next((
        cell for cell in cells
        if cell.selected is not None and (
            cell.selected.pair_window is None
            or cell.selected.pair_window.subject != cell.subject
            or cell.selected.pair_window.opponent != cell.opponent
            or cell.selected.pair_window.effective_since != cell.selected.since
        )
    ), None)
    headline_ok = parity_ok and invalid_window is None
    if not parity_ok:
        reason = "selected-cell ledger does not reproduce serialized row"
    elif invalid_window is not None:
        reason = f"invalid pair-window provenance for {invalid_window.opponent}"
    else:
        reason = None
    reconciliation = RowReconciliation(
        adaptive_selected=adaptive,
        serialized_recompute=serialized,
        parity_delta=parity_delta,
        strict_common_since=common_since,
        strict_common=common,
        strict_common_contributing_coverage=(
            common_contributing_mass / total_share if total_share else 0.0
        ),
        strict_common_coverage=common_coverage,
        estimator_delta=(adaptive - common if adaptive is not None and common is not None else None),
        headline_eligible=headline_ok,
        reason=reason,
    )
    valid_values = [value for value in (adaptive, floor) if value is not None]
    return RankingRowMeasurement(
        subject=subject,
        cells=tuple(cells),
        adjusted_field_wr=adaptive if headline_ok else None,
        floor=floor if headline_ok else None,
        floor_opponent=floor_cell.opponent if headline_ok and floor_cell is not None else None,
        agency=min(valid_values) if headline_ok and valid_values else None,
        measured_coverage=measured_coverage,
        top_k_measured=top_k_measured,
        grounded=headline_ok and top_k_measured and measured_coverage >= cover_min,
        floor_observability=observability,
        reconciliation=reconciliation,
    )

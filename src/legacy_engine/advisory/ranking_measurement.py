"""Typed, replayable measurement ledger for Best Call ranking rows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from legacy_engine.analytics.matchup import DISPLAY_GATE_N
from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.models.matchup import MatchupCell

CellSourceKind = Literal["era", "ban-fallback", "full-corpus", "strict-common-era"]


class RankingCellSource(LegacyEngineModel):
    kind: CellSourceKind
    since: str | None
    cell: MatchupCell


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
        concentration_warning=_concentration_warning(
            selected, ground_n=ground_n, warn_share=concentration_warn_share,
        ),
    )


def _weighted_value(sources: Sequence[tuple[float, RankingCellSource]]) -> float | None:
    usable = [(share, source.cell.p_shrunk) for share, source in sources
              if source.cell.n >= 1 and source.cell.p_shrunk is not None]
    mass = sum(share for share, _ in usable)
    return sum(share * value for share, value in usable) / mass if mass else None


def measure_ranking_row(
    subject: str,
    cells: Sequence[RankingCellMeasurement],
    *,
    top_k: int,
    cover_min: float,
    strict_common_sources: Mapping[str, RankingCellSource],
    display_gate_n: int = DISPLAY_GATE_N,
) -> RankingRowMeasurement:
    """Derive every ranking row metric from the selected-cell ledger once."""
    selected = [(cell.field_share, cell.selected) for cell in cells if cell.selected is not None]
    adaptive = _weighted_value([(share, source) for share, source in selected])
    measured = [cell for cell in cells if cell.measured]
    total_share = sum(cell.field_share for cell in cells)
    measured_coverage = (
        sum(cell.field_share for cell in measured) / total_share if total_share else 0.0
    )
    floor_cells = [cell for cell in measured if cell.selected.cell.p_shrunk is not None]
    floor_cell = min(floor_cells, key=lambda cell: cell.selected.cell.p_shrunk) if floor_cells else None
    floor = floor_cell.selected.cell.p_shrunk if floor_cell is not None else None
    top = sorted(cells, key=lambda cell: cell.field_share, reverse=True)[:top_k]
    top_k_measured = bool(top) and all(cell.measured for cell in top)

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
    common_since = max(
        (source.since for source in strict_common_sources.values() if source.since is not None),
        default=None,
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
    reason = None if parity_ok else "selected-cell ledger does not reproduce serialized row"
    reconciliation = RowReconciliation(
        adaptive_selected=adaptive,
        serialized_recompute=serialized,
        parity_delta=parity_delta,
        strict_common_since=common_since,
        strict_common=common,
        strict_common_coverage=common_coverage,
        estimator_delta=(adaptive - common if adaptive is not None and common is not None else None),
        headline_eligible=parity_ok,
        reason=reason,
    )
    valid_values = [value for value in (adaptive, floor) if value is not None]
    return RankingRowMeasurement(
        subject=subject,
        cells=tuple(cells),
        adjusted_field_wr=adaptive if parity_ok else None,
        floor=floor if parity_ok else None,
        floor_opponent=floor_cell.opponent if parity_ok and floor_cell is not None else None,
        agency=min(valid_values) if parity_ok and valid_values else None,
        measured_coverage=measured_coverage,
        top_k_measured=top_k_measured,
        grounded=parity_ok and top_k_measured and measured_coverage >= cover_min,
        floor_observability=observability,
        reconciliation=reconciliation,
    )

"""Recency-weighted field composition for the deck-ranking projection.

The current project schema is ``tournaments(id, date, source, provenance)``
and ``decks(tournament_id, deck_idx, archetype, variant)``.  The builder uses
the half-open ``[since, until)`` date window and never reads a post-cutoff row.

The returned maps distinguish exact published-list sightings, decay-weighted
composition, and ESS-scaled Dirichlet evidence.  The latter uses Kish ESS,
``(sum(weights) ** 2) / sum(weights ** 2)``, rather than grouped archetype
totals.  For bounded transition support, the host should add bounded integer
prior counts to ``effective_counts`` as posterior concentration while keeping
prior strength separate; pseudo-decks must never be added to ``exact_counts``
or described as current observations.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

import duckdb

_UNKNOWN_SOURCE = "unknown-source"
_UNLABELED_CAMP = "unlabeled"


def _date_only(value: object, *, name: str) -> date:
    if value is None:
        raise ValueError(f"{name} must be an ISO date, got None")
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError(f"{name} must begin with an ISO date, got {value!r}") from exc


@dataclass(frozen=True)
class SourceBreakdown:
    """One source on the observed published-list denominator."""

    source: str
    exact_decks: int
    weighted_decks: float
    published_list_share: float
    classified_exact_decks: int
    classified_weighted_decks: float
    classified_share: float
    denominator: str = "published-list"
    coverage_verified: bool = False


@dataclass(frozen=True)
class ShareMovement:
    """Latest normalized share minus the equally long preceding period."""

    archetype: str
    latest_share: float
    previous_share: float
    delta: float


@dataclass
class RecentField:
    """Deterministic, date-bounded current field observation."""

    since: str
    until: str
    half_life_days: float
    provenance: str | None
    shares: dict[str, float]
    exact_counts: dict[str, int]
    weighted_counts: dict[str, float]
    effective_counts: dict[str, float]
    exact_observed_decks: int
    exact_classified_decks: int
    exact_unlabeled_decks: int
    weighted_observed_decks: float
    weighted_classified_decks: float
    weighted_unlabeled_decks: float
    effective_sample_size: float
    source_breakdown: dict[str, SourceBreakdown]
    camp_fractions: dict[str, dict[str, float]]
    movement: dict[str, ShareMovement]
    previous_since: str
    previous_until: str
    source_denominator: str = "published-list"
    coverage_verified: bool = False
    coverage_note: str = (
        "Source composition uses observed published deck lists as its denominator; "
        "completeness of each source is not verified."
    )

    def as_dict(self) -> dict[str, Any]:
        """Serialize the complete result, including nested records."""

        return asdict(self)


@dataclass(frozen=True)
class _DeckObservation:
    event_date: date
    source: str
    archetype: str | None
    variant: str | None


def _weight(event_date: date, anchor: date, half_life_days: float) -> float:
    age = (anchor - event_date).days
    if age < 0:
        raise ValueError("cannot weight an observation after the evaluation cutoff")
    return 1.0 if math.isinf(half_life_days) else math.pow(2.0, -age / half_life_days)


def _ordered_float_map(values: Mapping[str, float]) -> dict[str, float]:
    return {
        key: float(values[key])
        for key in sorted(values, key=lambda item: (-values[item], item))
        if values[key] > 0
    }


def _ordered_int_map(values: Mapping[str, int]) -> dict[str, int]:
    return {
        key: int(values[key])
        for key in sorted(values, key=lambda item: (-values[item], item))
        if values[key] > 0
    }


def _normalized(values: Mapping[str, float]) -> dict[str, float]:
    total = sum(values.values())
    return _ordered_float_map({key: value / total for key, value in values.items()}) if total else {}


def _effective_counts(
    weighted: Mapping[str, float], *, total: float, ess: float,
) -> dict[str, float]:
    if total <= 0 or ess <= 0:
        return {}
    scale = ess / total
    return _ordered_float_map({key: value * scale for key, value in weighted.items()})


def _query_observations(
    con: duckdb.DuckDBPyConnection,
    *,
    start: date,
    end: date,
    provenance: str | None,
) -> list[_DeckObservation]:
    predicates = [
        "t.date IS NOT NULL",
        "substr(t.date, 1, 10) >= ?",
        "substr(t.date, 1, 10) < ?",
    ]
    params: list[object] = [start.isoformat(), end.isoformat()]
    if provenance is not None:
        predicates.append("t.provenance = ?")
        params.append(provenance)
    rows = con.execute(
        f"""
        SELECT substr(t.date, 1, 10), t.source, d.archetype, d.variant
        FROM decks d
        JOIN tournaments t ON t.id = d.tournament_id
        WHERE {' AND '.join(predicates)}
        ORDER BY substr(t.date, 1, 10), t.id, d.deck_idx
        """,
        params,
    ).fetchall()
    return [
        _DeckObservation(
            event_date=_date_only(event_text, name="tournaments.date"),
            source=(str(source).strip() if source is not None else "") or _UNKNOWN_SOURCE,
            archetype=(str(archetype).strip() if archetype is not None else "") or None,
            variant=(str(variant).strip() if variant is not None else "") or None,
        )
        for event_text, source, archetype, variant in rows
    ]


def build_recent_field(
    con: duckdb.DuckDBPyConnection,
    *,
    since: str,
    until: str,
    half_life_days: float = 28,
    provenance: str | None = None,
) -> RecentField:
    """Build a recency-weighted field for ``[since, until)``.

    Event ``D`` receives ``2 ** (-(until_date-D).days / half_life_days)``.
    The previous comparison is the equal-length ``[since-period, since)``
    window, weighted relative to ``since`` so movement reflects composition
    rather than the mechanical aging of the same event.  Shares include
    ``Unknown`` and ``Conflict`` labels; null/blank labels remain in explicit
    unlabeled coverage counts for host-side recommendation filtering.
    """

    since_date = _date_only(since, name="since")
    until_date = _date_only(until, name="until")
    if until_date <= since_date:
        raise ValueError("until must be after since")
    try:
        half_life = float(half_life_days)
    except (TypeError, ValueError) as exc:
        raise ValueError("half_life_days must be positive or infinity") from exc
    if half_life <= 0 or math.isnan(half_life):
        raise ValueError("half_life_days must be positive or infinity")

    period_days = (until_date - since_date).days
    previous_since = since_date - timedelta(days=period_days)
    observations = _query_observations(
        con, start=previous_since, end=until_date, provenance=provenance,
    )
    latest = [row for row in observations if since_date <= row.event_date < until_date]
    previous = [row for row in observations if previous_since <= row.event_date < since_date]

    exact: dict[str, int] = {}
    weighted: dict[str, float] = {}
    sources: dict[str, list[tuple[_DeckObservation, float]]] = {}
    camps: dict[str, dict[str, float]] = {}
    weighted_observed = 0.0
    weighted_unlabeled = 0.0
    classified_weight_square_sum = 0.0

    for row in latest:
        weight = _weight(row.event_date, until_date, half_life)
        weighted_observed += weight
        sources.setdefault(row.source, []).append((row, weight))
        if row.archetype is None:
            weighted_unlabeled += weight
            continue
        exact[row.archetype] = exact.get(row.archetype, 0) + 1
        weighted[row.archetype] = weighted.get(row.archetype, 0.0) + weight
        classified_weight_square_sum += weight * weight
        camp = row.variant or _UNLABELED_CAMP
        parent_camps = camps.setdefault(row.archetype, {})
        parent_camps[camp] = parent_camps.get(camp, 0.0) + weight

    weighted_classified = sum(weighted.values())
    ess = (
        weighted_classified * weighted_classified / classified_weight_square_sum
        if classified_weight_square_sum else 0.0
    )
    source_breakdown: dict[str, SourceBreakdown] = {}
    for source in sorted(sources):
        source_rows = sources[source]
        source_weight = sum(weight for _row, weight in source_rows)
        classified_rows = [(row, weight) for row, weight in source_rows if row.archetype is not None]
        classified_weight = sum(weight for _row, weight in classified_rows)
        source_breakdown[source] = SourceBreakdown(
            source=source,
            exact_decks=len(source_rows),
            weighted_decks=source_weight,
            published_list_share=source_weight / weighted_observed if weighted_observed else 0.0,
            classified_exact_decks=len(classified_rows),
            classified_weighted_decks=classified_weight,
            classified_share=classified_weight / weighted_classified if weighted_classified else 0.0,
        )

    camp_fractions = {
        parent: _normalized(camps[parent])
        for parent in sorted(camps, key=lambda key: (-sum(camps[key].values()), key))
    }
    previous_weighted: dict[str, float] = {}
    for row in previous:
        if row.archetype is not None:
            weight = _weight(row.event_date, since_date, half_life)
            previous_weighted[row.archetype] = previous_weighted.get(row.archetype, 0.0) + weight
    previous_shares = _normalized(previous_weighted)
    shares = _normalized(weighted)
    labels = set(shares) | set(previous_shares)
    movement = {
        label: ShareMovement(
            archetype=label,
            latest_share=shares.get(label, 0.0),
            previous_share=previous_shares.get(label, 0.0),
            delta=shares.get(label, 0.0) - previous_shares.get(label, 0.0),
        )
        for label in sorted(labels)
    }

    return RecentField(
        since=since_date.isoformat(),
        until=until_date.isoformat(),
        half_life_days=half_life,
        provenance=provenance,
        shares=shares,
        exact_counts=_ordered_int_map(exact),
        weighted_counts=_ordered_float_map(weighted),
        effective_counts=_effective_counts(weighted, total=weighted_classified, ess=ess),
        exact_observed_decks=len(latest),
        exact_classified_decks=sum(exact.values()),
        exact_unlabeled_decks=len(latest) - sum(exact.values()),
        weighted_observed_decks=weighted_observed,
        weighted_classified_decks=weighted_classified,
        weighted_unlabeled_decks=weighted_unlabeled,
        effective_sample_size=ess,
        source_breakdown=source_breakdown,
        camp_fractions=camp_fractions,
        movement=movement,
        previous_since=previous_since.isoformat(),
        previous_until=since_date.isoformat(),
    )


__all__ = [
    "RecentField",
    "ShareMovement",
    "SourceBreakdown",
    "build_recent_field",
]

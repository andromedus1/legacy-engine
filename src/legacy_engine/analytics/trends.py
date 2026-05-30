"""Meta-share trend series across ban-list regimes (version-stamped).

Partitions the corpus into windows bounded by ``BAN_EVENTS`` ban dates; calls
``compute_metashare`` once per non-empty regime with the regime's date window;
stamps each result with corpus-window stats and caps thin-window confidence at
``evolving``.  Owns *time/regime partitioning and version-stamping* — not share
math (that stays in ``metashare``).

Does **not** compute matchup trends (per-regime match sample too sparse for MVP).
``wrw`` trends are guarded: windowing match-results coherently is out of scope.
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from datetime import date

import duckdb

from legacy_engine.analytics.metashare import MetaShareEntry, compute_metashare
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample
from legacy_engine.ingestion.banlist import BAN_EVENTS

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unit 1 — Regime partitioning
# ---------------------------------------------------------------------------

Definition = str  # "raw" | "topcut"  (wrw deferred for trends)

_THIN_MIN_EVENTS = 4
_THIN_MIN_SPAN_DAYS = 14


@dataclass(frozen=True)
class RegimeWindow:
    """One ban-list regime — a half-open [since, until) date window opened by a B&R action.

    ``since``/``until`` are ``None`` only for the open-ended baseline / current bookends.
    ``opening_events`` is the tuple of cards banned on ``since`` (empty for the baseline regime).
    The ``event_count``/``span_days``/``thin`` fields are populated by ``compute_trends`` once the
    corpus is queried for this window (they are 0/False on a bare partition from ``regime_windows``).
    """

    label: str
    since: date | None
    until: date | None
    opening_events: tuple[str, ...]
    event_count: int = 0
    span_days: int = 0
    thin: bool = False


def regime_windows() -> list[RegimeWindow]:
    """Partition time into ban-list regimes from ``BAN_EVENTS`` (the SSOT for dated B&R actions).

    Each distinct ban date opens a regime; windows are half-open ``[date_i, date_{i+1})`` so a
    tournament dated exactly on a ban date belongs to the NEW regime. A ``(None, first_date)``
    baseline regime and a ``(last_date, None)`` current regime bookend the series.
    """
    # Group BAN_EVENTS by date → ordered dict of date → list[card]
    cards_by_date: dict[date, list[str]] = {}
    for event_date, card, _reason in BAN_EVENTS:
        cards_by_date.setdefault(event_date, []).append(card)

    dates = sorted(cards_by_date)

    windows: list[RegimeWindow] = []

    # Baseline regime: (None, dates[0])
    windows.append(
        RegimeWindow(
            label=f"baseline (pre-{dates[0]})",
            since=None,
            until=dates[0],
            opening_events=(),
        )
    )

    # Interior + current regimes
    for i, d in enumerate(dates):
        cards_tuple = tuple(cards_by_date[d])
        cards_str = ", ".join(cards_tuple)
        is_last = i == len(dates) - 1
        since = d
        until = dates[i + 1] if not is_last else None
        label = f"after {cards_str} ({d})"
        if is_last:
            label += " — current"
        windows.append(
            RegimeWindow(
                label=label,
                since=since,
                until=until,
                opening_events=cards_tuple,
            )
        )

    return windows


# ---------------------------------------------------------------------------
# Unit 3 — Trend record types + compute_trends
# ---------------------------------------------------------------------------


@dataclass
class TrendCell:
    """One archetype's share within one regime window."""

    archetype: str
    share: float
    n: int
    tier: ConfidenceLevel  # capped at "evolving" when its regime is thin


@dataclass
class TrendSeries:
    """Version-stamped meta-share trajectory across ban-list regimes.

    ``definition`` and ``provenance`` are ALWAYS labeled (PRINCIPLES #6).
    ``regimes`` contains only non-empty windows (chronological order).
    ``cells`` maps (regime.label, archetype) → TrendCell.
    ``archetypes`` is sorted by most-recent-regime share descending.
    """

    definition: Definition  # "raw" | "topcut" — ALWAYS labeled
    provenance: str | None  # basis — ALWAYS labeled
    regimes: list[RegimeWindow]  # chronological, only regimes with >=1 in-window event
    cells: dict[tuple[str, str], TrendCell]  # (regime.label, archetype) -> cell
    archetypes: list[str]  # union across regimes, sorted by most-recent-regime share desc

    def trajectory(self, archetype: str) -> list[TrendCell | None]:
        """Per-regime cells for one archetype (None where it's absent that regime)."""
        return [self.cells.get((r.label, archetype)) for r in self.regimes]


def _window_event_stats(
    con: duckdb.DuckDBPyConnection,
    *,
    since: date | None,
    until: date | None,
    provenance: str | None,
) -> tuple[int, int]:
    """Return (event_count, span_days) for tournaments in [since, until) on this provenance basis.

    ``span_days`` is the calendar distance between earliest and latest in-window event date
    (0 when event_count <= 1).
    """
    since_str = since.isoformat() if since else None
    until_str = until.isoformat() if until else None
    row = con.execute(
        """
        SELECT count(*), min(date), max(date)
        FROM tournaments
        WHERE (? IS NULL OR date >= ?)
          AND (? IS NULL OR date < ?)
          AND (? IS NULL OR provenance = ?)
        """,
        [since_str, since_str, until_str, until_str, provenance, provenance],
    ).fetchone()
    if not row or row[0] == 0:
        return 0, 0
    event_count = int(row[0])
    min_date_str, max_date_str = row[1], row[2]
    if event_count <= 1 or min_date_str is None or max_date_str is None:
        return event_count, 0
    span_days = (date.fromisoformat(max_date_str) - date.fromisoformat(min_date_str)).days
    return event_count, span_days


def _cap_thin(tier: ConfidenceLevel, *, thin: bool) -> ConfidenceLevel:
    """A thin window may never claim 'established' — cap it at 'evolving'."""
    return "evolving" if (thin and tier == "established") else tier


def compute_trends(
    con: duckdb.DuckDBPyConnection,
    *,
    definition: Definition = "raw",
    provenance: str | None = None,
    min_share: float = 0.02,
    cut_size: int = 8,
    min_events: int = _THIN_MIN_EVENTS,
    min_span_days: int = _THIN_MIN_SPAN_DAYS,
) -> TrendSeries:
    """Version-stamped meta-share trajectory across ban-list regimes.

    For each non-empty regime, calls ``compute_metashare`` with the regime's date window
    (``group_other=False`` so archetypes stay comparable across regimes), stamps the result with
    corpus-window stats, and caps thin-window confidence at 'evolving'. ``definition`` must be
    'raw' or 'topcut' — 'wrw' raises ``ValueError`` (deferred; per-regime match sample too sparse
    and windowing match-results coherently is out of MVP scope).
    """
    if definition not in {"raw", "topcut"}:
        raise ValueError(
            f"compute_trends: definition must be 'raw' or 'topcut', got {definition!r}. "
            "'wrw' trends are deferred — per-regime match-results sample is too sparse and "
            "windowing match_results coherently is out of scope."
        )

    windows = regime_windows()
    populated_regimes: list[RegimeWindow] = []
    cells: dict[tuple[str, str], TrendCell] = {}

    for window in windows:
        event_count, span_days = _window_event_stats(
            con, since=window.since, until=window.until, provenance=provenance
        )
        if event_count == 0:
            log.debug(
                "compute_trends: skipping empty regime %r (no in-window events)", window.label
            )
            continue

        thin = event_count < min_events or span_days < min_span_days
        populated_window = dataclasses.replace(
            window, event_count=event_count, span_days=span_days, thin=thin
        )

        since_str = window.since.isoformat() if window.since else None
        until_str = window.until.isoformat() if window.until else None

        report = compute_metashare(
            con,
            definition=definition,
            provenance=provenance,
            min_share=min_share,
            cut_size=cut_size,
            group_other=False,
            since=since_str,
            until=until_str,
        )

        for entry in report.entries:
            capped_tier = _cap_thin(entry.tier, thin=thin)
            cells[(populated_window.label, entry.archetype)] = TrendCell(
                archetype=entry.archetype,
                share=entry.share,
                n=entry.n,
                tier=capped_tier,
            )

        populated_regimes.append(populated_window)

    # Build archetype list: union across regimes, sorted by most-recent-regime share desc
    if populated_regimes:
        last_regime = populated_regimes[-1]
        last_cells = {
            arch: cells[(last_regime.label, arch)]
            for arch in {k[1] for k in cells if k[0] == last_regime.label}
        }
        all_archetypes = {k[1] for k in cells}
        # Sort: archetypes present in last regime by share desc, then remainder alphabetically
        in_last = sorted(last_cells.keys(), key=lambda a: last_cells[a].share, reverse=True)
        not_in_last = sorted(all_archetypes - set(in_last))
        archetypes = in_last + not_in_last
    else:
        archetypes = []

    return TrendSeries(
        definition=definition,
        provenance=provenance,
        regimes=populated_regimes,
        cells=cells,
        archetypes=archetypes,
    )

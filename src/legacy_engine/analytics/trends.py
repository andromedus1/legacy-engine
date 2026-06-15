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

from legacy_engine.analytics.metashare import compute_metashare
from legacy_engine.confidence import ConfidenceLevel
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


def resolve_regime(name: str = "current") -> tuple[str | None, str | None]:
    """Map a ban-regime name to a half-open ``(since, until)`` window of ISO date strings.

    - ``"current"`` (default) → the latest (open-ended) regime: ``(last_since, None)``.
    - ``"all"`` / ``"all-time"`` → ``(None, None)`` (full corpus).
    - any other string → the regime whose ``label`` contains it (case-insensitive substring,
      e.g. ``"Undercity"`` → the post-Undercity-Informer regime). Ambiguous/unknown → ``ValueError``.

    Returns ISO date strings (``None`` for an open bound), ready to pass into the windowed
    ``compute_match_results`` / ``build_matrix`` / ``build_global_field`` / ``compute_archetype_gaps``.
    """
    windows = regime_windows()
    key = name.strip().lower()

    if key == "current":
        w = windows[-1]
    elif key in ("all", "all-time", "alltime"):
        return None, None
    else:
        matches = [w for w in windows if key in w.label.lower()]
        if not matches:
            raise ValueError(
                f"resolve_regime: no ban regime matches {name!r}; "
                f"known regimes: {[w.label for w in windows]}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"resolve_regime: {name!r} is ambiguous across regimes: {[w.label for w in matches]}"
            )
        w = matches[0]

    since = w.since.isoformat() if w.since else None
    until = w.until.isoformat() if w.until else None
    return since, until


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
    # tournaments.date is ISO, but real-corpus values mix plain dates ("2025-11-09") with full
    # timestamps ("2025-11-09T14:00:00+00:00", from Melee). Take the date portion for the span.
    span_days = (
        date.fromisoformat(max_date_str[:10]) - date.fromisoformat(min_date_str[:10])
    ).days
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

        # ── Finding #8: skip topcut regimes with no top-cut decks ───────────
        # _window_event_stats counts all tournaments in the window, but a
        # regime can have in-window events with zero standings rows (e.g. Leagues
        # or paper events without standings data).  Using the report's total_decks
        # (top-cut decks) as the skip guard prevents a zero-denominator regime
        # from appearing in the topcut series.
        if definition == "topcut" and report.total_decks == 0:
            log.debug(
                "compute_trends: skipping topcut regime %r (in-window events but total_decks=0)",
                window.label,
            )
            continue

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


# ---------------------------------------------------------------------------
# Unit 4 — Biggest-movers digest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BiggestMover:
    """One archetype's share change between two adjacent regimes.

    ``delta`` is positive when the archetype grew, negative when it shrank.
    ``prev_regime`` and ``curr_regime`` are the regime labels used for the
    diff.  ``prev_share`` is ``None`` when the archetype was absent in the
    previous regime (new entrant); ``curr_share`` is ``None`` when it exited.
    """

    archetype: str
    delta: float          # curr_share - prev_share (treating absent as 0)
    prev_share: float | None
    curr_share: float | None
    prev_regime: str
    curr_regime: str


def biggest_movers(
    series: TrendSeries,
    *,
    n: int = 5,
    between: tuple[str, str] | None = None,
) -> list[BiggestMover]:
    """Return the top-N biggest share movers between adjacent regimes.

    By default compares the two most recent regimes (``series.regimes[-2]``
    and ``series.regimes[-1]``).  Pass ``between=(prev_label, curr_label)``
    to compare any two regimes by label.

    Returns an empty list if the series has fewer than two regimes or if the
    specified labels are not found.

    Absent archetypes are treated as 0 share (new entrant or exit), so the
    digest captures both arrivals and departures.  The result is sorted by
    ``|delta|`` descending (archetype name ascending as a deterministic
    tiebreak), then top-N sliced.

    Pure function over ``TrendSeries`` — no DB access.
    """
    if len(series.regimes) < 2:
        return []

    if between is not None:
        prev_label, curr_label = between
        prev_regimes = [r for r in series.regimes if r.label == prev_label]
        curr_regimes = [r for r in series.regimes if r.label == curr_label]
        if not prev_regimes or not curr_regimes:
            return []
        prev_regime = prev_regimes[0]
        curr_regime = curr_regimes[0]
    else:
        prev_regime = series.regimes[-2]
        curr_regime = series.regimes[-1]

    # Collect archetypes present in either regime.
    prev_archs = {k[1] for k in series.cells if k[0] == prev_regime.label}
    curr_archs = {k[1] for k in series.cells if k[0] == curr_regime.label}
    all_archs = prev_archs | curr_archs

    movers: list[BiggestMover] = []
    for arch in all_archs:
        prev_cell = series.cells.get((prev_regime.label, arch))
        curr_cell = series.cells.get((curr_regime.label, arch))
        prev_share = prev_cell.share if prev_cell is not None else None
        curr_share = curr_cell.share if curr_cell is not None else None
        delta = (curr_share or 0.0) - (prev_share or 0.0)
        movers.append(
            BiggestMover(
                archetype=arch,
                delta=delta,
                prev_share=prev_share,
                curr_share=curr_share,
                prev_regime=prev_regime.label,
                curr_regime=curr_regime.label,
            )
        )

    # |delta| descending, archetype name ascending as a deterministic tiebreak — `all_archs`
    # is a set, so equal-|delta| ties would otherwise select nondeterministically.
    movers.sort(key=lambda m: (-abs(m.delta), m.archetype))
    return movers[:n]

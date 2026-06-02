"""Viz prep models — pure dataclasses + prep helpers for the four chart surfaces.

Lifted verbatim from ``analytics/charts.py`` (they were already matplotlib-free).
These are view-models: each bakes in all honesty logic (masking, fringe, thin-regime
banding, caveat strings) so the downstream Vega-Lite spec builders in ``viz/specs.py``
are pure dict→dict transformers with no analytics decisions inside.

Imports: MatchupMatrix from analytics.matchup; MetaShareReport/TrendSeries from
analytics.metashare / analytics.trends (presentation→data edge; clean direction).
"""

from __future__ import annotations

from dataclasses import dataclass

from legacy_engine.analytics.matchup import MatchupMatrix
from legacy_engine.analytics.metashare import MetaShareReport, _is_never_other
from legacy_engine.analytics.trends import TrendSeries
from legacy_engine.confidence import ConfidenceLevel

# ---------------------------------------------------------------------------
# Tier-list share thresholds (presentation bins over raw share — no new stat)
# ---------------------------------------------------------------------------

TIER_S_MIN: float = 0.10
TIER_A_MIN: float = 0.05
TIER_B_MIN: float = 0.02

# ---------------------------------------------------------------------------
# Visual treatment constants (retained for downstream consumers)
# ---------------------------------------------------------------------------

_SPECULATIVE_ALPHA: float = 0.35
_MASKED_COLOR: str = "#cccccc"  # neutral gray for masked/n=0 cells
_THIN_BAND_ALPHA: float = 0.12  # shading alpha for thin-regime background bands


# ---------------------------------------------------------------------------
# HeatmapModel + _heatmap_model
# ---------------------------------------------------------------------------


@dataclass
class HeatmapModel:
    """Render-model for the matchup heatmap — all honesty logic resolved here (testable).

    ``values[i][j]`` is ``cell.p_shrunk`` when the cell is displayed, or ``None``
    when masked (``cell.display is False`` or ``n == 0``).  ``masked[i][j]`` mirrors
    that None condition.  ``mirror[i][i]`` is ``True`` for diagonal self-matchups.
    ``annotations[i][j]`` carries a human-readable per-cell label.  ``caveat`` is
    taken verbatim from ``matrix.caveat``.
    """

    archetypes: list[str]
    values: list[list[float | None]]     # p_shrunk or None (masked)
    masked: list[list[bool]]             # True where display is False or n==0
    mirror: list[list[bool]]             # True for (a, a) diagonal cells
    annotations: list[list[str]]         # per-cell label text
    caveat: str                          # matrix.caveat, baked into figure subtitle
    title: str


def _heatmap_model(matrix: MatchupMatrix) -> HeatmapModel:
    """Build the heatmap render-model from a MatchupMatrix — masks low-n/unobserved cells.

    A cell is masked (value=None, drawn gray) when ``not cell.display`` (n<30 gate)
    or ``n==0``.  Mirror cells are flagged.  Displayed cells use ``p_shrunk`` for color
    and annotate with raw% + n.  The caveat is taken verbatim from ``matrix.caveat``.
    Reuses the producer's already-computed ``display`` flag — never re-derives the gate.
    """
    archetypes = matrix.archetypes
    n = len(archetypes)
    idx = {a: i for i, a in enumerate(archetypes)}

    values: list[list[float | None]] = [[None] * n for _ in range(n)]
    masked: list[list[bool]] = [[True] * n for _ in range(n)]
    mirror: list[list[bool]] = [[False] * n for _ in range(n)]
    annotations: list[list[str]] = [[""] * n for _ in range(n)]

    basis = matrix.provenance if matrix.provenance else "all"
    title = f"Matchup Matrix  [basis={basis}]"

    for (arch_a, arch_b), cell in matrix.cells.items():
        if arch_a not in idx or arch_b not in idx:
            continue
        i, j = idx[arch_a], idx[arch_b]

        if cell.is_mirror:
            mirror[i][j] = True
            masked[i][j] = True
            values[i][j] = None
            annotations[i][j] = "mirror"
            continue

        is_masked = (not cell.display) or (cell.n == 0)
        masked[i][j] = is_masked

        if is_masked:
            values[i][j] = None
            if cell.n == 0:
                annotations[i][j] = "—"
            else:
                annotations[i][j] = f"n={cell.n}"
        else:
            values[i][j] = cell.p_shrunk
            pct = f"{cell.p_shrunk:.0%}" if cell.p_shrunk is not None else "?"
            annotations[i][j] = f"{pct}\n(n={cell.n})"

    return HeatmapModel(
        archetypes=archetypes,
        values=values,
        masked=masked,
        mirror=mirror,
        annotations=annotations,
        caveat=matrix.caveat,
        title=title,
    )


# ---------------------------------------------------------------------------
# BarModel + _metashare_model
# ---------------------------------------------------------------------------


@dataclass
class BarModel:
    """Render-model for the meta-share horizontal bar chart.

    ``muted[i]`` is True for speculative-tier entries (lower alpha).
    ``fringe[i]`` is True for fringe/Other entries (distinctive hatch).
    ``subtitle`` is baked from the report labels so the PNG is self-describing.
    """

    labels: list[str]
    shares: list[float]
    muted: list[bool]        # speculative-tier → muted alpha
    fringe: list[bool]       # fringe / "Other" → distinct hatch
    tiers: list[ConfidenceLevel]
    subtitle: str            # "definition=RAW  basis=online  total_decks=420"
    title: str


def _metashare_model(report: MetaShareReport) -> BarModel:
    """Bar-chart render-model from a MetaShareReport — speculative bars muted, fringe/Other hatched.

    ``muted[i] = entry.tier == "speculative"``
    ``fringe[i] = entry.fringe or entry.archetype == "Other"``
    Subtitle is baked from report.definition / report.provenance / report.total_decks.
    Recomputes nothing — consumes the producer's already-resolved tier/fringe flags.
    """
    basis = report.provenance if report.provenance else "all"
    subtitle = (
        f"definition={report.definition.upper()}  "
        f"basis={basis}  "
        f"total_decks={report.total_decks}"
    )
    title = f"Meta Share [{report.definition.upper()}]  basis={basis}"

    labels: list[str] = []
    shares: list[float] = []
    muted: list[bool] = []
    fringe_flags: list[bool] = []
    tiers: list[ConfidenceLevel] = []

    for entry in report.entries:
        labels.append(entry.archetype)
        shares.append(entry.share)
        muted.append(entry.tier == "speculative")
        fringe_flags.append(entry.fringe or entry.archetype == "Other")
        tiers.append(entry.tier)

    return BarModel(
        labels=labels,
        shares=shares,
        muted=muted,
        fringe=fringe_flags,
        tiers=tiers,
        subtitle=subtitle,
        title=title,
    )


# ---------------------------------------------------------------------------
# TierModel + _tier_model
# ---------------------------------------------------------------------------


@dataclass
class TierModel:
    """Render-model for the tier list (S/A/B buckets over raw shares).

    ``buckets["S"]`` contains archetypes with share >= TIER_S_MIN, etc.
    Sub-floor archetypes (share < TIER_B_MIN) are excluded from buckets
    (and so are "Other" rows and _is_never_other labels).
    Each entry is a tuple of (archetype, share, confidence_tier).
    """

    buckets: dict[str, list[tuple[str, float, ConfidenceLevel]]]
    subtitle: str
    title: str


def _tier_model(
    report: MetaShareReport,
    *,
    s_min: float = TIER_S_MIN,
    a_min: float = TIER_A_MIN,
    b_min: float = TIER_B_MIN,
) -> TierModel:
    """Bucket a MetaShareReport's entries into S/A/B tiers by share.

    Pure binning over ``entry.share`` — no new statistic.  Excludes the "Other"
    row and ``_is_never_other`` labels (Unknown, Conflict).  Sub-floor entries
    (share < ``b_min``) are excluded.  Each entry retains its confidence ``tier``
    for honest display.  Thresholds are configurable (default: S≥10%, A≥5%, B≥2%).
    """
    basis = report.provenance if report.provenance else "all"
    subtitle = (
        f"definition={report.definition.upper()}  "
        f"basis={basis}  "
        f"total_decks={report.total_decks}  "
        f"S≥{s_min:.0%} A≥{a_min:.0%} B≥{b_min:.0%}"
    )
    title = f"Tier List [{report.definition.upper()}]  basis={basis}"

    buckets: dict[str, list[tuple[str, float, ConfidenceLevel]]] = {
        "S": [],
        "A": [],
        "B": [],
    }

    for entry in report.entries:
        # Exclude Other and never-other labels (they aren't real archetypes to tier)
        if entry.archetype == "Other" or _is_never_other(entry.archetype):
            continue
        share = entry.share
        if share >= s_min:
            buckets["S"].append((entry.archetype, share, entry.tier))
        elif share >= a_min:
            buckets["A"].append((entry.archetype, share, entry.tier))
        elif share >= b_min:
            buckets["B"].append((entry.archetype, share, entry.tier))
        # else: sub-floor → excluded (untiered)

    return TierModel(buckets=buckets, subtitle=subtitle, title=title)


# ---------------------------------------------------------------------------
# TrendModel + _trends_model
# ---------------------------------------------------------------------------


@dataclass
class TrendModel:
    """Render-model for the meta-share trend line chart.

    ``series[archetype]`` is a list with one entry per regime (None where the
    archetype is absent that regime — creates a gap in the plotted line).
    ``thin_regimes[k]`` mirrors ``regimes[k].thin``.
    """

    regime_labels: list[str]
    archetypes: list[str]
    series: dict[str, list[float | None]]   # archetype -> share per regime (None = absent)
    thin_regimes: list[bool]                # per-regime thin flag
    subtitle: str
    title: str


def _trends_model(series: TrendSeries) -> TrendModel:
    """Line-chart render-model from a TrendSeries.

    One line per archetype across regimes; ``None`` cells create gaps (do not plot 0).
    ``thin_regimes[k] = series.regimes[k].thin``.
    Reuses ``series.trajectory(archetype)`` — recomputes nothing.
    """
    basis = series.provenance if series.provenance else "all"
    subtitle = f"definition={series.definition.upper()}  basis={basis}"
    title = f"Meta Trends [{series.definition.upper()}]  basis={basis}"

    regime_labels = [r.label for r in series.regimes]
    thin_regimes = [r.thin for r in series.regimes]

    archetype_series: dict[str, list[float | None]] = {}
    for archetype in series.archetypes:
        traj = series.trajectory(archetype)
        archetype_series[archetype] = [
            cell.share if cell is not None else None
            for cell in traj
        ]

    return TrendModel(
        regime_labels=regime_labels,
        archetypes=series.archetypes,
        series=archetype_series,
        thin_regimes=thin_regimes,
        subtitle=subtitle,
        title=title,
    )

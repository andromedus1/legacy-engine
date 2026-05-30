"""Analytics charts — prep/render pairs for heatmap, meta-share, tier list, and trends.

Each chart is a pure prep helper (returns a testable render-model with the
confidence-honesty flags resolved) plus a thin matplotlib renderer (smoke-tested
only: file exists + non-empty).  All honesty logic (low-n masking, fringe
distinction, thin-regime marking, caveat baking) lives in the prep helpers so
tests can assert on it — NOT buried in pyplot calls.

Backend is forced to ``Agg`` at import (before pyplot) so charts work headless
in CI with no display server.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless — must be before pyplot import
import matplotlib.pyplot as plt  # noqa: E402

from legacy_engine.analytics.matchup import MatchupMatrix
from legacy_engine.analytics.metashare import MetaShareReport, _is_never_other
from legacy_engine.analytics.trends import TrendSeries
from legacy_engine.confidence import ConfidenceLevel

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier-list share thresholds (presentation bins over raw share — no new stat)
# ---------------------------------------------------------------------------

TIER_S_MIN: float = 0.10
TIER_A_MIN: float = 0.05
TIER_B_MIN: float = 0.02

# ---------------------------------------------------------------------------
# Visual treatment constants
# ---------------------------------------------------------------------------

_SPECULATIVE_ALPHA: float = 0.35
_SUPPRESSED_HATCH: str = "////"
_MASKED_COLOR: str = "#cccccc"  # neutral gray for masked/n=0 cells
_THIN_BAND_ALPHA: float = 0.12   # shading alpha for thin-regime background bands

# ---------------------------------------------------------------------------
# Unit 1 — Matchup heatmap: HeatmapModel + _heatmap_model + render_matchup_heatmap
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


def render_matchup_heatmap(matrix: MatchupMatrix, out_path: Path | str) -> Path:
    """Render the matchup heatmap to a PNG at ``out_path``; returns the path written.

    Color-scales displayed cells by ``p_shrunk`` (diverging RdYlGn around 0.5);
    masked cells are drawn in neutral gray; mirror cells annotated "mirror".
    Figure carries the title + provenance + ``matrix.caveat`` subtitle.
    Empty matrix writes a labeled placeholder PNG rather than raising.
    Calls ``plt.close(fig)`` after save to prevent figure leaks.
    """
    import numpy as np

    out_path = Path(out_path)
    model = _heatmap_model(matrix)

    if not model.archetypes:
        fig, ax = plt.subplots(figsize=(4, 2))
        ax.text(0.5, 0.5, "No data — matrix empty", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        fig.suptitle("Matchup Matrix (no data)", fontsize=11)
        fig.savefig(out_path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        log.debug("render_matchup_heatmap: placeholder written to %s", out_path)
        return out_path

    n = len(model.archetypes)

    # Build float array for colormapping (NaN where masked/mirror)
    heat = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            if not model.masked[i][j] and model.values[i][j] is not None:
                heat[i][j] = model.values[i][j]

    fig_size = max(6, n * 0.9)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))

    # Draw masked / mirror cells as flat gray patches first
    for i in range(n):
        for j in range(n):
            if model.masked[i][j] or np.isnan(heat[i][j]):
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                           color=_MASKED_COLOR, zorder=0))

    # Main colormap image (NaNs transparent via masked array)
    masked_heat = np.ma.masked_invalid(heat)
    im = ax.imshow(
        masked_heat,
        cmap="RdYlGn",
        vmin=0.0,
        vmax=1.0,
        aspect="auto",
        interpolation="nearest",
        origin="upper",
    )

    # Annotations
    for i in range(n):
        for j in range(n):
            txt = model.annotations[i][j]
            if txt:
                ax.text(j, i, txt, ha="center", va="center", fontsize=7, wrap=True)

    # Grid lines
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(model.archetypes, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(model.archetypes, fontsize=8)
    ax.set_xlabel("Opponent (archetype_b)", fontsize=9)
    ax.set_ylabel("Deck (archetype_a)", fontsize=9)

    plt.colorbar(im, ax=ax, label="p_shrunk (win rate)", fraction=0.046, pad=0.04)

    basis = matrix.provenance if matrix.provenance else "all"
    ax.set_title(f"Matchup Matrix  [basis={basis}]\n{model.caveat[:80]}…",
                 fontsize=9, wrap=True)

    fig.tight_layout()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    log.debug("render_matchup_heatmap: wrote %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Unit 2 — Meta-share bar chart: BarModel + _metashare_model + render_metashare
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


def render_metashare(report: MetaShareReport, out_path: Path | str) -> Path:
    """Horizontal bar chart of meta shares.

    Muted alpha for speculative entries, hatch for fringe/Other entries.
    Labeled subtitle baked into the figure so the PNG is self-describing.
    Empty report writes a labeled placeholder PNG rather than raising.
    Calls ``plt.close(fig)`` after save.
    """
    out_path = Path(out_path)
    model = _metashare_model(report)

    if not model.labels:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, "No data — empty report", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        fig.suptitle(model.title, fontsize=11)
        fig.text(0.5, 0.02, model.subtitle, ha="center", fontsize=8, style="italic")
        fig.savefig(out_path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        log.debug("render_metashare: placeholder written to %s", out_path)
        return out_path

    n = len(model.labels)
    fig_h = max(3, n * 0.45)
    fig, ax = plt.subplots(figsize=(9, fig_h))

    colors = ["#4878d0"] * n
    hatches = [_SUPPRESSED_HATCH if model.fringe[i] else "" for i in range(n)]
    alphas = [_SPECULATIVE_ALPHA if model.muted[i] else 0.85 for i in range(n)]

    for i, (label, share) in enumerate(zip(model.labels, model.shares)):
        bar = ax.barh(
            i,
            share,
            color=colors[i],
            alpha=alphas[i],
            hatch=hatches[i],
            edgecolor="white",
        )
        # Annotate bar with share % + tier
        ax.text(
            share + 0.003,
            i,
            f"{share:.1%} ({model.tiers[i]})",
            va="center",
            fontsize=8,
        )

    ax.set_yticks(range(n))
    ax.set_yticklabels(model.labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Share", fontsize=9)
    ax.set_xlim(0, max(model.shares) * 1.35)
    ax.set_title(model.title, fontsize=11)
    fig.text(0.5, -0.02, model.subtitle, ha="center", fontsize=8, style="italic")

    fig.tight_layout()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    log.debug("render_metashare: wrote %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Unit 3 — Tier list: TierModel + _tier_model + render_tier_list + _print_tier_list
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


def render_tier_list(report: MetaShareReport, out_path: Path | str, **thresholds) -> Path:
    """Render the tier list as a labeled column-per-tier PNG.

    Each column (S, A, B) lists its archetypes with share% and confidence tier.
    Empty report writes a labeled placeholder PNG rather than raising.
    Calls ``plt.close(fig)`` after save.
    """
    out_path = Path(out_path)
    model = _tier_model(report, **thresholds)

    fig, axes = plt.subplots(1, 3, figsize=(12, max(4, max(
        (len(model.buckets["S"]), len(model.buckets["A"]), len(model.buckets["B"])), default=1
    ) * 0.5 + 2)))

    has_any = any(model.buckets[t] for t in ("S", "A", "B"))
    if not has_any:
        for ax in axes:
            ax.axis("off")
        axes[1].text(0.5, 0.5, "No archetypes meet the tier thresholds",
                     ha="center", va="center", transform=axes[1].transAxes, fontsize=10)
        fig.suptitle(model.title, fontsize=12)
        fig.text(0.5, 0.01, model.subtitle, ha="center", fontsize=8, style="italic")
        fig.savefig(out_path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        log.debug("render_tier_list: placeholder written to %s", out_path)
        return out_path

    bucket_colors = {"S": "#d4af37", "A": "#c0c0c0", "B": "#cd7f32"}

    for ax, tier_key in zip(axes, ("S", "A", "B")):
        entries = model.buckets[tier_key]
        ax.set_title(f"Tier {tier_key}", fontsize=13, fontweight="bold",
                     color=bucket_colors[tier_key])
        ax.axis("off")
        if not entries:
            ax.text(0.5, 0.5, "(none)", ha="center", va="center",
                    transform=ax.transAxes, fontsize=9, color="gray")
            continue
        y = 0.95
        for archetype, share, conf_tier in entries:
            ax.text(
                0.05, y,
                f"{archetype}  {share:.1%}  [{conf_tier}]",
                transform=ax.transAxes,
                fontsize=9,
                va="top",
            )
            y -= 0.08

    fig.suptitle(model.title, fontsize=12)
    fig.text(0.5, 0.01, model.subtitle, ha="center", fontsize=8, style="italic")
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    log.debug("render_tier_list: wrote %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Unit 4 — Trends chart: TrendModel + _trends_model + render_trends
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


def render_trends(series: TrendSeries, out_path: Path | str) -> Path:
    """Multi-line share-trajectory chart across ban-list regimes.

    Thin regimes are marked with a shaded vertical band and "⚠" tick label suffix.
    None entries in a trajectory create line gaps (plotted as disconnected segments).
    Empty series writes a labeled placeholder PNG rather than raising.
    Calls ``plt.close(fig)`` after save.
    """
    import numpy as np

    out_path = Path(out_path)
    model = _trends_model(series)

    if not model.regime_labels or not model.archetypes:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "No data — empty series", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        fig.suptitle(model.title, fontsize=11)
        fig.text(0.5, 0.02, model.subtitle, ha="center", fontsize=8, style="italic")
        fig.savefig(out_path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        log.debug("render_trends: placeholder written to %s", out_path)
        return out_path

    n_regimes = len(model.regime_labels)
    fig_w = max(8, n_regimes * 1.5)
    fig, ax = plt.subplots(figsize=(fig_w, 6))

    # Shade thin-regime columns
    for k, thin in enumerate(model.thin_regimes):
        if thin:
            ax.axvspan(k - 0.5, k + 0.5, color="orange", alpha=_THIN_BAND_ALPHA, zorder=0)

    x = np.arange(n_regimes)
    cmap = plt.get_cmap("tab10")
    for color_idx, archetype in enumerate(model.archetypes):
        shares = model.series[archetype]
        # Plot connected segments, skipping None gaps
        seg_x: list[float] = []
        seg_y: list[float] = []
        color = cmap(color_idx % 10)
        for xi, val in enumerate(shares):
            if val is not None:
                seg_x.append(xi)
                seg_y.append(val)
            else:
                if seg_x:
                    ax.plot(seg_x, seg_y, marker="o", markersize=4,
                            label=archetype if not seg_x or seg_x[0] == 0 else "_",
                            color=color)
                seg_x = []
                seg_y = []
        if seg_x:
            ax.plot(seg_x, seg_y, marker="o", markersize=4,
                    label=archetype,
                    color=color)

    # Build x-axis tick labels with thin-marker suffix
    tick_labels = []
    for k, lbl in enumerate(model.regime_labels):
        short = lbl[:20]
        suffix = "⚠" if model.thin_regimes[k] else ""
        tick_labels.append(f"{short}{suffix}")

    ax.set_xticks(x)
    ax.set_xticklabels(tick_labels, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("Share", fontsize=9)
    ax.set_xlabel("Ban-list Regime", fontsize=9)
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend(loc="upper right", fontsize=7, ncol=max(1, len(model.archetypes) // 8))
    ax.set_title(model.title, fontsize=11)
    fig.text(0.5, -0.02, model.subtitle, ha="center", fontsize=8, style="italic")

    fig.tight_layout()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    log.debug("render_trends: wrote %s", out_path)
    return out_path

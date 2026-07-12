"""MatchupCell — consumer-facing directed matchup estimate.

Self-describing: carries computed stats AND the display decision so downstream
consumers (charts, advisory) never re-derive the n<30 gate logic.
"""

from __future__ import annotations

from legacy_engine.confidence import ConfidenceLevel
from legacy_engine.models.base import LegacyEngineModel


class MatchupCell(LegacyEngineModel):
    """One directed matchup estimate: archetype_a vs archetype_b.

    Self-describing — carries the computed stats AND the display decision so
    consumers (charts, advisory) never re-derive the gate.

    Fields
    ------
    archetype_a, archetype_b
        The two archetypes in matchup order (a's record vs b).
    wins
        Number of decisive matches archetype_a won against archetype_b.
        For mirror cells: ``n // 2`` (cosmetic).
    n
        Total decisive a-vs-b matches (matchup-n, NOT metashare-n).
    p_raw
        Raw win-rate ``wins / n``; ``None`` when ``n == 0``.
    p_shrunk
        Beta-Binomial posterior mean — shrunk toward 0.5 with prior α=β=7.5.
        ``None`` when ``n == 0`` (degenerate cell); ``0.5`` for mirror cells.
        Always shown alongside ``p_raw`` when ``n > 0`` (never shrunk-only).
    ci_low, ci_high
        95% confidence interval (Jeffreys for n≤40; Wilson for n>40).
        ``None`` for mirror cells and n=0 cells.
    tier
        Confidence tier from ``tier_for_sample(n)``:
        ``"speculative"`` (<30), ``"evolving"`` (30–99), ``"established"`` (≥100).
    is_mirror
        ``True`` for the ``(a, a)`` diagonal — rate fixed at 0.5, no CI.
    display
        ``False`` when ``n < 30`` (speculative gate): the rate should be hidden
        and rendered as "n=X, insufficient" rather than a confident number.
    prior_mean
        The Beta prior mean ``p_shrunk`` was shrunk toward (epic-stable-era-windows-shrinkage's
        hierarchical cell prior). ``0.5`` (the flat legacy prior) with ``prior_source is None``
        for a caller that didn't supply one (additive default — ``build_cell``'s pre-hierarchy
        signature). ``None`` only on directly-constructed mirror/hand-built cells that omit it.
    prior_source
        Human-readable label for what ``prior_mean`` came from: ``"marginal"`` (the subject
        archetype's own shrunk marginal WR), ``"parent cell (leave-camp-out)"`` (a split-variant
        camp cell shrunk toward its parent archetype's LCO cell), or
        ``"pre-disturbance value (window < <date>); hierarchy: <source>"`` (the cross-era prior,
        ``build_adaptive_matrix`` only — wins over the hierarchy source when both apply). ``None``
        when the cell was built with the flat legacy prior (no hierarchy label to show) or left
        unset by a direct constructor call.
    """

    archetype_a: str
    archetype_b: str
    wins: int
    n: int  # matchup-n (decisive a-vs-b matches); NOT metashare-n
    p_raw: float | None  # wins/n; None when n==0
    p_shrunk: float | None  # Beta-Binomial posterior mean; None when n==0 (or 0.5 prior)
    ci_low: float | None
    ci_high: float | None
    tier: ConfidenceLevel  # tier_for_sample(n)
    is_mirror: bool = False  # mirror → p fixed 0.5, no CI
    display: bool = True  # False when n<30 (speculative gate): hide rate, show "n=X, insufficient"
    prior_mean: float | None = None  # what p_shrunk was shrunk toward (additive)
    prior_source: str | None = None  # "marginal" | "parent cell (leave-camp-out)" | cross-era label

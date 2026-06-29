"""Configuration / transform comparator.

Compares two *deck configurations* against a field and reports which positions better,
per-matchup contributions, and a break-even. A configuration is a list of **modes**; its
per-opponent win-rate is the ``max`` over its modes — so a plain deck is one mode, and a
**transform-alternate** (one 75 that sideboards into a second deck) is two modes, scored as
``max(mode_A, mode_B)`` per matchup (the optimistic "you always end in the better mode" ceiling).

Two clearly-separated statistical layers (per the feature's stats decision):
  1. **Bayesian-MC base layer** (no lifts) — generalizes ``positioning._sample_S`` to a per-matchup
     ``max`` over modes and two configs sharing per-draw cell draws; yields field-EV CIs and
     P(Config A beats Config B).
  2. **Point-estimate overlay** — applies sideboard-lift adjustments deterministically (lifts are
     hand-asserted or measured assumptions, so they never enter the MC — no false precision) and
     drives the break-even.

Reuses ``positioning``'s cell extraction + Beta/Dirichlet constants verbatim (SSOT) and the
matchup matrix + ``field.py`` field. Lifts may be pulled from Piece 1 (``slot_lift``).
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field

import numpy as np

from legacy_engine.advisory.positioning import (
    _BETA_JEFFREYS,
    _DEFAULT_DRAWS,
    _DIRICHLET_GAMMA,
    _NODATA_STRENGTH,
    _row_winrate_inputs,
)
from legacy_engine.confidence import ConfidenceLevel


# ---------------------------------------------------------------------------
# Config model
# ---------------------------------------------------------------------------

@dataclass
class ConfigMode:
    """One mode a configuration can present: an archetype + optional per-matchup SB lifts."""

    archetype: str
    lifts: dict[str, float] = dc_field(default_factory=dict)  # opponent -> additive WR delta (overlay only)


@dataclass
class DeckConfig:
    """A configuration = label + 1+ modes. Per-opponent WR is the max over modes."""

    label: str
    modes: list[ConfigMode]


@dataclass
class MatchupContribution:
    opponent: str
    share: float
    wr_a_base: float
    wr_b_base: float
    wr_a_adj: float
    wr_b_adj: float
    chosen_mode_a: str
    chosen_mode_b: str
    imputed_a: bool
    imputed_b: bool
    contribution_diff: float  # share * (wr_a_adj - wr_b_adj)


@dataclass
class ComparisonResult:
    a_label: str
    b_label: str
    field_source: str
    rows: list[MatchupContribution]
    ev_a_base: float
    ev_b_base: float
    ev_a_adj: float
    ev_b_adj: float
    ev_a_base_ci: tuple[float, float]
    ev_b_base_ci: tuple[float, float]
    p_a_beats_b_base: float
    n_draws: int
    breakeven_lift: float | None
    breakeven_targets: list[str]
    breakeven_feasible: bool
    coverage_a: float
    coverage_b: float
    warnings: list[str]


# ---------------------------------------------------------------------------
# Point-estimate row WR (mirrors positioning's mean-vs-known imputation, on p_shrunk)
# ---------------------------------------------------------------------------

def _row_point_wr(matrix, archetype: str, field_archetypes: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Per-opponent point win-rate for ``archetype`` over ``field_archetypes``.

    Uses the matchup cell ``p_shrunk``; mirror → 0.5; no-data → mean of known (non-mirror) cells
    (else 0.5). Returns ``(wr, imputed_mask)``.
    """
    m = len(field_archetypes)
    wr = np.full(m, 0.5, dtype=np.float64)
    imputed = np.zeros(m, dtype=bool)
    known: list[float] = []
    for i, opp in enumerate(field_archetypes):
        if opp == archetype:
            wr[i] = 0.5  # mirror
            continue
        cell = matrix.cells.get((archetype, opp))
        if cell is not None and cell.n > 0:
            wr[i] = float(cell.p_shrunk)
            known.append(wr[i])
        else:
            imputed[i] = True
    if known:
        wr[imputed] = float(np.mean(known))
    # else: imputed stay 0.5
    return wr, imputed


def _config_point(
    matrix, config: DeckConfig, field_archetypes: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Per-opponent max-over-modes point WR for a config.

    Returns ``(wr_base, wr_adj, imputed_chosen, chosen_mode)``:
      - ``wr_base``: max over modes of base p_shrunk (no lifts).
      - ``wr_adj``: max over modes of (base + mode lift), clamped [0,1] — lift can change the winner.
      - ``imputed_chosen``: whether the mode that wins ``wr_adj`` was imputed for that opponent.
      - ``chosen_mode``: the winning mode's archetype per opponent.
    """
    m = len(field_archetypes)
    mode_wr = []
    mode_imp = []
    for mode in config.modes:
        wr, imp = _row_point_wr(matrix, mode.archetype, field_archetypes)
        adj = wr.copy()
        for opp, delta in mode.lifts.items():
            if opp in field_archetypes:
                j = field_archetypes.index(opp)
                adj[j] = min(1.0, max(0.0, adj[j] + delta))
        mode_wr.append((wr, adj))
        mode_imp.append(imp)

    wr_base = np.full(m, -1.0)
    wr_adj = np.full(m, -1.0)
    imputed_chosen = np.zeros(m, dtype=bool)
    chosen = [""] * m
    for mi, mode in enumerate(config.modes):
        base, adj = mode_wr[mi]
        for i in range(m):
            if adj[i] > wr_adj[i]:
                wr_adj[i] = adj[i]
                wr_base[i] = base[i]
                imputed_chosen[i] = bool(mode_imp[mi][i])
                chosen[i] = mode.archetype
    return wr_base, wr_adj, imputed_chosen, chosen


# ---------------------------------------------------------------------------
# MC base layer (Unit 2) — generalizes positioning._sample_S to max-over-modes + 2 configs
# ---------------------------------------------------------------------------

def _row_P(matrix, archetype: str, field_archetypes: list[str], *, rng, n_draws: int) -> np.ndarray:
    """(n_draws, m) Beta WR draws for ``archetype`` — same cells/imputation as positioning."""
    wins, n, is_mirror, _ = _row_winrate_inputs(matrix, archetype, field_archetypes)
    m = len(field_archetypes)
    P = np.empty((n_draws, m), dtype=np.float64)
    known_mask = (n > 0) & (~is_mirror)
    center = float((wins[known_mask] / n[known_mask]).mean()) if known_mask.any() else 0.5
    for i in range(m):
        if is_mirror[i]:
            P[:, i] = 0.5
        elif n[i] > 0:
            P[:, i] = rng.beta(wins[i] + _BETA_JEFFREYS, (n[i] - wins[i]) + _BETA_JEFFREYS, size=n_draws)
        else:
            a_imp = max(_NODATA_STRENGTH * center, 1e-6)
            b_imp = max(_NODATA_STRENGTH * (1.0 - center), 1e-6)
            P[:, i] = rng.beta(a_imp, b_imp, size=n_draws)
    return P


def _sample_W(field, field_archetypes: list[str], *, rng, n_draws: int) -> np.ndarray:
    """(n_draws, m) field-share weights — Dirichlet from counts if present, else tiled point shares."""
    if getattr(field, "counts", None) is not None:
        alpha = np.array([field.counts[a] for a in field_archetypes], dtype=np.float64) + _DIRICHLET_GAMMA
        return rng.dirichlet(alpha, size=n_draws)
    shares = np.array([field.shares[a] for a in field_archetypes], dtype=np.float64)
    return np.tile(shares, (n_draws, 1))


def _mc_base(
    matrix, field, config_a: DeckConfig, config_b: DeckConfig, field_archetypes: list[str],
    *, n_draws: int, seed: int | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Paired S samples (S_a, S_b) for the BASE (no-lift) configs, sharing field + cell draws."""
    rng = np.random.default_rng(seed)
    W = _sample_W(field, field_archetypes, rng=rng, n_draws=n_draws)  # shared field draw
    row_cache: dict[str, np.ndarray] = {}

    def row(arch: str) -> np.ndarray:
        if arch not in row_cache:  # one draw per distinct archetype row → shared modes correlate
            row_cache[arch] = _row_P(matrix, arch, field_archetypes, rng=rng, n_draws=n_draws)
        return row_cache[arch]

    def config_S(cfg: DeckConfig) -> np.ndarray:
        max_P = row(cfg.modes[0].archetype)
        for mode in cfg.modes[1:]:
            max_P = np.maximum(max_P, row(mode.archetype))
        return (W * max_P).sum(axis=1)

    return config_S(config_a), config_S(config_b)


# ---------------------------------------------------------------------------
# Public engine (Unit 1)
# ---------------------------------------------------------------------------

def compare_configs(
    matrix, field, config_a: DeckConfig, config_b: DeckConfig, *,
    n_draws: int = _DEFAULT_DRAWS, seed: int | None = None,
    breakeven_targets: list[str] | None = None,
) -> ComparisonResult:
    """Compare two configs against ``field``. See module docstring for the two stat layers."""
    field_archetypes = list(field.shares)
    shares = np.array([field.shares[a] for a in field_archetypes], dtype=np.float64)
    warnings: list[str] = []

    if not field_archetypes:
        raise ValueError("compare_configs: field has no archetypes")

    a_base, a_adj, a_imp, a_mode = _config_point(matrix, config_a, field_archetypes)
    b_base, b_adj, b_imp, b_mode = _config_point(matrix, config_b, field_archetypes)

    ev_a_base = float((shares * a_base).sum())
    ev_b_base = float((shares * b_base).sum())
    ev_a_adj = float((shares * a_adj).sum())
    ev_b_adj = float((shares * b_adj).sum())

    rows = [
        MatchupContribution(
            opponent=opp, share=float(shares[i]),
            wr_a_base=float(a_base[i]), wr_b_base=float(b_base[i]),
            wr_a_adj=float(a_adj[i]), wr_b_adj=float(b_adj[i]),
            chosen_mode_a=a_mode[i], chosen_mode_b=b_mode[i],
            imputed_a=bool(a_imp[i]), imputed_b=bool(b_imp[i]),
            contribution_diff=float(shares[i] * (a_adj[i] - b_adj[i])),
        )
        for i, opp in enumerate(field_archetypes)
    ]
    rows.sort(key=lambda r: -abs(r.contribution_diff))

    coverage_a = float(shares[~a_imp].sum())
    coverage_b = float(shares[~b_imp].sum())
    if coverage_a < 0.5 or coverage_b < 0.5:
        warnings.append(
            f"low matchup-data coverage (A={coverage_a:.0%}, B={coverage_b:.0%}) — EV leans on 0.5 imputation"
        )

    # ── MC base layer ────────────────────────────────────────────────────────
    s_a, s_b = _mc_base(matrix, field, config_a, config_b, field_archetypes, n_draws=n_draws, seed=seed)
    ev_a_base_ci = (float(np.percentile(s_a, 2.5)), float(np.percentile(s_a, 97.5)))
    ev_b_base_ci = (float(np.percentile(s_b, 2.5)), float(np.percentile(s_b, 97.5)))
    # Split ties so identical configs (shared per-draw cell draws ⇒ element-wise equal S) read 0.5,
    # not 0.0. For non-identical configs ties are vanishingly rare (continuous Beta draws).
    p_a_beats_b = float((s_a > s_b).mean() + 0.5 * (s_a == s_b).mean())

    # ── Break-even (point overlay) ───────────────────────────────────────────
    if breakeven_targets is not None:
        targets = [t for t in breakeven_targets if t in field_archetypes]
    else:
        targets = sorted({opp for mode in config_a.modes for opp in mode.lifts if opp in field_archetypes})
    target_share = float(sum(field.shares[t] for t in targets))
    breakeven_lift: float | None = None
    breakeven_feasible = True
    if ev_a_base >= ev_b_adj:
        breakeven_lift = None  # A already at/ahead from its base — no lift needed
    elif target_share <= 0.0:
        breakeven_lift = None
        warnings.append("break-even undefined: no target matchups (declare --a-lift or --break-even-matchups)")
    else:
        breakeven_lift = (ev_b_adj - ev_a_base) / target_share
        # Feasibility: a uniform +L on every target must stay within [0,1].
        idx = {opp: k for k, opp in enumerate(field_archetypes)}
        breakeven_feasible = all(a_base[idx[t]] + breakeven_lift <= 1.0 for t in targets)

    return ComparisonResult(
        a_label=config_a.label, b_label=config_b.label, field_source=field.field_source,
        rows=rows, ev_a_base=ev_a_base, ev_b_base=ev_b_base, ev_a_adj=ev_a_adj, ev_b_adj=ev_b_adj,
        ev_a_base_ci=ev_a_base_ci, ev_b_base_ci=ev_b_base_ci, p_a_beats_b_base=p_a_beats_b,
        n_draws=n_draws, breakeven_lift=breakeven_lift, breakeven_targets=targets,
        breakeven_feasible=breakeven_feasible, coverage_a=coverage_a, coverage_b=coverage_b,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Unit 3 — slot-test lift auto-pull
# ---------------------------------------------------------------------------

def slot_lift(con, archetype: str, card: str, opponent: str, *, board: str = "side") -> float | None:
    """Full-corpus measured WR diff (with − without) for ``card`` in ``archetype`` vs ``opponent``.

    Pulls Piece 1's ``card_matchup_contrast`` (full corpus, since/until=None) and returns the cell's
    ``diff``. ``None`` when no computable diff (a cohort is empty).
    """
    from legacy_engine.analytics.slot_test import card_matchup_contrast

    report = card_matchup_contrast(con, archetype, opponent, board=board, cards=[card])
    if not report.cells:
        return None
    return report.cells[0].diff

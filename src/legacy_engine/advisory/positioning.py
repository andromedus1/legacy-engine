"""Meta-positioning score — Bayesian Monte-Carlo implementation.

S(D) = Σ_a w_a · winrate(D vs a)

The expected win rate of deck D against one random opponent drawn from field
distribution w.  Uncertainty is propagated via Monte-Carlo:

- Per draw: sample each cell  p_a ~ Beta(wins+½, (n−wins)+½)  (Jeffreys)
- Mirror cell fixed at 0.5 (zero variance)
- No-data cells imputed with a weak Beta centred on the deck's mean vs known cells
  (or worst observed if ``robust=True``)
- Shares: when field.counts is provided, sample  w ~ Dirichlet(counts+γ);
  when counts is None (custom field), use fixed point shares

Both ``positioning_score`` and ``rank_decks`` build on the vectorised MC core
``_sample_S`` so all decks in a ranking see the same per-draw sampled field
(giving an honest P(best) that captures share-uncertainty correlation).

Units:
  1  ``_row_winrate_inputs`` + ``_sample_S``          — vectorised core
  2  ``PositioningResult``                             — result dataclass
  3  ``positioning_score``                             — single-deck entry point
  4  ``DeckRanking`` + ``rank_decks``                  — ranking entry point
  5  ``delta_var_S``                                    — closed-form sanity check
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field
from typing import Sequence

import numpy as np

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.analytics.matchup import MatchupMatrix

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DRAWS: int = 20_000
_DIRICHLET_GAMMA: float = 0.5      # Jeffreys pseudo-count for Dirichlet
_BETA_JEFFREYS: float = 0.5        # Jeffreys prior pseudo-count for Beta cells
_NODATA_STRENGTH: float = 2.0      # weak pseudo-count for no-data imputation
_THIN_ROW_THRESHOLD: float = 0.5   # warn when >50% of field archetypes are imputed


# ---------------------------------------------------------------------------
# Unit 1 — _row_winrate_inputs + _sample_S
# ---------------------------------------------------------------------------


def _row_winrate_inputs(
    matrix: MatchupMatrix,
    deck_archetype: str,
    field_archetypes: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Extract wins, n, and mirror mask for a deck's row in the given field order.

    Returns
    -------
    wins : ndarray shape (m,)
        Integer win counts per field archetype.
    n : ndarray shape (m,)
        Integer match counts per field archetype (0 for missing cells).
    is_mirror : ndarray bool shape (m,)
        True where the opponent archetype equals ``deck_archetype``.
    no_data : list[str]
        Archetypes with n==0 AND not a mirror (need imputation).
    """
    m = len(field_archetypes)
    wins = np.zeros(m, dtype=np.float64)
    n = np.zeros(m, dtype=np.float64)
    is_mirror = np.zeros(m, dtype=bool)
    no_data: list[str] = []

    for i, opp in enumerate(field_archetypes):
        if opp == deck_archetype:
            is_mirror[i] = True
            # Mirror n comes from the mirror cell if it exists
            cell = matrix.cells.get((deck_archetype, deck_archetype))
            if cell is not None:
                n[i] = cell.n
                wins[i] = cell.wins
            # else n=0, wins=0 — cell absent entirely
        else:
            cell = matrix.cells.get((deck_archetype, opp))
            if cell is not None and cell.n > 0:
                wins[i] = cell.wins
                n[i] = cell.n
            else:
                # n==0 or cell absent → no data
                no_data.append(opp)

    return wins, n, is_mirror, no_data


def _sample_S(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    deck_archetype: str,
    *,
    n_draws: int = _DEFAULT_DRAWS,
    gamma: float = _DIRICHLET_GAMMA,
    include_mirror: bool = True,
    robust: bool = False,
    rng: np.random.Generator,
    shared_w: np.ndarray | None = None,
) -> np.ndarray:
    """Return an (n_draws,) array of S samples for one deck.

    Vectorised over draws:

    - Build an (n_draws, m) Beta matrix P for each field archetype.
    - Build an (n_draws, m) weight matrix W (Dirichlet, or tiled point shares).
    - S = (W * P).sum(axis=1).

    Parameters
    ----------
    shared_w
        Pre-sampled (n_draws, m) weight matrix aligned to ``list(field.shares)``.
        When provided, share sampling is skipped (used by ``rank_decks`` for the
        shared-field correlation that makes P(best) honest).
    """
    field_archetypes = list(field.shares)
    m = len(field_archetypes)

    if m == 0:
        return np.full(n_draws, 0.5)

    wins, n, is_mirror, no_data_list = _row_winrate_inputs(matrix, deck_archetype, field_archetypes)

    # ── Build (n_draws, m) Beta matrix P ────────────────────────────────────
    P = np.empty((n_draws, m), dtype=np.float64)

    for i in range(m):
        if is_mirror[i]:
            # Mirror: fixed 0.5, zero variance
            P[:, i] = 0.5
        elif n[i] > 0:
            # Jeffreys Beta: Beta(wins+½, (n-wins)+½)
            a_param = wins[i] + _BETA_JEFFREYS
            b_param = (n[i] - wins[i]) + _BETA_JEFFREYS
            P[:, i] = rng.beta(a_param, b_param, size=n_draws)
        else:
            # No-data: impute with a weak Beta centred on mean vs known opponents
            # (non-mirror, n>0 cells)
            known_mask = (n > 0) & (~is_mirror)
            if known_mask.any():
                if robust:
                    # worst observed raw winrate
                    center = float((wins[known_mask] / n[known_mask]).min())
                else:
                    # mean raw winrate vs known opponents
                    center = float((wins[known_mask] / n[known_mask]).mean())
            else:
                # No information at all — use 0.5
                center = 0.5
            # Weak Beta: pseudo-strength _NODATA_STRENGTH, centred on `center`
            a_imp = _NODATA_STRENGTH * center + _BETA_JEFFREYS
            b_imp = _NODATA_STRENGTH * (1.0 - center) + _BETA_JEFFREYS
            P[:, i] = rng.beta(a_imp, b_imp, size=n_draws)

    # ── Build (n_draws, m) weight matrix W ──────────────────────────────────
    if shared_w is not None:
        # Caller supplies pre-sampled weights aligned to field_archetypes
        W = shared_w
    elif field.counts is not None:
        # Global field: sample Dirichlet(counts + gamma)
        counts_arr = np.array([field.counts[a] for a in field_archetypes], dtype=np.float64)
        alpha = counts_arr + gamma
        W = rng.dirichlet(alpha, size=n_draws)  # shape (n_draws, m)
    else:
        # Custom field: fixed point shares, no share-variance
        shares_arr = np.array([field.shares[a] for a in field_archetypes], dtype=np.float64)
        W = np.tile(shares_arr, (n_draws, 1))  # shape (n_draws, m)

    # ── Handle include_mirror=False ──────────────────────────────────────────
    if not include_mirror:
        mirror_mask = is_mirror  # shape (m,)
        # Zero out mirror columns in W, then renormalize row-wise
        W = W.copy()
        W[:, mirror_mask] = 0.0
        row_sums = W.sum(axis=1, keepdims=True)
        # Avoid division by zero (degenerate: no non-mirror archetypes)
        safe_sums = np.where(row_sums > 0, row_sums, 1.0)
        W = W / safe_sums

    # ── S = (W * P).sum(axis=1) ─────────────────────────────────────────────
    S = (W * P).sum(axis=1)
    return S


# ---------------------------------------------------------------------------
# Unit 2 — PositioningResult
# ---------------------------------------------------------------------------


@dataclass
class PositioningResult:
    """MC summary for one deck's meta-positioning score.

    Fields
    ------
    deck_archetype
        The archetype label scored.
    s_mean
        Posterior mean of S — field-weighted expected win rate.
    s_ci
        (2.5th, 97.5th) percentile credible interval.
    u_bar
        Unweighted mean win rate over known (n>0, non-mirror) cells.
        The "best-deck" lens: how good is this deck overall?
    field_source
        From ``FieldDistribution.field_source`` — always set.
    n_draws
        Number of MC draws used.
    imputed
        Archetypes imputed (no matchup data in the row).
    warnings
        Ordered informational warnings (thin row, provenance, etc.).
    s_samples
        Raw (n_draws,) sample array; ``None`` unless ``keep_samples=True``.
    """

    deck_archetype: str
    s_mean: float
    s_ci: tuple[float, float]
    u_bar: float
    field_source: str
    n_draws: int
    imputed: frozenset[str]
    warnings: tuple[str, ...]
    s_samples: np.ndarray | None = None


# ---------------------------------------------------------------------------
# Unit 3 — positioning_score
# ---------------------------------------------------------------------------


def positioning_score(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    deck_archetype: str,
    *,
    n_draws: int = _DEFAULT_DRAWS,
    gamma: float = _DIRICHLET_GAMMA,
    include_mirror: bool = True,
    robust: bool = False,
    keep_samples: bool = False,
    seed: int | None = None,
) -> PositioningResult:
    """Score one deck's meta-positioning S(D) against the field via Bayesian MC.

    Also computes the unweighted aggregate Ū(D) — the best-deck lens.

    Parameters
    ----------
    matrix
        Assembled matchup matrix (from ``build_matrix``).
    field
        Field distribution (from ``build_global_field`` or ``build_custom_field``).
    deck_archetype
        The archetype label to score.
    n_draws
        MC sample count (default 20 000).
    gamma
        Dirichlet pseudo-count (default 0.5, Jeffreys).
    include_mirror
        Include the self-mirror at field share, p=0.5 (default True).
    robust
        Use worst observed win rate for no-data imputation (default False =
        mean vs known).
    keep_samples
        Retain the raw ``(n_draws,)`` S array in the result (default False).
    seed
        RNG seed for determinism; None = non-deterministic.

    Returns
    -------
    PositioningResult
    """
    rng = np.random.default_rng(seed)

    field_archetypes = list(field.shares)
    wins, n, is_mirror, no_data_list = _row_winrate_inputs(matrix, deck_archetype, field_archetypes)

    # ── MC samples ──────────────────────────────────────────────────────────
    samples = _sample_S(
        matrix, field, deck_archetype,
        n_draws=n_draws, gamma=gamma,
        include_mirror=include_mirror, robust=robust,
        rng=rng,
    )

    s_mean = float(samples.mean())
    lo, hi = np.percentile(samples, [2.5, 97.5])
    s_ci = (float(lo), float(hi))

    # ── Ū — unweighted mean over known (n>0, non-mirror) cells ──────────────
    known_mask = (n > 0) & (~is_mirror)
    if known_mask.any():
        u_bar = float((wins[known_mask] / n[known_mask]).mean())
    else:
        u_bar = 0.5  # no information

    # ── Warnings ─────────────────────────────────────────────────────────────
    warnings_list: list[str] = list(field.warnings)

    imputed_set = frozenset(no_data_list)

    # Also flag field archetypes listed in field.no_data (custom field)
    all_imputed = imputed_set | (field.no_data & frozenset(field_archetypes))

    if all_imputed:
        warnings_list.append(
            f"imputed {len(all_imputed)} no-data opponent(s): "
            + ", ".join(sorted(all_imputed))
        )

    # Thin-row warning: if more than half of field archetypes lack data
    total_non_mirror = sum(1 for a in field_archetypes if a != deck_archetype)
    if total_non_mirror > 0:
        imputed_non_mirror = sum(1 for a in no_data_list if a != deck_archetype) + len(
            field.no_data & frozenset(a for a in field_archetypes if a != deck_archetype)
        )
        if imputed_non_mirror / total_non_mirror > _THIN_ROW_THRESHOLD:
            warnings_list.append(
                f"thin row for {deck_archetype!r}: "
                f"{imputed_non_mirror}/{total_non_mirror} opponent(s) imputed; "
                "S is dominated by the imputation prior"
            )

    return PositioningResult(
        deck_archetype=deck_archetype,
        s_mean=s_mean,
        s_ci=s_ci,
        u_bar=u_bar,
        field_source=field.field_source,
        n_draws=n_draws,
        imputed=all_imputed,
        warnings=tuple(warnings_list),
        s_samples=samples if keep_samples else None,
    )


# ---------------------------------------------------------------------------
# Unit 4 — DeckRanking + rank_decks
# ---------------------------------------------------------------------------


@dataclass
class DeckRanking:
    """Ranked list of candidate decks under shared-field MC uncertainty.

    Fields
    ------
    decks
        Candidates sorted best→worst by ``p_best`` (or 5th-percentile S if
        ``risk_averse=True``).
    p_best
        P(S_D = max) across shared-field draws.
    s_mean
        Posterior mean S per deck.
    s_ci
        (2.5th, 97.5th) credible interval per deck.
    pairwise
        P(S_a > S_b) for every ordered pair (a, b).
    field_source
        From the field distribution.
    """

    decks: list[str]
    p_best: dict[str, float]
    s_mean: dict[str, float]
    s_ci: dict[str, tuple[float, float]]
    pairwise: dict[tuple[str, str], float]
    field_source: str


def rank_decks(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    candidates: list[str],
    *,
    n_draws: int = _DEFAULT_DRAWS,
    gamma: float = _DIRICHLET_GAMMA,
    robust: bool = False,
    risk_averse: bool = False,
    seed: int | None = None,
) -> DeckRanking:
    """Rank candidate decks under shared-field MC.

    Samples ONE shared field ``(n_draws, m)`` per iteration and scores ALL
    candidate decks against that same sampled field — giving an honest
    P(best) that respects the Dirichlet Σw=1 constraint across decks.

    Parameters
    ----------
    risk_averse
        Sort by 5th-percentile S (conservative ranking) instead of p_best.
    """
    if not candidates:
        return DeckRanking(
            decks=[],
            p_best={},
            s_mean={},
            s_ci={},
            pairwise={},
            field_source=field.field_source,
        )

    rng = np.random.default_rng(seed)

    field_archetypes = list(field.shares)
    m = len(field_archetypes)

    # ── Sample ONE shared field (n_draws, m) ─────────────────────────────────
    if m == 0:
        shared_w = np.ones((n_draws, 1)) / 1.0  # degenerate
    elif field.counts is not None:
        counts_arr = np.array([field.counts[a] for a in field_archetypes], dtype=np.float64)
        alpha = counts_arr + gamma
        shared_w = rng.dirichlet(alpha, size=n_draws)
    else:
        shares_arr = np.array([field.shares[a] for a in field_archetypes], dtype=np.float64)
        shared_w = np.tile(shares_arr, (n_draws, 1))

    # ── Score each candidate against the shared field ─────────────────────
    # Shape: (n_draws, k)  where k = len(candidates)
    k = len(candidates)
    all_S = np.empty((n_draws, k), dtype=np.float64)

    for j, deck in enumerate(candidates):
        all_S[:, j] = _sample_S(
            matrix, field, deck,
            n_draws=n_draws, gamma=gamma,
            include_mirror=True, robust=robust,
            rng=rng,
            shared_w=shared_w,
        )

    # ── p_best: fraction of draws where each deck is the maximum ─────────
    best_idx = np.argmax(all_S, axis=1)  # shape (n_draws,)
    p_best: dict[str, float] = {}
    for j, deck in enumerate(candidates):
        p_best[deck] = float((best_idx == j).mean())

    # ── s_mean + s_ci ─────────────────────────────────────────────────────
    s_mean_dict: dict[str, float] = {}
    s_ci_dict: dict[str, tuple[float, float]] = {}
    for j, deck in enumerate(candidates):
        col = all_S[:, j]
        s_mean_dict[deck] = float(col.mean())
        lo, hi = np.percentile(col, [2.5, 97.5])
        s_ci_dict[deck] = (float(lo), float(hi))

    # ── pairwise P(S_a > S_b) ────────────────────────────────────────────
    pairwise: dict[tuple[str, str], float] = {}
    for j, a in enumerate(candidates):
        for l, b in enumerate(candidates):  # noqa: E741
            if a != b:
                pairwise[(a, b)] = float((all_S[:, j] > all_S[:, l]).mean())

    # ── Sort ──────────────────────────────────────────────────────────────
    if risk_averse:
        # Sort by 5th-percentile S descending
        p5 = {deck: float(np.percentile(all_S[:, j], 5)) for j, deck in enumerate(candidates)}
        sorted_decks = sorted(candidates, key=lambda d: p5[d], reverse=True)
    else:
        sorted_decks = sorted(candidates, key=lambda d: p_best[d], reverse=True)

    return DeckRanking(
        decks=sorted_decks,
        p_best=p_best,
        s_mean=s_mean_dict,
        s_ci=s_ci_dict,
        pairwise=pairwise,
        field_source=field.field_source,
    )


# ---------------------------------------------------------------------------
# Unit 5 — delta_var_S  (closed-form sanity check)
# ---------------------------------------------------------------------------


def delta_var_S(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    deck_archetype: str,
) -> float:
    """Closed-form Var(S) = Σ_a w_a² · p̂_a(1−p̂_a) / n_a.

    Delta-method approximation using point estimates.  Known (n>0, non-mirror)
    cells only.  Useful as a fast sanity check on the MC posterior spread.

    Returns 0.0 when there are no known cells.
    """
    field_archetypes = list(field.shares)
    wins, n, is_mirror, _ = _row_winrate_inputs(matrix, deck_archetype, field_archetypes)

    var_S = 0.0
    for i, opp in enumerate(field_archetypes):
        if is_mirror[i] or n[i] == 0:
            continue
        w = field.shares[opp]
        p_hat = wins[i] / n[i]
        var_S += (w ** 2) * p_hat * (1.0 - p_hat) / n[i]

    return var_S

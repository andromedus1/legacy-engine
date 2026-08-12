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

**Ranking headline:** ``rank_decks`` sorts by a risk-adjusted lower-posterior-
quantile of each deck's S samples (``risk_quantile=0.25`` default).  This
penalises thin-data, high-variance decks whose P(best) could spike spuriously
in the shared-field MC.  ``p_best`` is kept as a secondary reported dict.

**data_coverage:** fraction of field share-mass the deck has a *measured* cell
against (``cell.display``, i.e. n≥30, non-mirror).  Consumers and the report
layer can condition on this to label or exclude low-data decks.

Units:
  1  ``_row_winrate_inputs`` + ``_sample_S``          — vectorised core
  2  ``PositioningResult``                             — result dataclass
  3  ``positioning_score``                             — single-deck entry point
  4  ``DeckRanking`` + ``rank_decks``                  — ranking entry point
  5  ``delta_var_S``                                    — closed-form sanity check
  6  ``GranularPositioningResult`` + ``composition_adjusted_winrates``
     + ``positioning_score_granular``                  — opt-in heuristic overlay
     PRESENCE-CORRELATIONAL HEURISTIC, NOT CAUSAL PRECISION.  Default OFF;
     archetype-level S is byte-identical to the baseline when not invoked.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field as dataclass_field
from typing import Literal, TypedDict

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
_COVERAGE_RESTRICT_THRESHOLD: float = 0.85   # below this data_coverage, restrict S to the covered sub-field
_PBEST_SUPPRESS_COVERAGE: float = 0.05       # below this data_coverage, P(best) is imputation noise → suppress in display
_DEFAULT_RISK_QUANTILE: float = 0.25   # default lower-quantile for risk-adjusted ranking
_RISK_AVERSE_QUANTILE: float = 0.05   # quantile used when risk_averse=True

RankingEvidenceStratum = Literal[
    "grounded", "lean", "imputation-dominated", "transition-prior", "inactive", "unscorable"
]


class RankingEvidencePayload(TypedDict):
    stratum: RankingEvidenceStratum
    measured_share: float
    imputed_share: float
    observed_field_share: float
    decision_field_share: float
    eligible: bool
    reason: str | None


def ranking_evidence_payload(
    *,
    field_share: float | None = None,
    measured_share: float,
    resolved_cells: int,
    grounded: bool,
    observed_field_share: float | None = None,
    decision_field_share: float | None = None,
    transition_prior: bool = False,
    suppress_coverage: float = _PBEST_SUPPRESS_COVERAGE,
) -> RankingEvidencePayload:
    """Classify a row's evidence without changing its score or display presence."""
    if decision_field_share is None:
        decision_field_share = field_share if field_share is not None else 0.0
    if observed_field_share is None:
        observed_field_share = decision_field_share
    if decision_field_share < 0.0 or observed_field_share < 0.0:
        raise ValueError("field shares must be non-negative")
    measured = min(1.0, max(0.0, measured_share))
    imputed = min(1.0, max(0.0, 1.0 - measured))
    reason: str | None = None
    if decision_field_share <= 0.0:
        stratum: RankingEvidenceStratum = "inactive"
        reason = "no current-field presence"
    elif resolved_cells == 0:
        stratum = "unscorable"
        reason = "no resolved matchup cells against the selected field"
    elif measured < suppress_coverage:
        stratum = "unscorable"
        reason = f"measured field coverage {measured:.1%} is below {suppress_coverage:.0%}"
    elif imputed > 0.5:
        stratum = "imputation-dominated"
    elif transition_prior and observed_field_share <= 0.0:
        stratum = "transition-prior"
    elif grounded:
        stratum = "grounded"
    else:
        stratum = "lean"
    return {
        "stratum": stratum,
        "measured_share": measured,
        "imputed_share": imputed,
        "observed_field_share": float(observed_field_share),
        "decision_field_share": float(decision_field_share),
        "eligible": stratum not in ("inactive", "unscorable"),
        "reason": reason,
    }


def practical_recommendation_order(
    rows: Mapping[str, Mapping[str, object]],
) -> tuple[str, ...]:
    """Order supported rows by the existing posterior lean, without changing Agency authority."""
    eligible: list[tuple[str, float, float]] = []
    for label, row in rows.items():
        evidence = row.get("ranking_evidence")
        if isinstance(evidence, Mapping) and not evidence.get("eligible", False):
            continue
        methodology = row.get("methodology")
        lean = methodology.get("lean") if isinstance(methodology, Mapping) else row.get("lean")
        if not isinstance(lean, Mapping):
            continue
        q25 = lean.get("q25")
        median = lean.get("median")
        if isinstance(q25, (int, float)) and isinstance(median, (int, float)):
            eligible.append((str(label), float(q25), float(median)))
    return tuple(label for label, _q25, _median in sorted(
        eligible, key=lambda item: (-item[1], -item[2], item[0]),
    ))


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
            # Weak Beta: concentration-only params so the distribution is exactly
            # centred on `center`.  a/b = strength * center / (1-center) so
            # E[X] = a/(a+b) = center.  A small eps guard prevents a=0 when
            # center∈{0,1} (which would be degenerate).
            _eps = 1e-6
            a_imp = max(_NODATA_STRENGTH * center, _eps)
            b_imp = max(_NODATA_STRENGTH * (1.0 - center), _eps)
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
        # Degenerate case: all columns are mirror (mirror-only field).
        # Returning 0.0 would be misleading; 0.5 is the correct undefined-view
        # sentinel (same as the mirror cell itself).
        if not (row_sums > 0).any():
            log.warning(
                "_sample_S: include_mirror=False but the field consists entirely of "
                "mirror archetypes for %r — S is undefined; returning 0.5",
                deck_archetype,
            )
            return np.full(n_draws, 0.5)
        safe_sums = np.where(row_sums > 0, row_sums, 1.0)
        W = W / safe_sums

    # ── S = (W * P).sum(axis=1) ─────────────────────────────────────────────
    S = (W * P).sum(axis=1)
    return S


# ---------------------------------------------------------------------------
# Internal helper — data_coverage
# ---------------------------------------------------------------------------


def _is_covered_cell(
    matrix: MatchupMatrix,
    deck_archetype: str,
    opp: str,
    *,
    min_n: int | None = None,
) -> bool:
    """Whether ``deck`` has trustworthy matchup data against ``opp``.

    Single source of truth for "covered": the self-mirror (a fixed-0.5 cell that is never
    imputed) counts as covered, as does any *displayed* (n ≥ DISPLAY_GATE_N), non-mirror
    cell.  An absent or thin (n < gate) cell is NOT covered.
    """
    if min_n is not None and min_n < 1:
        raise ValueError("coverage min_n must be >= 1")
    if opp == deck_archetype:
        return True  # mirror: fixed 0.5, never imputed
    cell = matrix.cells.get((deck_archetype, opp))
    if cell is None or cell.is_mirror:
        return False
    return cell.display if min_n is None else cell.n >= min_n


def covered_field_archetypes(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    deck_archetype: str,
) -> frozenset[str]:
    """The keep-set for restriction: field archetypes the deck has covered data against.

    Includes the deck's own archetype (the mirror) so that restricting the field to this set
    keeps the self-mirror column rather than producing a degenerate field.
    """
    return frozenset(a for a in field.shares if _is_covered_cell(matrix, deck_archetype, a))


def _compute_data_coverage(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    deck_archetype: str,
    *,
    min_n: int | None = None,
) -> float:
    """Fraction of *non-mirror* field share-mass the deck has a measured cell against.

    A cell is measured per ``_is_covered_cell`` (n ≥ DISPLAY_GATE_N, non-mirror).  Share-mass
    weighting means a deck fully covered against the top-50% opponent gets ~0.5, not a binary
    count fraction — matching the decision-relevant question "what share of a random opponent
    does this deck have honest data for?".  The mirror is excluded from the denominator here
    (the coverage *ratio* is about opponents) even though it is in the keep-*set* above.

    Returns 1.0 when the field is empty (degenerate; no coverage needed).
    """
    if min_n is not None and min_n < 1:
        raise ValueError("coverage min_n must be >= 1")
    field_archetypes = list(field.shares)
    if not field_archetypes:
        return 1.0

    covered_mass = 0.0
    total_non_mirror_mass = 0.0

    for opp in field_archetypes:
        if opp == deck_archetype:
            continue  # skip mirror — not part of the coverage-ratio denominator
        share = field.shares[opp]
        total_non_mirror_mass += share
        if _is_covered_cell(matrix, deck_archetype, opp, min_n=min_n):
            covered_mass += share

    if total_non_mirror_mass <= 0.0:
        return 1.0  # field is all self-mirror; coverage is vacuously 1.0

    return covered_mass / total_non_mirror_mass


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
    data_coverage
        Fraction of non-mirror field share-mass the deck has a *measured*
        cell against (``cell.display``, i.e. n≥30).  1.0 = fully covered;
        0.0 = all cells are imputed.  Always computed on the FULL field — the
        honest "you have data for X% of the real field" — even when ``s_mean``
        is computed on a restricted sub-field.
    restricted
        True when ``s_mean`` was computed on the covered sub-field (because
        ``data_coverage`` fell below the restrict threshold) rather than the
        full field.  When False, S is the full-field score (byte-identical to
        the pre-restriction behavior).
    excluded_share
        Share-mass dropped by restriction (0.0 when not restricted).
    excluded_archetypes
        Field archetypes excluded by restriction (empty when not restricted).
    s_computable
        False when there is no covered (non-mirror) opponent at all — S cannot
        be honestly computed, so ``s_mean``/``s_ci`` are NaN and consumers must
        present "not computable" rather than a fabricated number.
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
    data_coverage: float = 1.0
    restricted: bool = False
    excluded_share: float = 0.0
    excluded_archetypes: frozenset[str] = frozenset()
    s_computable: bool = True
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
    restrict_to_covered: bool = True,
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
    restrict_to_covered
        When True (default) and ``data_coverage`` falls below
        ``_COVERAGE_RESTRICT_THRESHOLD``, compute S over the covered sub-field
        (renormalized) rather than the full field — so S is an honest expected
        WR vs the part of the field that has matchup data, not a number
        dominated by the imputation prior.  When coverage is already at/above
        the threshold, the field is left untouched and the result is
        byte-identical to ``restrict_to_covered=False``.
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

    # ── data_coverage — share-mass fraction with measured (n≥30) cells (FULL field) ──
    # Always computed on the full field: the honest "you have data for X% of the real field",
    # independent of whether the score below is restricted to the covered sub-field.
    data_coverage = _compute_data_coverage(matrix, field, deck_archetype)

    # ── Choose the scoring field: restrict to the covered sub-field when coverage is low ──
    scoring_field = field
    restricted = False
    excluded_share = 0.0
    excluded_archetypes: frozenset[str] = frozenset()
    s_computable = True
    restrict_warning: str | None = None

    if restrict_to_covered and data_coverage < _COVERAGE_RESTRICT_THRESHOLD:
        covered = covered_field_archetypes(matrix, field, deck_archetype)
        non_mirror_covered = [a for a in covered if a != deck_archetype]
        if not non_mirror_covered:
            # Zero coverage: no honest opponent to score against — refuse rather than
            # auto-restrict to a degenerate mirror-only field that would read 0.5.
            s_computable = False
            restrict_warning = (
                "S not computable: no covered (n≥30) matchups in the field; "
                "any score would be pure imputation prior"
            )
        else:
            scoring_field, excluded_share = field.restrict_to(covered)
            excluded_archetypes = frozenset(field_archetypes) - covered
            restricted = True
            restrict_warning = (
                f"restricted S to the covered sub-field — excluded {excluded_share:.1%} of the "
                f"field with no matchup data ({len(excluded_archetypes)} archetype(s))"
            )

    # ── MC samples (on the scoring field) ────────────────────────────────────
    if s_computable:
        samples = _sample_S(
            matrix, scoring_field, deck_archetype,
            n_draws=n_draws, gamma=gamma,
            include_mirror=include_mirror, robust=robust,
            rng=rng,
        )
        s_mean = float(samples.mean())
        lo, hi = np.percentile(samples, [2.5, 97.5])
        s_ci = (float(lo), float(hi))
    else:
        samples = np.full(n_draws, np.nan)
        s_mean = float("nan")
        s_ci = (float("nan"), float("nan"))

    # ── Ū — unweighted mean over known (n>0, non-mirror) cells ──────────────
    known_mask = (n > 0) & (~is_mirror)
    if known_mask.any():
        u_bar = float((wins[known_mask] / n[known_mask]).mean())
    else:
        u_bar = 0.5  # no information

    # ── Warnings ─────────────────────────────────────────────────────────────
    warnings_list: list[str] = list(field.warnings)

    # ── imputed — archetypes that were actually imputed in the SCORING field ──
    # When restricted=True, S was scored on the covered sub-field; excluded opponents
    # were dropped entirely (not imputed).  Listing them in `imputed` is misleading
    # ("imputed N no-data opponent(s)" fires for opponents we never scored against).
    # Fix: restrict the imputed set to scoring-field archetypes only.
    # When s_computable=False, no MC ran at all — nothing was imputed.
    if not s_computable:
        # Zero-coverage: S not computed; nothing was imputed
        all_imputed: frozenset[str] = frozenset()
    elif restricted:
        # Scoring field is the covered sub-field; re-derive no_data only within it.
        scoring_field_archetypes = list(scoring_field.shares)
        _, s_n, s_is_mirror, s_no_data_list = _row_winrate_inputs(
            matrix, deck_archetype, scoring_field_archetypes
        )
        s_imputed_set = frozenset(s_no_data_list)
        all_imputed = s_imputed_set | (scoring_field.no_data & frozenset(scoring_field_archetypes))
    else:
        imputed_set = frozenset(no_data_list)
        # Also flag field archetypes listed in field.no_data (custom field)
        all_imputed = imputed_set | (field.no_data & frozenset(field_archetypes))

    if all_imputed:
        warnings_list.append(
            f"imputed {len(all_imputed)} no-data opponent(s): "
            + ", ".join(sorted(all_imputed))
        )

    # Thin-row warning: if more than half of field archetypes lack data.
    # Suppressed when we restricted (or couldn't compute) S — the "dominated by the imputation
    # prior" framing is false once S is scored on the covered sub-field; the restrict/not-computable
    # warning below carries the honest message instead.
    if restricted or not s_computable:
        if restrict_warning is not None:
            warnings_list.append(restrict_warning)
    else:
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
        data_coverage=data_coverage,
        restricted=restricted,
        excluded_share=excluded_share,
        excluded_archetypes=excluded_archetypes,
        s_computable=s_computable,
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
        Candidates sorted best→worst by the risk-adjusted lower-quantile of S
        (controlled by ``risk_quantile`` in ``rank_decks``; default q=0.25).
        This penalises thin-data, high-variance decks that would otherwise
        spike to the top of a raw P(best) ranking.
    p_best
        Secondary field: P(S_D = max) across shared-field draws.  Kept for
        diagnostics and display — no longer the sort key.
    s_mean
        Posterior mean S per deck.  Always the FULL-FIELD shared-MC value —
        ``rank_decks`` uses one shared sampled field for all candidates so
        P(best) is honest; per-deck restriction to different sub-fields is
        not possible here.  Consumers should display "S (full-field)" for
        decks in ``coverage_caveated`` rather than presenting this as if it
        were the same restricted-sub-field S that ``positioning_score`` shows.
    s_ci
        (2.5th, 97.5th) credible interval per deck.
    s_quantile
        The lower-quantile value used as the headline sort key (keyed by deck).
        ``quantile_level`` records which quantile was used.
    quantile_level
        The quantile used for sorting (matches ``risk_quantile`` param).
    data_coverage
        Fraction of non-mirror field share-mass the deck has a measured cell
        against (n≥30).  Keyed by deck archetype.
    low_coverage
        Set of deck archetypes whose ``data_coverage < min_coverage``.  These
        are flagged, not silently dropped — they remain in ``decks``.
    coverage_caveated
        Set of deck archetypes whose ``data_coverage < _COVERAGE_RESTRICT_THRESHOLD``
        (0.85) — the same threshold at which ``positioning_score`` auto-restricts
        the single-deck view to the covered sub-field.  Because ``rank_decks``
        cannot per-deck-restrict (shared-field MC constraint), their ``s_mean``
        is a full-field estimate dominated by imputation; consumers must label
        it as such.  Always populated regardless of ``min_coverage``.
    pairwise
        P(S_a > S_b) for every ordered pair (a, b).
    field_source
        From the field distribution.
    """

    decks: list[str]
    p_best: dict[str, float]
    s_mean: dict[str, float]
    s_ci: dict[str, tuple[float, float]]
    s_quantile: dict[str, float]
    quantile_level: float
    data_coverage: dict[str, float]
    low_coverage: set[str]
    coverage_caveated: set[str]
    pairwise: dict[tuple[str, str], float]
    field_source: str
    imputation_share: dict[str, float] = dataclass_field(default_factory=dict)


def rank_decks(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    candidates: list[str],
    *,
    n_draws: int = _DEFAULT_DRAWS,
    gamma: float = _DIRICHLET_GAMMA,
    robust: bool = False,
    risk_averse: bool = False,
    risk_quantile: float = _DEFAULT_RISK_QUANTILE,
    min_coverage: float = 0.0,
    coverage_min_n: int | None = None,
    seed: int | None = None,
) -> DeckRanking:
    """Rank candidate decks under shared-field MC.

    Samples ONE shared field ``(n_draws, m)`` per iteration and scores ALL
    candidate decks against that same sampled field — giving an honest
    P(best) that respects the Dirichlet Σw=1 constraint across decks.

    The headline ranking sort key is the **risk-adjusted lower-posterior-
    quantile** of each deck's S samples (default q=0.25).  This penalises
    thin-data, high-variance decks that spike spuriously in the argmax MC
    but have genuinely unreliable positioning estimates.  ``p_best`` is
    still computed and returned as a secondary field.

    Parameters
    ----------
    risk_averse
        Convenience flag: forces ``risk_quantile = _RISK_AVERSE_QUANTILE``
        (0.05) for a more conservative sort.  Mutually consistent with
        ``risk_quantile`` — if both are provided, ``risk_averse=True``
        overrides to 0.05.
    risk_quantile
        The quantile of the S posterior used as the headline sort key.
        Default 0.25 (lower quartile).  Lower values are more conservative.
        ``risk_averse=True`` overrides this to 0.05.
    min_coverage
        Decks with ``data_coverage < min_coverage`` are added to
        ``DeckRanking.low_coverage`` and flagged — they are NOT dropped
        from ``decks``.  Default 0.0 (no flagging).
    """
    if coverage_min_n is not None and coverage_min_n < 1:
        raise ValueError("coverage_min_n must be >= 1")

    # Reconcile risk_averse / risk_quantile: risk_averse=True → use 0.05
    effective_q = _RISK_AVERSE_QUANTILE if risk_averse else risk_quantile

    if not candidates:
        return DeckRanking(
            decks=[],
            p_best={},
            s_mean={},
            s_ci={},
            s_quantile={},
            quantile_level=effective_q,
            data_coverage={},
            low_coverage=set(),
            coverage_caveated=set(),
            pairwise={},
            field_source=field.field_source,
            imputation_share={},
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
    # Split tied-max credit evenly across all tied candidates per draw so that
    # identical/equal-performing decks each receive P(best)=1/k rather than
    # the first candidate receiving 1.0 (np.argmax breaks ties to lowest index).
    row_max = all_S.max(axis=1, keepdims=True)          # shape (n_draws, 1)
    is_max = (all_S == row_max)                          # shape (n_draws, k) bool
    tie_counts = is_max.sum(axis=1, keepdims=True)       # shape (n_draws, 1) int
    credit = is_max / tie_counts.astype(np.float64)      # shape (n_draws, k)
    p_best: dict[str, float] = {}
    for j, deck in enumerate(candidates):
        p_best[deck] = float(credit[:, j].mean())

    # ── s_mean + s_ci ─────────────────────────────────────────────────────
    s_mean_dict: dict[str, float] = {}
    s_ci_dict: dict[str, tuple[float, float]] = {}
    for j, deck in enumerate(candidates):
        col = all_S[:, j]
        s_mean_dict[deck] = float(col.mean())
        lo, hi = np.percentile(col, [2.5, 97.5])
        s_ci_dict[deck] = (float(lo), float(hi))

    # ── s_quantile — lower-posterior-quantile headline sort key ──────────
    # Computed at effective_q (default 0.25); penalises thin-data high-
    # variance decks whose S spikes in the argmax MC but is unreliable.
    s_quantile_dict: dict[str, float] = {}
    for j, deck in enumerate(candidates):
        s_quantile_dict[deck] = float(np.percentile(all_S[:, j], effective_q * 100))

    # ── data_coverage per deck ────────────────────────────────────────────
    coverage_dict: dict[str, float] = {
        deck: _compute_data_coverage(
            matrix, field, deck, min_n=coverage_min_n,
        ) for deck in candidates
    }
    imputation_dict = {
        deck: min(1.0, max(0.0, 1.0 - coverage))
        for deck, coverage in coverage_dict.items()
    }

    # ── low_coverage flag set ─────────────────────────────────────────────
    low_coverage: set[str] = {
        deck for deck, cov in coverage_dict.items() if cov < min_coverage
    }
    if low_coverage:
        log.warning(
            "rank_decks: %d deck(s) below min_coverage=%.2f: %s",
            len(low_coverage),
            min_coverage,
            ", ".join(sorted(low_coverage)),
        )

    # ── coverage_caveated — decks that would be restricted in positioning_score ──
    # Populated at the same 0.85 threshold positioning_score uses for auto-restrict
    # so the ranking path is consistent with the single-deck path.  S values for
    # these decks are full-field (shared-MC constraint) and dominated by imputation;
    # consumers must label them as such rather than presenting them as equivalent to
    # the restricted-sub-field S positioning_score returns.
    coverage_caveated: set[str] = {
        deck for deck, cov in coverage_dict.items() if cov < _COVERAGE_RESTRICT_THRESHOLD
    }
    if coverage_caveated:
        log.debug(
            "rank_decks: %d deck(s) in coverage_caveated (data_coverage < %.2f): %s",
            len(coverage_caveated),
            _COVERAGE_RESTRICT_THRESHOLD,
            ", ".join(sorted(coverage_caveated)),
        )

    # ── pairwise P(S_a ≥ S_b) with half-credit on exact ties ────────────
    # Use (strict win) + 0.5 * (tie) so P(a>b) + P(b>a) = 1.0 even for
    # identical candidates (pure ties give each side 0.5).
    pairwise: dict[tuple[str, str], float] = {}
    for j, a in enumerate(candidates):
        for l, b in enumerate(candidates):  # noqa: E741
            if a != b:
                Sa = all_S[:, j]
                Sb = all_S[:, l]
                pairwise[(a, b)] = float(
                    ((Sa > Sb).astype(np.float64) + 0.5 * (Sa == Sb).astype(np.float64)).mean()
                )

    # ── Sort by risk-adjusted lower-quantile (headline ranking) ──────────
    sorted_decks = sorted(candidates, key=lambda d: s_quantile_dict[d], reverse=True)

    return DeckRanking(
        decks=sorted_decks,
        p_best=p_best,
        s_mean=s_mean_dict,
        s_ci=s_ci_dict,
        s_quantile=s_quantile_dict,
        quantile_level=effective_q,
        data_coverage=coverage_dict,
        low_coverage=low_coverage,
        coverage_caveated=coverage_caveated,
        pairwise=pairwise,
        field_source=field.field_source,
        imputation_share=imputation_dict,
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


# ---------------------------------------------------------------------------
# Unit 6 — List-granular positioning overlay  (OPT-IN, DEFAULT OFF)
#
# HEURISTIC CAVEAT:
#   ``composition_adjusted_winrates`` and ``positioning_score_granular`` produce a
#   *presence-correlational* adjustment to per-matchup win-rates based on which
#   cards in the submitted list deviate from the archetype baseline.
#
#   - "Decks containing card X win more vs archetype M" is an *association*, not a
#     causal effect.  Pilot skill, deck selection, and small samples all confound it.
#   - The overlay is an EXPERIMENTAL heuristic for differentiating two same-archetype
#     lists.  Do NOT present it as higher-precision positioning data.
#   - The default ``positioning_score`` path is completely unchanged.  This unit is
#     only invoked when callers explicitly call ``positioning_score_granular``.
# ---------------------------------------------------------------------------

#: Maximum absolute per-matchup nudge in win-rate units.  Caps each card's
#: lift contribution so a single high-lift card in a thin matchup cannot
#: swing the overlay by more than this per opponent.
#:
#: Calibration rationale: a ±5 pp clamp keeps the worst-case per-matchup shift
#: below the ~10 pp range of a strong (established) single-card matchup signal.
#: Observed grindy-vs-lean Dimir Tempo differentiation (≈2–4 pp on a 60% ANT
#: field) is well within this cap — tightening to ±3 pp passes the same tests
#: but leaves less headroom for genuine multi-card stacking.  Loosen only if
#: calibration on real corpus data shows the current cap is consistently binding
#: (i.e. every matchup hits the wall), which would suggest the scale is also
#: too aggressive.
_GRANULAR_MAX_NUDGE: float = 0.05

#: Scale factor applied to the aggregated card-lift signal before nudging.
#: Keeps the overlay clearly sub-dominant relative to archetype-level WR.
#:
#: Calibration rationale: 0.5× ensures the aggregate lift of all cards in the
#: deck is halved before being applied, which (combined with the ±5 pp clamp)
#: keeps |s_granular − base_S| well under 5 pp in all observed scenarios.
#: Real-corpus calibration target: |s_granular − base_S| < max_nudge (5 pp).
#: Both constants are tested by ``test_positioning_granular_hardening.py``
#: (sub-dominance bound + grindy/lean differentiation reproduction).
_GRANULAR_SCALE: float = 0.5

#: Honesty caveat attached to every GranularPositioningResult.
GRANULAR_CAVEAT: str = (
    "[EXPERIMENTAL] List-granular S_granular is a presence-correlational heuristic overlay "
    "on top of archetype-level S.  Card lift signals reflect registered-75 associations "
    "(not causal win-rate deltas) and are confounded by pilot skill and sample size.  "
    "Do not treat S_granular as higher-precision positioning data."
)


@dataclass
class GranularPositioningResult:
    """Result of the opt-in list-granular positioning overlay.

    Fields
    ------
    base
        The archetype-level ``PositioningResult`` (unchanged; byte-identical to
        calling ``positioning_score`` directly).
    s_granular
        Field-weighted expected win-rate after nudging per-matchup win-rates by
        the deck's card-composition deviation from the archetype baseline.
        This is a presence-correlational heuristic — see ``GRANULAR_CAVEAT``.
    adjusted_winrates
        Per-opponent adjusted win-rate used to compute ``s_granular``.
        Keyed by field archetype (opponents only; mirror is excluded).
    caveat
        Always ``GRANULAR_CAVEAT``.  Consumers must display this.
    """

    base: PositioningResult
    s_granular: float
    adjusted_winrates: dict[str, float]
    caveat: str


def filter_nonland_cards(
    deck_cards: dict[str, int],
    is_land_fn,  # callable(card_name: str) -> bool
) -> dict[str, int]:
    """Return ``deck_cards`` with land cards removed.

    ``is_land_fn`` is a caller-supplied predicate so this function stays pure
    and testable without DB access.  The CLI resolves it via ``store.fetch_card``
    (same pattern as ``advisory.whattoplay``); tests pass a lambda.

    Cards not found by ``is_land_fn`` (i.e. unknown cards) are kept — the
    conservative default (unknown ≠ definitely land).  If ``is_land_fn`` raises,
    the exception propagates so callers discover DB issues early.
    """
    return {name: count for name, count in deck_cards.items() if not is_land_fn(name)}


def composition_adjusted_winrates(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    deck_archetype: str,
    deck_cards: dict[str, int],
    card_win_rates,  # CardWinRates — avoid import cycle; callers pass it in
    *,
    board: str = "main",
    max_nudge: float = _GRANULAR_MAX_NUDGE,
    scale: float = _GRANULAR_SCALE,
) -> dict[str, float]:
    """Compute per-matchup win-rates nudged by the deck's card-composition.

    For each field opponent ``opp``:
      1. Start from the archetype-level shrunk win-rate ``p_shrunk`` (from the
         matrix cell).  When there is no data (n=0), start from the imputation
         center used in ``_sample_S`` (mean vs known cells, or 0.5).
      2. For each card in ``deck_cards``, look up its ``card_value_matchup``
         lift vs ``opp``.  Only cards with ``tier in ("evolving", "established")``
         contribute (speculative lift is ignored).
      3. Aggregate lifts weighted by card count (normalised by total deck size),
         apply ``scale``, and clamp to ``[-max_nudge, +max_nudge]``.
      4. Add the nudge to the baseline win-rate, clamping the result to [0, 1].

    Returns
    -------
    dict[str, float]
        Per-opponent adjusted win-rate.  Mirror opponent is NOT included
        (mirror is fixed at 0.5 and is not meaningful to adjust).

    This is a PRESENCE-CORRELATIONAL heuristic (see ``GRANULAR_CAVEAT``).
    Caller must expose the caveat to end-users.
    """
    from legacy_engine.analytics.card_value import card_value_matchup

    field_archetypes = list(field.shares)
    wins, n, is_mirror, no_data_list = _row_winrate_inputs(matrix, deck_archetype, field_archetypes)

    # Baseline imputation center — mean vs known cells (replicates _sample_S logic)
    known_mask = (n > 0) & (~is_mirror)
    if known_mask.any():
        imputation_center = float((wins[known_mask] / n[known_mask]).mean())
    else:
        imputation_center = 0.5

    total_nonland_count = sum(deck_cards.values())
    if total_nonland_count == 0:
        total_nonland_count = 1  # safety: avoid division by zero

    adjusted: dict[str, float] = {}

    for i, opp in enumerate(field_archetypes):
        if is_mirror[i]:
            # Mirror: fixed 0.5 — skip
            continue

        # Baseline win-rate for this matchup
        if n[i] > 0:
            cell = matrix.cells.get((deck_archetype, opp))
            baseline_wr = cell.p_shrunk if (cell is not None and cell.p_shrunk is not None) else (wins[i] / n[i])
        else:
            baseline_wr = imputation_center

        # Aggregate card-lift signal
        lift_sum = 0.0
        for card_name, count in deck_cards.items():
            cv = card_value_matchup(card_win_rates, card_name, board, opp)
            if cv.tier not in ("evolving", "established"):
                # Speculative lift: ignore (not enough data to trust)
                continue
            lift_sum += cv.lift * count

        # Normalise by deck size, scale, clamp
        nudge = lift_sum / total_nonland_count * scale
        nudge = max(-max_nudge, min(max_nudge, nudge))

        adjusted_wr = max(0.0, min(1.0, baseline_wr + nudge))
        adjusted[opp] = adjusted_wr

    return adjusted


def positioning_score_granular(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    deck_archetype: str,
    deck_cards: dict[str, int],
    card_win_rates,  # CardWinRates
    *,
    board: str = "main",
    max_nudge: float = _GRANULAR_MAX_NUDGE,
    scale: float = _GRANULAR_SCALE,
    n_draws: int = _DEFAULT_DRAWS,
    gamma: float = _DIRICHLET_GAMMA,
    include_mirror: bool = True,
    robust: bool = False,
    restrict_to_covered: bool = True,
    keep_samples: bool = False,
    seed: int | None = None,
) -> GranularPositioningResult:
    """Opt-in list-granular positioning: archetype S + composition-adjusted S_granular.

    **DEFAULT OFF** — the standard ``positioning_score`` is byte-identical to
    the archetype-level baseline.  This function is the OPT-IN entry point.

    Returns a ``GranularPositioningResult`` with:
    - ``base``: the unmodified archetype-level ``PositioningResult`` (unchanged).
    - ``s_granular``: field-weighted WR after nudging per-matchup rates by the
      deck's card-composition deviation from the archetype baseline.
    - ``adjusted_winrates``: per-opponent adjusted WR dict.
    - ``caveat``: always ``GRANULAR_CAVEAT`` — consumers MUST display this.

    Parameters mirror ``positioning_score``; extra params:
    deck_cards
        ``{card_name: count}`` maindeck (non-land; lands carry no matchup lift).
    card_win_rates
        ``CardWinRates`` from ``compute_card_win_rates``.  Caller supplies it
        to keep this function pure and testable without DB access.
    board
        Board context for ``card_value_matchup`` lookup (default ``"main"``).
    max_nudge
        Maximum absolute per-matchup adjustment (default 0.05 = 5 pp).
    scale
        Global scale applied to lift aggregation (default 0.5).

    PRESENCE-CORRELATIONAL HEURISTIC — see ``GRANULAR_CAVEAT``.
    """
    # Compute the archetype-level base (byte-identical to calling positioning_score)
    base = positioning_score(
        matrix, field, deck_archetype,
        n_draws=n_draws, gamma=gamma,
        include_mirror=include_mirror, robust=robust,
        restrict_to_covered=restrict_to_covered,
        keep_samples=keep_samples, seed=seed,
    )

    # Compute composition-adjusted per-matchup win-rates
    adj_wrs = composition_adjusted_winrates(
        matrix, field, deck_archetype, deck_cards, card_win_rates,
        board=board, max_nudge=max_nudge, scale=scale,
    )

    # Compute S_granular: field-weighted average of adjusted win-rates.
    # Mirror matchup (self) contributes 0.5 at its field share when include_mirror=True.
    # Use point shares from the SCORING field (honors restrict_to_covered choice).
    scoring_field = field
    if base.restricted and base.excluded_archetypes:
        # Reuse the restricted scoring field so S_granular is comparable to base.s_mean
        covered = frozenset(field.shares) - base.excluded_archetypes
        scoring_field, _ = field.restrict_to(covered)

    scoring_shares = scoring_field.shares
    s_granular_num = 0.0
    s_granular_denom = 0.0

    for opp, share in scoring_shares.items():
        if opp == deck_archetype:
            # Mirror: always 0.5, included when include_mirror=True
            if include_mirror:
                s_granular_num += share * 0.5
                s_granular_denom += share
        else:
            wr = adj_wrs.get(opp)
            if wr is None:
                # Opponent not in field (shouldn't happen but be safe)
                continue
            s_granular_num += share * wr
            s_granular_denom += share

    s_granular = s_granular_num / s_granular_denom if s_granular_denom > 0 else float("nan")

    return GranularPositioningResult(
        base=base,
        s_granular=s_granular,
        adjusted_winrates=adj_wrs,
        caveat=GRANULAR_CAVEAT,
    )

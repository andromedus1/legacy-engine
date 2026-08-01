"""Superarchetype aggregation — the pure random-effects estimator over member tallies.

Method pinned by ``docs/briefs/superarchetype-aggregation.md`` §4 and the feature design
(``epic-superarchetype-layer-aggregation``):

- **Per-member effect** (Unit 1): continuity-corrected logit ``y_k = log((w+0.5)/(n-w+0.5))`` with
  variance ``v_k = 1/(w+0.5) + 1/(n-w+0.5)`` (Haldane-Anscombe; mandatory — 0-for-3 cells are
  routine and the raw logit is undefined there).
- **Between-member variance** (Unit 1): DerSimonian-Laird from Cochran's Q,
  ``tau^2 = max(0, (Q - (K-1)) / (Sum(w) - Sum(w^2)/Sum(w)))``; pooled with random-effects weights
  ``1/(v_k + tau^2)``. The estimator self-degrades: at ``tau^2 = 0`` it is plain inverse variance
  (close to size weighting), and as members disagree the weights flatten toward equality, defusing
  the one-dominant-member problem before any gate is consulted.
- **``n_eff``** (Unit 2): the only integration seam into the tier system — the display gate reads
  ``n_eff = 1/(Var(theta_hat) * p_bar(1-p_bar))`` clamped to ``<= Sum(n_k)``, never the raw pooled
  count. ``tau^2 = 0`` does NOT imply ``n_eff = Sum(n_k)``; see ``effective_n``.
- **Two gates + two guards** (Units 3-4): concentration (HHI / ``m_eff``, top-share cap),
  heterogeneity (I^2 bands mapped onto the project's three-state honesty vocabulary), a
  direction/spread guard, and a minimum-computability rule. A refused pool is a first-class output
  with a named reason and the member split — never a blended number, never a silent drop
  (honest-degrade-marker + divergence-as-diagnostic-surface).
- **Prior strength** (Unit 5): evidence-gated, NOT ``tau^2``-gated — the brief's §4.5 derivation is
  inverted (its own §6.4 shows ``tau^2 = 0`` at these member sizes mostly means "we cannot SEE
  spread") and is deliberately replaced here per the adversarial read.
- **Licensed imputation** (Unit 7): profile-level coherence EARNS a license where data exists;
  empty cells SPEND it, subject to a per-cell local veto. Assignee tallies never contribute
  (contribute-vs-receive, era addendum #2); freshness provenance rides through untouched.

**This module is DB-free and never imports duckdb** (not even transitively — which is why it does
not import ``analytics.matchup``): the caller supplies plain ``MemberTally`` rows and receives
typed results (objective-search-split). It also never computes windows; era discipline is the
caller's job and this kernel only carries the provenance through.

I^2 is ONE-SIDED evidence. A high value is a reliable stop signal; a low value is never a
certificate of exchangeability (Q has low power at these member counts and sizes). That caveat is
structured output — ``Heterogeneity.one_sided_note`` — not prose, so surfaces can render it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "Concentration",
    "MemberTally",
    "RandomEffects",
    "concentration",
    "dersimonian_laird",
    "effective_n",
]


# ---------------------------------------------------------------------------
# Calibration constants
#
# Values marked CALIBRATION are this project's choices, not sourced results — the brief is explicit
# about which of its numbers are measured, which are sourced, and which are author judgment, and the
# design requires that provenance to survive to the definition site. Named constants so
# recalibration after dogfooding is a one-line change; the audit output names them as calibrations.
# ---------------------------------------------------------------------------

_CONTINUITY = 0.5
"""Haldane-Anscombe continuity correction for 0-win and n-win members (calibration: the standard
0.5; mandatory — the raw logit is undefined at 0/n and n/n, and such cells are routine here)."""

_TAU2_MIN_MEMBERS = 2
"""Below this member count tau^2 / I^2 are not computable — ``i2`` is ``None`` and no caller may
read that as homogeneity (the one-sided rule)."""

_EPS = 1e-12


# ---------------------------------------------------------------------------
# Unit 1 — DerSimonian-Laird random-effects pool on continuity-corrected logits (pure)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemberTally:
    """One member archetype's tally against the subject — the kernel's only input type.

    ``intra_cluster`` flags a sibling tally (subject and member share a cluster): it counts toward
    the pool, flagged, per the epic decision — never silently excluded. ``definer`` implements the
    era addendum's contribute-vs-receive rule: pool contributions come from definers + curated
    members only; an assignee tally (``definer=False``) is excluded from every pool with a named
    reason (assignees receive imputation, they never contribute).

    Fails fast on empty tallies: ``n == 0`` carries no information yet would receive real weight
    under the continuity correction (``v = 4``), so constructing one is an author error, not data.
    """

    archetype: str
    wins: int
    n: int
    intra_cluster: bool = False
    definer: bool = True

    def __post_init__(self) -> None:
        if not self.archetype.strip():
            raise ValueError("MemberTally: archetype must be a non-empty name")
        if self.n < 1:
            raise ValueError(
                f"MemberTally: {self.archetype!r} has n={self.n} — a tally needs at least one "
                "match; do not pass empty members into a pool"
            )
        if not 0 <= self.wins <= self.n:
            raise ValueError(
                f"MemberTally: {self.archetype!r} has wins={self.wins} outside [0, n={self.n}]"
            )

    @property
    def p_hat(self) -> float:
        """Raw member rate ``wins/n`` (defined: ``n >= 1`` is enforced at construction)."""
        return self.wins / self.n


@dataclass(frozen=True)
class RandomEffects:
    """One DerSimonian-Laird fit: pooled logit, between-member variance, Q, and the RE weights.

    ``i2`` is ``None`` when not computable (fewer than ``_TAU2_MIN_MEMBERS`` members) — the caller
    must not read that as homogeneous. ``weights`` are the normalised random-effects weights
    ``1/(v_k + tau^2)`` in member order; they sum to 1 and flatten toward equality as ``tau^2``
    grows.
    """

    logit_mean: float
    tau2: float
    q: float
    df: int
    i2: float | None
    weights: tuple[float, ...]


def _logit_with_correction(wins: int, n: int) -> tuple[float, float]:
    """Continuity-corrected logit and its variance for one member cell.

    ``y = log((w+0.5)/(n-w+0.5))``, ``v = 1/(w+0.5) + 1/(n-w+0.5)``. Finite for every legal tally
    including 0-for-n and n-for-n — that is the point of the correction.
    """
    a = wins + _CONTINUITY
    b = (n - wins) + _CONTINUITY
    return math.log(a / b), 1.0 / a + 1.0 / b


def _logistic(x: float) -> float:
    """Numerically stable inverse logit (never overflows ``math.exp``)."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


def dersimonian_laird(members: Sequence[MemberTally]) -> RandomEffects:
    """DerSimonian-Laird random-effects pool over member tallies (brief §4.3, closed form).

    Fixed-effect weights ``w_k = 1/v_k`` give Cochran's ``Q = Sum(w_k (y_k - y_bar)^2)``;
    ``tau^2 = max(0, (Q - df) / (Sum(w) - Sum(w^2)/Sum(w)))`` (the DL moment estimator — the brief
    flags that its sources attest Q and the *definition* of tau^2, not this expression; the
    expression here is the standard DerSimonian-Laird 1986 form). Random-effects weights are
    ``1/(v_k + tau^2)``, renormalised.

    Degenerate branches are explicit, never NaN:

    - empty input fails fast (the orchestrator refuses empty pools with a named reason *before*
      calling this);
    - a single member returns ``tau2=0.0, df=0, i2=None`` — tau^2 is not computable and the caller
      must not read the zero as homogeneity;
    - ``Q = 0`` (all corrected logits identical) returns ``i2 = 0.0`` — the heterogeneity gate
      names the branch and the one-sided caveat still rides the result.
    """
    if not members:
        raise ValueError("dersimonian_laird: no member tallies supplied")

    stats = [_logit_with_correction(m.wins, m.n) for m in members]
    k = len(stats)
    if k < _TAU2_MIN_MEMBERS:
        y, _v = stats[0]
        return RandomEffects(logit_mean=y, tau2=0.0, q=0.0, df=0, i2=None, weights=(1.0,))

    w_fixed = [1.0 / v for _y, v in stats]
    sum_w = sum(w_fixed)
    y_bar = sum(w * y for (y, _v), w in zip(stats, w_fixed, strict=True)) / sum_w
    q = sum(w * (y - y_bar) ** 2 for (y, _v), w in zip(stats, w_fixed, strict=True))
    df = k - 1

    # Sum(w)^2 - Sum(w^2) = Sum_{i != j} w_i w_j > 0 for k >= 2 positive weights, so the DL
    # denominator is strictly positive here — no division-by-zero branch exists to hide.
    denominator = sum_w - sum(w * w for w in w_fixed) / sum_w
    tau2 = max(0.0, (q - df) / denominator)

    i2 = 0.0 if q <= _EPS else max(0.0, (q - df) / q)

    w_random = [1.0 / (v + tau2) for _y, v in stats]
    sum_w_random = sum(w_random)
    logit_mean = sum(w * y for (y, _v), w in zip(stats, w_random, strict=True)) / sum_w_random
    weights = tuple(w / sum_w_random for w in w_random)
    return RandomEffects(logit_mean=logit_mean, tau2=tau2, q=q, df=df, i2=i2, weights=weights)


# ---------------------------------------------------------------------------
# Unit 2 — n_eff: the only integration seam into the tier system (pure)
# ---------------------------------------------------------------------------


def _pooled_variance(members: Sequence[MemberTally], tau2: float) -> float:
    """Random-effects variance of the pooled logit: ``1 / Sum(1/(v_k + tau^2))``.

    Strictly positive for any non-empty member list (every ``v_k > 0`` by the continuity
    correction, ``tau^2 >= 0``), so no division-by-zero branch exists downstream.
    """
    if not members:
        raise ValueError("_pooled_variance: no member tallies supplied")
    return 1.0 / sum(
        1.0 / (_logit_with_correction(m.wins, m.n)[1] + tau2) for m in members
    )


def effective_n(members: Sequence[MemberTally], re: RandomEffects) -> float:
    """The effective sample behind the pooled cell: ``1/(Var(theta_hat) * p_bar(1-p_bar))``,
    clamped to ``<= Sum(n_k)``.

    The construction is the brief author's (§4.4), not a sourced formula, and its REAL behaviour —
    pinned by tests, per the adversarial read — is:

    - ``tau^2 = 0`` with all member rates equal: the continuity correction inflates every member's
      precision slightly above ``n_k * p(1-p)``, so the raw value overshoots and the clamp returns
      exactly ``Sum(n_k)`` — the honest full pooled sample.
    - ``tau^2 = 0`` with member rates differing: ``n_eff`` can sit STRICTLY below ``Sum(n_k)``
      (concavity of ``p(1-p)`` plus the inverse-variance weighting of ``p_bar``); the brief's
      "returns Sum(n_k) at tau^2 = 0" is false as written and is deliberately not asserted.
    - ``n_eff`` is non-increasing in ``tau^2`` and never exceeds ``Sum(n_k)`` — the error
      direction is always the safe one (never more generous than the raw pooled count).

    Feed the result to the existing ``tier_for_sample`` / display gate — no new gate machinery,
    just a more honest argument.
    """
    if not members:
        raise ValueError("effective_n: no member tallies supplied")
    variance = _pooled_variance(members, re.tau2)
    p_bar = _logistic(re.logit_mean)
    pq = p_bar * (1.0 - p_bar)
    total_n = float(sum(m.n for m in members))
    if pq <= 0.0:
        # Unreachable for real tallies (a finite logit keeps p_bar strictly inside (0, 1); pq can
        # only underflow to 0.0 at |logit| > ~745, i.e. astronomically large n). Named fallback so
        # no input can produce a ZeroDivisionError or an inf escaping into a cell.
        return total_n
    return min(1.0 / (variance * pq), total_n)


# ---------------------------------------------------------------------------
# Unit 3 — concentration gate: "is this really one member's record?" (pure)
# ---------------------------------------------------------------------------

_MEFF_MIN = 2.0
"""CALIBRATION (measured): minimum effective number of members ``m_eff = 1/HHI`` for a pooled cell
to be labelled a cluster read. Calibrated on the real corpus — median HHI across multi-member
poolable cells is exactly 0.500, so this gate bisects the measured population (46% exceed it). The
DOJ antitrust bands do NOT transfer (a perfectly even four-member cluster would be "highly
concentrated"); only the effective-number reading of HHI is borrowed."""

_MAX_MEMBER_SHARE = 0.60
"""CALIBRATION, NOT SOURCED and NOT separately measured (adversarial-read finding 3): no single
member may supply this share (or more) of the pooled n. Slack at K=2 (a 60/40 split already fails
``m_eff``) but BINDING at K>=3 — a 60/20/20 split passes ``m_eff`` at 2.27 and fails only this cap,
so the comparison is ``>=`` (a member at exactly 0.60 fails). Re-derive from the measured
member-share distribution after dogfooding."""

_CONCENTRATION_CALIBRATION_NOTE = (
    f"m_eff >= {_MEFF_MIN} is calibrated on the measured corpus (median HHI 0.500 bisects the "
    f"poolable population); the {_MAX_MEMBER_SHARE:.2f} top-share cap is a project calibration, "
    "not a sourced threshold — binding at K>=3, where 60/20/20 passes m_eff (2.27) and fails "
    "only the cap"
)


@dataclass(frozen=True)
class Concentration:
    """Concentration verdict for one pooled cell.

    A failing cell is still SERVED — coverage is the point of the epic — but carries ``label``
    (``dominated by <member> (...)``) that the surface must print (honest-degrade-marker).
    ``calibration_note`` names both thresholds' provenance so the audit output can say which is
    measured and which is a project calibration.
    """

    hhi: float
    m_eff: float
    top_share: float
    top_member: str
    passed: bool
    label: str | None
    calibration_note: str


def concentration(members: Sequence[MemberTally]) -> Concentration:
    """HHI over member shares of the pooled n, reported as ``m_eff = 1/HHI`` (brief §5).

    Passes only when ``m_eff >= _MEFF_MIN`` AND the top member's share is under
    ``_MAX_MEMBER_SHARE`` (a share of exactly 0.60 fails — the 60/20/20 case is the K>=3 shape the
    cap exists to catch). A single member concentrates fully (HHI 1.0) and always fails; the
    orchestrator refuses that case separately ("not a pool at all"). Ties for the top member break
    to the alphabetically first name, for determinism.
    """
    if not members:
        raise ValueError("concentration: no member tallies supplied")
    names = [m.archetype for m in members]
    if len(set(names)) != len(names):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise ValueError(
            f"concentration: duplicate member archetype(s) {duplicates} — a member appears at "
            "most once per pooled cell"
        )
    total = sum(m.n for m in members)
    shares = {m.archetype: m.n / total for m in members}
    hhi = sum(share**2 for share in shares.values())
    m_eff = 1.0 / hhi
    top_member = min(shares, key=lambda a: (-shares[a], a))
    top_share = shares[top_member]
    passed = m_eff >= _MEFF_MIN and top_share < _MAX_MEMBER_SHARE
    label = None if passed else f"dominated by {top_member} ({top_share:.0%} of pooled n)"
    return Concentration(
        hhi=hhi,
        m_eff=m_eff,
        top_share=top_share,
        top_member=top_member,
        passed=passed,
        label=label,
        calibration_note=_CONCENTRATION_CALIBRATION_NOTE,
    )

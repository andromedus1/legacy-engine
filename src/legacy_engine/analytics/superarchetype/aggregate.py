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
from statistics import median
from typing import TYPE_CHECKING

from legacy_engine.confidence import ConfidenceLevel, tier_for_sample

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "I2_ONE_SIDED_NOTE",
    "Concentration",
    "Heterogeneity",
    "MemberSplit",
    "MemberTally",
    "PooledCell",
    "PriorStrength",
    "RandomEffects",
    "aggregate_cluster_cell",
    "concentration",
    "dersimonian_laird",
    "effective_n",
    "heterogeneity",
    "prior_strength",
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


# ---------------------------------------------------------------------------
# Unit 4 — heterogeneity gate + direction/spread guard + minimum computability (pure)
# ---------------------------------------------------------------------------

_I2_FREE = 0.40
_I2_REFUSE = 0.75
"""Band EDGES from Cochrane's published interpretation guidance; the ACTIONS attached to them are
this project's (CALIBRATION), mapped onto the three-state honesty vocabulary: ``<= 0.40`` pool
freely, ``(0.40, 0.75]`` pool with a heterogeneous-pool note naming the spread, ``> 0.75`` refuse
the pooled number and emit the member split instead."""

_SPREAD_FORCE = 0.25
_SPREAD_MIN_N = 10
"""CALIBRATION (author's engineering rule, grounded in Cochrane's caveat that I^2 thresholds "can
be misleading"): among members with ``n >= _SPREAD_MIN_N``, an observed rate spread of
``>= _SPREAD_FORCE`` forces the refuse band regardless of I^2."""

_HET_MIN_MEMBERS = 2
_HET_MIN_MEMBER_N = 5
"""CALIBRATION (author's rule): a heterogeneity claim — in EITHER direction — requires at least
``_HET_MIN_MEMBERS`` members with ``n >= _HET_MIN_MEMBER_N`` each (a 1-match member carries no
usable variance). Below that the band is ``not-computable`` and the cell falls back to the
concentration labelling of the §5 gate."""

_VALID_HET_BANDS = frozenset({"free", "labelled", "refused", "not-computable"})
"""Closed vocabulary (closed-vocabulary-fail-fast-token)."""

I2_ONE_SIDED_NOTE = (
    "I^2 is one-sided evidence: a high value is a reliable stop signal, but a low value is never "
    "a certificate of exchangeability (Q has low power at these member counts and sizes) — a "
    "pooled cell that merely passes this gate is still a superarchetype-sourced estimate"
)
"""The honesty caveat that must reach the UI (brief §6.4). Rides on every ``Heterogeneity`` as
structured provenance — the epic flags this deliverable as able to fall between features, so it is
a field, not a docstring."""


@dataclass(frozen=True)
class Heterogeneity:
    """Heterogeneity verdict for one pooled cell.

    ``band`` is the closed vocabulary ``free | labelled | refused | not-computable`` (fail-fast on
    anything else). ``i2`` is ``None`` exactly when no heterogeneity claim may be made
    (``not-computable``) — reporting a number there would itself be a claim. ``spread`` is the raw
    member-rate range (max - min) across all members, ``None`` below two members. ``note`` carries
    the labelled band's ``heterogeneous pool`` message. ``one_sided_note`` always carries
    ``I2_ONE_SIDED_NOTE``. ``reason`` names the branch taken — including the degenerate ``Q = 0``
    case — so a surface can print the verdict verbatim.
    """

    band: str
    i2: float | None
    q: float
    spread: float | None
    note: str | None
    one_sided_note: str
    reason: str

    def __post_init__(self) -> None:
        if self.band not in _VALID_HET_BANDS:
            raise ValueError(
                f"Heterogeneity: band {self.band!r} must be one of {sorted(_VALID_HET_BANDS)}"
            )


def heterogeneity(members: Sequence[MemberTally], re: RandomEffects) -> Heterogeneity:
    """The heterogeneity gate (brief §6): I^2 bands + the two guards that do not depend on I^2.

    Decision order:

    1. **Minimum computability** — fewer than ``_HET_MIN_MEMBERS`` members with
       ``n >= _HET_MIN_MEMBER_N`` -> ``not-computable``, no homogeneity claim in either direction.
    2. **Direction/spread guard** — among members with ``n >= _SPREAD_MIN_N`` (needs at least two),
       a rate spread ``>= _SPREAD_FORCE`` forces ``refused`` regardless of I^2.
    3. **I^2 bands** — ``> _I2_REFUSE`` refused; ``(_I2_FREE, _I2_REFUSE]`` labelled with a
       ``heterogeneous pool`` note naming the spread; ``<= _I2_FREE`` free, with the ``Q = 0``
       degenerate branch named explicitly.

    The one-sided caveat rides every result: passing this gate is never a certificate.
    """
    if not members:
        raise ValueError("heterogeneity: no member tallies supplied")

    rates = [m.p_hat for m in members]
    spread = max(rates) - min(rates) if len(members) >= 2 else None

    counted = [m for m in members if m.n >= _HET_MIN_MEMBER_N]
    if len(counted) < _HET_MIN_MEMBERS:
        return Heterogeneity(
            band="not-computable",
            i2=None,
            q=re.q,
            spread=spread,
            note=None,
            one_sided_note=I2_ONE_SIDED_NOTE,
            reason=(
                f"heterogeneity not computable: {len(counted)} member(s) with "
                f"n >= {_HET_MIN_MEMBER_N} (need >= {_HET_MIN_MEMBERS}) — no homogeneity claim "
                "in either direction; the cell falls back to the concentration labelling"
            ),
        )

    guarded = [m for m in members if m.n >= _SPREAD_MIN_N]
    if len(guarded) >= 2:
        guarded_rates = [m.p_hat for m in guarded]
        guarded_spread = max(guarded_rates) - min(guarded_rates)
        if guarded_spread >= _SPREAD_FORCE:
            return Heterogeneity(
                band="refused",
                i2=re.i2,
                q=re.q,
                spread=spread,
                note=None,
                one_sided_note=I2_ONE_SIDED_NOTE,
                reason=(
                    f"direction/spread guard: member rates span {min(guarded_rates):.3f}-"
                    f"{max(guarded_rates):.3f} among members with n >= {_SPREAD_MIN_N} "
                    f"(spread {guarded_spread:.2f} >= {_SPREAD_FORCE}) — treated as "
                    f"I^2 > {_I2_REFUSE} regardless of I^2"
                ),
            )

    if re.i2 is None:
        # Defensive: a RandomEffects fitted on fewer members than were passed here. Making a
        # band claim from it would be unfounded — degrade with a name rather than guess.
        return Heterogeneity(
            band="not-computable",
            i2=None,
            q=re.q,
            spread=spread,
            note=None,
            one_sided_note=I2_ONE_SIDED_NOTE,
            reason=(
                "heterogeneity not computable: the supplied RandomEffects carries no I^2 "
                "(single-member fit) — no homogeneity claim in either direction"
            ),
        )

    i2 = re.i2
    if i2 > _I2_REFUSE:
        return Heterogeneity(
            band="refused",
            i2=i2,
            q=re.q,
            spread=spread,
            note=None,
            one_sided_note=I2_ONE_SIDED_NOTE,
            reason=(
                f"I^2 = {i2:.2f} > {_I2_REFUSE}: considerable heterogeneity — the pooled number "
                "is refused; serve the per-member split instead"
            ),
        )
    if i2 > _I2_FREE:
        note = (
            f"heterogeneous pool: member rates span {min(rates):.3f}-{max(rates):.3f} "
            f"(I^2 = {i2:.2f})"
        )
        return Heterogeneity(
            band="labelled",
            i2=i2,
            q=re.q,
            spread=spread,
            note=note,
            one_sided_note=I2_ONE_SIDED_NOTE,
            reason=(
                f"I^2 = {i2:.2f} in ({_I2_FREE}, {_I2_REFUSE}]: pooled, with the heterogeneous-"
                "pool note naming the spread (the random-effects n_eff already widens the gate)"
            ),
        )
    if re.q <= _EPS:
        reason = (
            "Q = 0.0 — no observed dispersion on the logit scale; I^2 = 0.00 is absence of "
            "evidence of spread, not evidence of absence (one-sided)"
        )
    else:
        reason = f"I^2 = {i2:.2f} <= {_I2_FREE}: pooled and displayed normally (one-sided — see note)"
    return Heterogeneity(
        band="free",
        i2=i2,
        q=re.q,
        spread=spread,
        note=None,
        one_sided_note=I2_ONE_SIDED_NOTE,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Unit 5 — evidence-gated prior strength (REPLACES the brief's inverted §4.5)
#
# The brief reads tau^2 = 0 as "coherent cluster" and awards the MAXIMUM strength (30). Its own
# §6.4 shows why that is inverted: at these member sizes tau^2 = 0 was measured on 58.7% of
# poolable cells and mostly means "we cannot SEE spread", not that spread is absent — so §4.5 as
# written hands maximum prior influence to the majority of cells on the WEAKEST evidence. Here
# strength is gated on EVIDENCE SUFFICIENCY (member count and per-member n) and then only REDUCED
# by observed dispersion; tau^2 = 0 alone never buys the maximum.
# ---------------------------------------------------------------------------

_PRIOR_MIN = 5.0
"""CALIBRATION, UNCALIBRATED FLOOR (the brief says so): an incoherent cluster still beats a bare
0.5 prior but barely nudges the cell. Validate against the existing ``SHRINK_STRENGTH = 15``
during dogfooding — see the feature file's implementation notes for the shipped check."""

_PRIOR_MAX = 30.0
"""Project-grounded ceiling: equals ``DISPLAY_GATE_N`` — a superarchetype prior may carry at most
one displayable cell's worth of evidence."""

_PRIOR_FULL_MEMBERS = 3
_PRIOR_FULL_N = 30
"""CALIBRATION: evidence sufficiency for full prior strength — at least this many members AND a
median per-member n at this floor (one displayable cell each) before the ceiling is reachable.
Evidence, NOT ``tau^2 == 0``, is what buys strength (adversarial-read finding 1)."""


@dataclass(frozen=True)
class PriorStrength:
    """Strength for using the pooled cluster cell as a Beta prior (two-level-empirical-bayes:
    this feature supplies a ``prior_mean`` and a ``strength``; ``beta_binomial_shrink_to`` stays
    untouched).

    ``ceiling`` is the evidence-gated maximum; ``moment_matched`` is the brief's §4.5 dispersion
    figure ``s = 1/(tau^2 * mu(1-mu)) - 1`` (``None`` at ``tau^2 = 0``, where it is unbounded and
    deliberately NOT read as coherence). ``strength`` is ``min(ceiling, moment_matched)`` clamped
    to ``[_PRIOR_MIN, _PRIOR_MAX]``. ``reason`` names the rule so the prior_source label can carry
    it verbatim.
    """

    strength: float
    ceiling: float
    moment_matched: float | None
    reason: str


def prior_strength(members: Sequence[MemberTally], re: RandomEffects) -> PriorStrength:
    """Evidence-gated prior strength: sufficiency sets the ceiling, dispersion only lowers it.

    - Evidence factor = ``min(1, K/_PRIOR_FULL_MEMBERS) * min(1, median(n_k)/_PRIOR_FULL_N)``;
      the ceiling interpolates ``[_PRIOR_MIN, _PRIOR_MAX]`` on it. Two tiny members land near the
      FLOOR even at ``tau^2 = 0`` — a zero computed from too few / too small members maps to LOW
      strength (the inversion fix).
    - ``tau^2 > 0`` moment-matches the brief's ``s`` and binds when it is below the ceiling, so
      strength is non-increasing in ``tau^2`` at fixed evidence and an incoherent cluster falls to
      the floor.
    """
    if not members:
        raise ValueError("prior_strength: no member tallies supplied")

    k = len(members)
    median_n = float(median(m.n for m in members))
    evidence = min(1.0, k / _PRIOR_FULL_MEMBERS) * min(1.0, median_n / _PRIOR_FULL_N)
    ceiling = _PRIOR_MIN + (_PRIOR_MAX - _PRIOR_MIN) * evidence

    mu = _logistic(re.logit_mean)
    pq = mu * (1.0 - mu)
    if re.tau2 > 0.0 and pq > 0.0:
        # Brief §4.5 moment match, tau^2 mapped to the probability scale:
        # tau2_p = tau2 * (mu(1-mu))^2, s = mu(1-mu)/tau2_p - 1 = 1/(tau2 * mu(1-mu)) - 1.
        moment_matched: float | None = 1.0 / (re.tau2 * pq) - 1.0
        raw = min(ceiling, moment_matched)
    else:
        # tau^2 = 0 is "spread not visible", never "coherent" — the moment match is unbounded
        # and the evidence-gated ceiling is the binding constraint.
        moment_matched = None
        raw = ceiling

    strength = min(_PRIOR_MAX, max(_PRIOR_MIN, raw))

    reason = (
        f"evidence-gated (replaces the brief's inverted §4.5): {k} member(s) toward "
        f"{_PRIOR_FULL_MEMBERS} and median n {median_n:.0f} toward {_PRIOR_FULL_N} set the "
        f"ceiling at {ceiling:.1f}; tau^2 = 0 is read as 'spread not visible', never as coherence"
    )
    if moment_matched is not None and moment_matched < ceiling:
        reason += (
            f"; dispersion moment-match s = {moment_matched:.1f} at tau^2 = {re.tau2:.3f} "
            "binds below the ceiling"
        )
    if raw < _PRIOR_MIN:
        reason += f"; clamped to the floor {_PRIOR_MIN:.0f} (floor is uncalibrated — brief §4.5)"

    return PriorStrength(
        strength=strength, ceiling=ceiling, moment_matched=moment_matched, reason=reason
    )


# ---------------------------------------------------------------------------
# Unit 6 — orchestrator: one typed pooled cell carrying its own gate verdicts (pure)
# ---------------------------------------------------------------------------

_Z_95 = 1.959963984540054
"""Two-sided 95% normal quantile — the project-wide CI convention (advisory-methods brief)."""

_CALIBRATION_AUDIT_NOTE = (
    "gate thresholds are project calibrations, not sourced values, except where the definition "
    "site says otherwise (see the constants block in analytics/superarchetype/aggregate.py)"
)


@dataclass(frozen=True)
class MemberSplit:
    """One member's raw record — the per-member split that stays reachable behind every pooled
    number (divergence-as-diagnostic-surface), and the whole display when the pool is refused."""

    archetype: str
    wins: int
    n: int
    p_hat: float
    tier: ConfidenceLevel
    intra_cluster: bool


@dataclass(frozen=True)
class PooledCell:
    """One subject-vs-cluster pooled cell, refusals included — the estimator's only output.

    **Refusal is a state, not an exception**: ``pooled_p is None`` exactly when the pool is
    refused, with ``refused_reason`` naming every gate that fired and ``member_split`` carrying
    what to render instead. A refused cell's diagnostics (``concentration``/``heterogeneity``/
    ``prior``/``n_eff``) are still populated where computable — ``None`` only when there was
    nothing to compute (empty input, no contributors).

    ``tier`` derives from ``round(n_eff)``, never from the raw pooled count. ``prior`` is inert on
    a refused cell (there is no ``pooled_p`` to anchor a Beta prior on). ``exclusions`` names
    every tally that did not contribute and why (self-mirror, assignee) — honest-degrade, never a
    silent drop. ``window_note`` and ``current_regime_share`` are freshness passthrough (era
    addendum #2): the kernel never computes windows and never drops them; a pool below the page's
    muting floor still returns, share attached, for the surface to mute.
    """

    subject: str
    cluster_id: str
    pooled_p: float | None
    ci_low: float | None
    ci_high: float | None
    n_eff: float
    tier: ConfidenceLevel
    concentration: Concentration | None
    heterogeneity: Heterogeneity | None
    prior: PriorStrength | None
    intra_cluster_n: int
    intra_cluster_share: float | None
    mirror_n: int
    refused_reason: str | None
    member_split: tuple[MemberSplit, ...]
    exclusions: tuple[str, ...]
    provenance: tuple[str, ...]
    window_note: str
    current_regime_share: float | None


def _split_of(members: Sequence[MemberTally]) -> tuple[MemberSplit, ...]:
    return tuple(
        MemberSplit(
            archetype=m.archetype,
            wins=m.wins,
            n=m.n,
            p_hat=m.p_hat,
            tier=tier_for_sample(m.n),
            intra_cluster=m.intra_cluster,
        )
        for m in sorted(members, key=lambda m: m.archetype)
    )


def _refused_cell(
    subject: str,
    cluster_id: str,
    reason: str,
    *,
    contributors: Sequence[MemberTally] = (),
    mirror_n: int = 0,
    exclusions: tuple[str, ...] = (),
    provenance: tuple[str, ...] = (),
    window_note: str = "",
    current_regime_share: float | None = None,
) -> PooledCell:
    """A refusal with everything computable still computed (single-member and gate refusals get
    diagnostics; structurally empty refusals get honest ``None``s)."""
    if contributors:
        re = dersimonian_laird(contributors)
        conc: Concentration | None = concentration(contributors)
        het: Heterogeneity | None = heterogeneity(contributors, re)
        prior: PriorStrength | None = prior_strength(contributors, re)
        n_eff = effective_n(contributors, re)
        intra_n = sum(m.n for m in contributors if m.intra_cluster)
        pool_n = sum(m.n for m in contributors)
        intra_share: float | None = (intra_n + mirror_n) / (pool_n + mirror_n)
    else:
        conc, het, prior = None, None, None
        n_eff = 0.0
        intra_n = 0
        intra_share = None
    return PooledCell(
        subject=subject,
        cluster_id=cluster_id,
        pooled_p=None,
        ci_low=None,
        ci_high=None,
        n_eff=n_eff,
        tier=tier_for_sample(round(n_eff)),
        concentration=conc,
        heterogeneity=het,
        prior=prior,
        intra_cluster_n=intra_n,
        intra_cluster_share=intra_share,
        mirror_n=mirror_n,
        refused_reason=reason,
        member_split=_split_of(contributors),
        exclusions=exclusions,
        provenance=(_CALIBRATION_AUDIT_NOTE, *provenance),
        window_note=window_note,
        current_regime_share=current_regime_share,
    )


def aggregate_cluster_cell(
    subject: str,
    cluster_id: str,
    members: Sequence[MemberTally],
    *,
    window_note: str = "",
    current_regime_share: float | None = None,
) -> PooledCell:
    """Pool one subject's per-member tallies against one cluster into a single honest cell.

    Pipeline: exclude the exact self-mirror (0.5 by symmetry, zero edge information — its n is
    reported as ``mirror_n``) and assignee tallies (contribute-vs-receive, era addendum #2), then
    fit DerSimonian-Laird over the contributors and attach the verdicts:

    - **empty / mirror-only / assignee-only / single contributor** -> refused with a named reason
      ("a cell with exactly one contributing member is not a pool at all");
    - **heterogeneity band ``refused``** (I^2 > 0.75 or the spread guard) -> refused; the reason
      names EVERY gate that fired, including a concentration failure, and ``member_split`` carries
      the per-member records to render instead — the naive pooled rate appears nowhere;
    - **otherwise** the cell serves ``pooled_p`` (the random-effects pooled rate, never the raw
      count pool), a logit-scale 95% CI from the random-effects variance, and
      ``tier_for_sample(round(n_eff))``; a concentration failure or a ``labelled``/
      ``not-computable`` band serves WITH its label in ``provenance`` (coverage is the point —
      honest-degrade, not suppression).

    ``window_note``/``current_regime_share`` ride through untouched; the kernel never computes
    windows (the caller supplies both from the adaptive build).
    """
    if not subject.strip():
        raise ValueError("aggregate_cluster_cell: subject must be a non-empty archetype name")
    if not cluster_id.strip():
        raise ValueError("aggregate_cluster_cell: cluster_id must be a non-empty id")

    passthrough = {"window_note": window_note, "current_regime_share": current_regime_share}
    if not members:
        return _refused_cell(
            subject, cluster_id, "no member tallies supplied — nothing to pool", **passthrough
        )

    exclusions: list[str] = []
    contributors: list[MemberTally] = []
    mirror_n = 0
    for m in members:
        if m.archetype == subject:
            mirror_n += m.n
            exclusions.append(
                f"self-mirror excluded from the rate: {subject} vs itself, n={m.n} "
                "(0.5 by symmetry — carries no edge information; n reported as mirror_n)"
            )
        elif not m.definer:
            exclusions.append(
                f"{m.archetype}: assignee tally excluded (n={m.n}) — assignees receive "
                "imputation but never contribute to pools (contribute-vs-receive, era addendum)"
            )
        else:
            contributors.append(m)

    if not contributors:
        return _refused_cell(
            subject,
            cluster_id,
            (
                f"no contributor tallies remain: {len(members)} tally(ies) supplied, all "
                "excluded (see exclusions) — definers and curated members are the only pool "
                "contributors"
            ),
            mirror_n=mirror_n,
            exclusions=tuple(exclusions),
            **passthrough,
        )

    if len(contributors) == 1:
        only = contributors[0]
        return _refused_cell(
            subject,
            cluster_id,
            (
                f"single-member cluster — not a pool at all; {only.archetype} is the only "
                "contributor (serve its own cell at cluster granularity)"
            ),
            contributors=contributors,
            mirror_n=mirror_n,
            exclusions=tuple(exclusions),
            **passthrough,
        )

    re = dersimonian_laird(contributors)
    conc = concentration(contributors)
    het = heterogeneity(contributors, re)
    prior = prior_strength(contributors, re)
    n_eff = effective_n(contributors, re)
    tier = tier_for_sample(round(n_eff))

    pool_n = sum(m.n for m in contributors)
    intra_n = sum(m.n for m in contributors if m.intra_cluster)
    intra_share = (intra_n + mirror_n) / (pool_n + mirror_n)

    provenance: list[str] = [_CALIBRATION_AUDIT_NOTE]
    if het.note:
        provenance.append(het.note)
    if not conc.passed and conc.label:
        provenance.append(f"served with concentration label: {conc.label}")

    if het.band == "refused":
        reasons = [f"heterogeneity gate: {het.reason}"]
        if not conc.passed:
            reasons.append(
                f"concentration gate also fails: {conc.label} "
                f"(m_eff {conc.m_eff:.2f}, top share {conc.top_share:.2f})"
            )
        return PooledCell(
            subject=subject,
            cluster_id=cluster_id,
            pooled_p=None,
            ci_low=None,
            ci_high=None,
            n_eff=n_eff,
            tier=tier,
            concentration=conc,
            heterogeneity=het,
            prior=prior,
            intra_cluster_n=intra_n,
            intra_cluster_share=intra_share,
            mirror_n=mirror_n,
            refused_reason="; ".join(reasons),
            member_split=_split_of(contributors),
            exclusions=tuple(exclusions),
            provenance=tuple(provenance),
            window_note=window_note,
            current_regime_share=current_regime_share,
        )

    variance = _pooled_variance(contributors, re.tau2)
    half_width = _Z_95 * math.sqrt(variance)
    pooled_p = _logistic(re.logit_mean)
    ci_low = _logistic(re.logit_mean - half_width)
    ci_high = _logistic(re.logit_mean + half_width)

    return PooledCell(
        subject=subject,
        cluster_id=cluster_id,
        pooled_p=pooled_p,
        ci_low=ci_low,
        ci_high=ci_high,
        n_eff=n_eff,
        tier=tier,
        concentration=conc,
        heterogeneity=het,
        prior=prior,
        intra_cluster_n=intra_n,
        intra_cluster_share=intra_share,
        mirror_n=mirror_n,
        refused_reason=None,
        member_split=_split_of(contributors),
        exclusions=tuple(exclusions),
        provenance=tuple(provenance),
        window_note=window_note,
        current_regime_share=current_regime_share,
    )

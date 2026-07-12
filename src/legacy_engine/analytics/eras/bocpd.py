"""Beta-Binomial Bayesian Online Change-Point Detection (Adams & MacKay 2007).

Maintains the exact posterior distribution over "run length" (buckets since the last
changepoint) as each new bucket's (successes, trials) pair arrives. For an exponential-family
likelihood the recursion reduces to tracking conjugate hyperparameters per run-length hypothesis
`[gundersen-bocpd]{6}` (see ``docs/briefs/change-point-detection.md`` §3) — here the Beta-Binomial
conjugate pair, the natural model for weekly share/win-rate proportions. No Python package ships
count/proportion BOCPD likelihoods (the commonly-cited reference implementation covers only
StudentT/MultivariateT), so this recursion is implemented in-project from the paper's message-
passing update, entirely in numpy/scipy with zero RNG.

At each step t:
  1. Score bucket t's (k successes of n trials) against every surviving run-length hypothesis'
     Beta(a, b) posterior via the exact Beta-Binomial predictive pmf.
  2. Growth: hypothesis r survives to r+1 with mass scaled by its predictive likelihood and
     ``(1 - hazard)``.
  3. Changepoint: all hypotheses' mass, weighted by predictive likelihood and ``hazard``, is
     pooled into a fresh run-length-0 hypothesis.
  4. Renormalize; record ``p_change`` and ``map_run_length`` BEFORE truncating negligible-mass
     hypotheses (truncation is a bookkeeping optimization only — it must never change a reported
     value, since it only ever discards mass below ``_MASS_TRUNCATION``).

The hazard is constant (memoryless): ``hazard = 1 / hazard_lambda``, i.e. a geometric prior on
run length with mean ``hazard_lambda`` buckets — the brief's ~4-disturbances/year starting point
(§3).

**Why ``p_change`` is the mass on run length <= 1, not literally run length == 0 (load-bearing
implementation note):** under any hazard that does not depend on run length (the "constant
hazard" this module implements), the posterior mass at EXACTLY run length 0 is a fixed algebraic
identity of the recursion — ``P(r_t=0 | x_1..t) == hazard``, for every ``t`` and every possible
observed series, independent of the data. Proof sketch: the changepoint mass is
``hazard * sum_r(P(r_{t-1}) * predictive_r(x_t))`` and the total growth mass is
``(1 - hazard) * sum_r(P(r_{t-1}) * predictive_r(x_t))`` — the SAME weighted sum in both cases
(hazard doesn't depend on ``r``, so it factors out), so after renormalizing they land in exactly
a ``hazard : (1 - hazard)`` split no matter what the predictives say (verified here by hand
derivation and empirically against a synthetic step series before shipping — literal run-length-0
mass sat at exactly ``1/hazard_lambda`` at every bucket, including right at an obvious 0.05->0.30
step). Run length 1 carries the actual signal instead: it is fed *only* by the previous step's
run-length-0 hypothesis, which uses the flat, freshly-reset Beta(``prior_a``, ``prior_b``)
predictive — for the ``Beta(1,1)`` default this predictive is the exact discrete-uniform
``1/(n+1)``, a constant independent of the data. Every OTHER surviving hypothesis is
data-informed and its predictive collapses when a real break occurs, shrinking the
renormalizing denominator while the run-length-1 numerator stays fixed — so ``P(r_t=1)`` spikes
exactly at a break and is flat otherwise. ``p_change[t]`` sums the run-length-0 and run-length-1
mass (the minimal, hazard-independent "a reset just happened, confirmed by one more bucket"
window) so it inherits that real, non-degenerate signal. A zero-trial bucket (``k=n=0``) scores
as an exact point-mass predictive of 1 for every hypothesis (the Beta-Binomial pmf formula needs
no special case here), so ``p_change`` at a zero-trial bucket is the exact closed-form constant
``hazard * (2 - hazard)`` regardless of history — never a spike.

**Cold-start note:** at bucket 0 the run-length hypothesis universe is only ``{0, 1}``, so
``p_change[0]`` is trivially 1.0 for ANY input — there is no prior history yet for the data to be
surprising relative to. This is an inherent, expected property of online change detection (a
burn-in bucket), not a defect; callers comparing "did bucket t stand out" should treat bucket 0
as uninformative.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import betaln, gammaln

# Posterior mass below this is discarded from the run-length hypothesis set after each step —
# a computational bound only (the brief's "truncate below 1e-9 mass"); it is applied AFTER the
# per-bucket p_change/map_run_length values are captured, so it can never alter a reported value.
_MASS_TRUNCATION: float = 1e-9


@dataclass(frozen=True)
class BocpdResult:
    """Per-bucket BOCPD output.

    ``p_change[t]`` is the posterior probability that bucket ``t`` is at or within one bucket of
    a fresh run (``P(run_length <= 1)`` — see the module docstring for why the literal
    run-length-0 mass alone is a degenerate, data-independent constant under constant hazard, and
    why the minimal 2-bucket window is the fix). ``map_run_length[t]`` is the run length with the
    largest posterior mass after observing bucket ``t``. Both arrays have length
    ``len(successes)``.
    """

    p_change: np.ndarray
    map_run_length: np.ndarray


def _log_beta_binomial_pmf(
    k: float, n: float, a: np.ndarray, b: np.ndarray
) -> np.ndarray:
    """log P(k successes of n trials | Beta(a, b)), vectorized over hypothesis arrays ``a``/``b``.

    ``C(n,k) * B(k+a, n-k+b) / B(a,b)`` in log space (``gammaln`` for the binomial coefficient,
    ``betaln`` for the Beta-function ratio) — the exact Beta-Binomial predictive, never a normal
    approximation (brief §2/§3: weekly counts are too small for count-chart normal approximations).
    ``n=k=0`` yields log-pmf 0 (pmf 1) with no special case: both terms cancel identically.
    """
    log_binom = gammaln(n + 1.0) - gammaln(k + 1.0) - gammaln(n - k + 1.0)
    log_beta_ratio = betaln(k + a, n - k + b) - betaln(a, b)
    return log_binom + log_beta_ratio


def beta_binomial_bocpd(
    successes: np.ndarray,
    trials: np.ndarray,
    *,
    hazard_lambda: float = 25.0,
    prior_a: float = 1.0,
    prior_b: float = 1.0,
) -> BocpdResult:
    """Run the Beta-Binomial BOCPD recursion over a bucket-ordered (successes, trials) series.

    ``successes``/``trials`` are per-bucket integer (or float) arrays of equal length — e.g. an
    entity's weekly deck count vs. the field, or match wins vs. matches played. ``hazard_lambda``
    is the constant hazard's mean run length in buckets (hazard = ``1 / hazard_lambda``);
    ``prior_a``/``prior_b`` are the Beta prior each fresh run length starts from.

    Deterministic, RNG-free, pure numpy/scipy. Zero-trial buckets are safe (see module docstring)
    and never spike ``p_change``.
    """
    successes = np.asarray(successes, dtype=float)
    trials = np.asarray(trials, dtype=float)
    if successes.shape != trials.shape:
        raise ValueError(
            f"beta_binomial_bocpd: successes.shape {successes.shape} != "
            f"trials.shape {trials.shape}"
        )
    n_buckets = successes.shape[0]

    p_change = np.zeros(n_buckets)
    map_run_length = np.zeros(n_buckets, dtype=int)
    if n_buckets == 0:
        return BocpdResult(p_change=p_change, map_run_length=map_run_length)

    hazard = 1.0 / hazard_lambda

    # State BEFORE observing bucket t: posterior over run-length hypotheses as of bucket t-1.
    # `run_lengths[i]` names the actual run length carried by slot i — tracked explicitly (not
    # inferred from array position) so truncation can never desynchronize "index" from "run
    # length" bookkeeping.
    probs = np.array([1.0])
    run_lengths = np.array([0])
    a_arr = np.array([prior_a])
    b_arr = np.array([prior_b])

    for t in range(n_buckets):
        k = successes[t]
        n = trials[t]

        log_pmf = _log_beta_binomial_pmf(k, n, a_arr, b_arr)
        pmf = np.exp(log_pmf)

        growth_mass = probs * pmf * (1.0 - hazard)
        cp_mass = float(np.sum(probs * pmf * hazard))

        new_probs = np.concatenate(([cp_mass], growth_mass))
        new_run_lengths = np.concatenate(([0], run_lengths + 1))
        new_a = np.concatenate(([prior_a], a_arr + k))
        new_b = np.concatenate(([prior_b], b_arr + (n - k)))

        total = float(new_probs.sum())
        if total <= 0.0 or not np.isfinite(total):
            raise FloatingPointError(
                f"beta_binomial_bocpd: non-finite/zero run-length normalizer at bucket {t} "
                f"(total={total}); check for negative/NaN successes or trials"
            )
        new_probs = new_probs / total

        # Capture reported values BEFORE truncation — truncation only ever discards mass below
        # _MASS_TRUNCATION, so it cannot change either the reset-window mass or the argmax.
        # See module docstring: mass at EXACTLY run length 0 is a degenerate constant under
        # constant hazard, so p_change sums run lengths {0, 1} — the minimal window that carries
        # the actual changepoint signal.
        p_change[t] = float(new_probs[new_run_lengths <= 1].sum())
        map_run_length[t] = int(new_run_lengths[int(np.argmax(new_probs))])

        keep = new_probs >= _MASS_TRUNCATION
        if not keep.any():
            keep[int(np.argmax(new_probs))] = True  # never fully empty the hypothesis set
        probs = new_probs[keep]
        run_lengths = new_run_lengths[keep]
        a_arr = new_a[keep]
        b_arr = new_b[keep]
        probs = probs / probs.sum()  # renormalize the (negligibly) truncated mass away

    return BocpdResult(p_change=p_change, map_run_length=map_run_length)

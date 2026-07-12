"""Tests for analytics.eras.bocpd — Beta-Binomial BOCPD recursion.

House style: deterministic synthetic series (``round(p * n)``, never sampled), TestX classes,
exact/pinned assertions where the math permits (zero-trial buckets have an exact closed form).
"""

from __future__ import annotations

import numpy as np
import pytest

from legacy_engine.analytics.eras.bocpd import BocpdResult, beta_binomial_bocpd

_HAZARD_LAMBDA = 25.0


def _step_series(n_buckets: int = 40, step_at: int = 20, n_trials: int = 40,
                  p_before: float = 0.05, p_after: float = 0.30):
    """Deterministic step series: successes = round(p * n) per bucket, no sampling."""
    trials = np.full(n_buckets, n_trials, dtype=float)
    successes = np.array([
        round(p_after * n_trials) if t >= step_at else round(p_before * n_trials)
        for t in range(n_buckets)
    ], dtype=float)
    return successes, trials


class TestStepDetection:
    # Bucket 0 is an inherent cold-start artifact for ANY online change detector: with no prior
    # history at all, the run-length hypothesis universe is just {0, 1}, so "P(run length <= 1)"
    # is trivially 1.0 regardless of data (there is nothing yet to be surprised relative to).
    # Real detection is only well-posed once a baseline has accumulated — every comparison below
    # excludes this single burn-in bucket, standard practice for online changepoint monitors.
    _BURN_IN = 1

    def test_step_peak_within_one_bucket_of_the_true_break(self):
        successes, trials = _step_series()
        result = beta_binomial_bocpd(successes, trials, hazard_lambda=_HAZARD_LAMBDA)

        peak = self._BURN_IN + int(np.argmax(result.p_change[self._BURN_IN:]))
        assert abs(peak - 20) <= 1

    def test_stationary_peak_is_well_below_the_step_peak(self):
        step_successes, step_trials = _step_series()
        step_result = beta_binomial_bocpd(step_successes, step_trials, hazard_lambda=_HAZARD_LAMBDA)
        step_peak = float(np.max(step_result.p_change[self._BURN_IN:]))

        n_buckets, n_trials, p = 40, 40, 0.15
        stationary_successes = np.full(n_buckets, round(p * n_trials), dtype=float)
        stationary_trials = np.full(n_buckets, n_trials, dtype=float)
        stationary_result = beta_binomial_bocpd(
            stationary_successes, stationary_trials, hazard_lambda=_HAZARD_LAMBDA
        )
        stationary_peak = float(np.max(stationary_result.p_change[self._BURN_IN:]))

        assert stationary_peak < 0.5 * step_peak


class TestZeroTrialBuckets:
    def test_zero_trial_buckets_are_finite_and_never_spike(self):
        # p=0.10 baseline with zero-trial buckets interleaved at fixed positions.
        n_buckets, n_trials, p = 20, 20, 0.10
        zero_idx = {3, 7, 11, 15, 19}
        successes = np.array(
            [0.0 if t in zero_idx else round(p * n_trials) for t in range(n_buckets)]
        )
        trials = np.array([0.0 if t in zero_idx else n_trials for t in range(n_buckets)])

        result = beta_binomial_bocpd(successes, trials, hazard_lambda=_HAZARD_LAMBDA)

        assert np.isfinite(result.p_change).all()
        assert np.isfinite(result.map_run_length).all()

        # Exact closed form: a zero-trial bucket's Beta-Binomial predictive is 1 for every
        # surviving hypothesis (n=k=0), so p_change (mass on run lengths {0, 1}) collapses to
        # exactly hazard * (2 - hazard), regardless of history — never a spike above baseline.
        hazard = 1.0 / _HAZARD_LAMBDA
        expected = hazard * (2.0 - hazard)
        for idx in zero_idx:
            assert result.p_change[idx] == pytest.approx(expected, abs=1e-9)

        non_zero_max = max(
            result.p_change[t] for t in range(n_buckets) if t not in zero_idx
        )
        for idx in zero_idx:
            assert result.p_change[idx] <= non_zero_max + 1e-9


class TestShapesAndDeterminism:
    def test_output_length_matches_input(self):
        successes, trials = _step_series()
        result = beta_binomial_bocpd(successes, trials)
        assert len(result.p_change) == len(successes)
        assert len(result.map_run_length) == len(successes)

    def test_empty_input(self):
        result = beta_binomial_bocpd(np.array([]), np.array([]))
        assert len(result.p_change) == 0
        assert len(result.map_run_length) == 0

    def test_result_is_frozen(self):
        result = beta_binomial_bocpd(np.array([1.0]), np.array([2.0]))
        assert isinstance(result, BocpdResult)
        with pytest.raises(AttributeError):
            result.p_change = np.array([0.0])

    def test_deterministic_given_same_input(self):
        successes, trials = _step_series()
        r1 = beta_binomial_bocpd(successes, trials)
        r2 = beta_binomial_bocpd(successes, trials)
        assert np.array_equal(r1.p_change, r2.p_change)
        assert np.array_equal(r1.map_run_length, r2.map_run_length)

    def test_mismatched_shapes_raises(self):
        with pytest.raises(ValueError):
            beta_binomial_bocpd(np.array([1.0, 2.0]), np.array([1.0]))

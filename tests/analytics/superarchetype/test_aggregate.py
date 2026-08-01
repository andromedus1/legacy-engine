"""Unit tests for the pure superarchetype aggregation kernel (no DuckDB anywhere in this module).

Fixtures come verbatim from the brief's §6.3 worked example (the headline Dimir Tempo pair) and
the 2026-07-31 real-corpus dilution measurements recorded in the feature file. Hermetic and
DB-free throughout — the estimator takes plain tallies.
"""

from __future__ import annotations

import math
from itertools import pairwise

import pytest

from legacy_engine.analytics.superarchetype.aggregate import (
    MemberTally,
    _logit_with_correction,
    dersimonian_laird,
)


class TestMemberTally:
    def test_rejects_empty_tally(self):
        with pytest.raises(ValueError, match="at least one match"):
            MemberTally(archetype="A", wins=0, n=0)

    def test_rejects_wins_out_of_range(self):
        with pytest.raises(ValueError, match="outside"):
            MemberTally(archetype="A", wins=5, n=3)
        with pytest.raises(ValueError, match="outside"):
            MemberTally(archetype="A", wins=-1, n=3)

    def test_rejects_blank_archetype(self):
        with pytest.raises(ValueError, match="non-empty"):
            MemberTally(archetype="  ", wins=1, n=2)

    def test_flags_default_to_contributing_non_sibling(self, make_tally):
        tally = make_tally("Aluren", wins=4, n=13)
        assert tally.intra_cluster is False
        assert tally.definer is True
        assert tally.p_hat == pytest.approx(4 / 13)


class TestLogitWithCorrection:
    def test_zero_win_member_is_finite(self):
        y, v = _logit_with_correction(0, 3)
        assert math.isfinite(y) and math.isfinite(v)
        assert y == pytest.approx(math.log(0.5 / 3.5))
        assert v == pytest.approx(1 / 0.5 + 1 / 3.5)

    def test_all_win_member_is_finite(self):
        y, v = _logit_with_correction(3, 3)
        assert math.isfinite(y) and math.isfinite(v)
        assert y == pytest.approx(-_logit_with_correction(0, 3)[0])

    def test_balanced_member_is_zero_logit(self):
        y, _v = _logit_with_correction(5, 10)
        assert y == pytest.approx(0.0)


class TestDersimonianLaird:
    def test_headline_fixture_reproduces_the_briefs_worked_i2(self, headline_pair):
        # Brief §6.3: I^2 = 0.89, Q = 9.1 on K = 2 — the epic's motivating pair.
        re = dersimonian_laird(headline_pair)
        assert re.i2 is not None
        assert round(re.i2, 2) == pytest.approx(0.89)
        assert re.q == pytest.approx(9.1, abs=0.05)
        assert re.df == 1
        assert re.tau2 > 0.0

    def test_extreme_members_yield_finite_pool(self, make_tally):
        re = dersimonian_laird([make_tally("A", wins=0, n=3), make_tally("B", wins=3, n=3)])
        assert math.isfinite(re.logit_mean)
        assert math.isfinite(re.tau2)
        assert math.isfinite(re.q)
        assert all(math.isfinite(w) for w in re.weights)

    def test_single_member_returns_no_i2_claim(self, make_tally):
        # tau2 is not computable below two members; the zero must never read as "homogeneous".
        re = dersimonian_laird([make_tally("A", wins=7, n=20)])
        assert re.tau2 == 0.0
        assert re.i2 is None
        assert re.df == 0
        assert re.weights == (1.0,)

    def test_empty_input_fails_fast(self):
        with pytest.raises(ValueError, match="no member tallies"):
            dersimonian_laird([])

    def test_q_zero_reports_i2_zero_not_nan(self, make_tally):
        # Two identical members: identical corrected logits, Q = 0 exactly.
        re = dersimonian_laird([make_tally("A", wins=5, n=10), make_tally("B", wins=5, n=10)])
        assert re.q == pytest.approx(0.0)
        assert re.i2 == 0.0
        assert re.tau2 == 0.0
        assert math.isfinite(re.logit_mean)

    def test_weights_sum_to_one(self, headline_pair):
        re = dersimonian_laird(headline_pair)
        assert sum(re.weights) == pytest.approx(1.0)

    def test_weights_match_the_re_formula(self, headline_pair):
        # weights_k = 1/(v_k + tau2), renormalised — pinned against the member variances.
        re = dersimonian_laird(headline_pair)
        raw = [1.0 / (_logit_with_correction(m.wins, m.n)[1] + re.tau2) for m in headline_pair]
        total = sum(raw)
        for got, expected in zip(re.weights, raw, strict=True):
            assert got == pytest.approx(expected / total)

    def test_weights_flatten_monotonically_as_tau2_grows(self, headline_pair):
        # The self-degrading property the estimator was chosen for: adding tau^2 to every
        # denominator compresses the large-member/small-member weight ratio toward 1.
        variances = [_logit_with_correction(m.wins, m.n)[1] for m in headline_pair]
        ratios = []
        for tau2 in (0.0, 0.25, 1.0, 4.0, 16.0):
            weights = [1.0 / (v + tau2) for v in variances]
            ratios.append(max(weights) / min(weights))
        assert all(a > b for a, b in pairwise(ratios))
        assert ratios[-1] == pytest.approx(1.0, abs=0.05)

    def test_pooled_logit_lies_between_member_logits(self, headline_pair):
        re = dersimonian_laird(headline_pair)
        logits = [_logit_with_correction(m.wins, m.n)[0] for m in headline_pair]
        assert min(logits) < re.logit_mean < max(logits)

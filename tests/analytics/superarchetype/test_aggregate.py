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
    concentration,
    dersimonian_laird,
    effective_n,
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


class TestEffectiveN:
    """Pins the REAL n_eff behaviour, not the brief's false identity (adversarial-read finding 2)."""

    def test_tau2_zero_and_equal_rates_returns_the_full_pooled_sample(self, make_tally):
        # Both members at 50%: tau2 = 0 and the clamp returns exactly Sum(n_k) = 30.
        members = [make_tally("A", wins=5, n=10), make_tally("B", wins=10, n=20)]
        re = dersimonian_laird(members)
        assert re.tau2 == 0.0
        assert effective_n(members, re) == pytest.approx(30.0)

    def test_tau2_zero_and_equal_rates_off_half_still_clamps_to_sum(self, make_tally):
        # Equal rates away from 0.5 (both 20%): corrected logits differ slightly but Q << df,
        # tau2 = 0, and the correction's precision inflation still overshoots -> clamp to 30.
        members = [make_tally("A", wins=2, n=10), make_tally("B", wins=4, n=20)]
        re = dersimonian_laird(members)
        assert re.tau2 == 0.0
        assert members[0].p_hat == members[1].p_hat
        assert effective_n(members, re) == pytest.approx(30.0)

    def test_tau2_zero_with_differing_rates_sits_strictly_below_sum(self, make_tally):
        # THE identity the brief asserts and the adversarial read refutes: tau2 = 0 does NOT
        # imply n_eff = Sum(n_k). Four members whose rates differ (7.5% vs 15%) inside sampling
        # noise (Q ~ 2.0 < df = 3, so DL clamps tau2 to zero) — concavity of p(1-p) plus the
        # inverse-variance weighting of p_bar pulls n_eff strictly below Sum(n) = 160.
        members = [
            make_tally("A", wins=3, n=40),
            make_tally("B", wins=3, n=40),
            make_tally("C", wins=6, n=40),
            make_tally("D", wins=6, n=40),
        ]
        re = dersimonian_laird(members)
        assert re.tau2 == 0.0
        assert len({m.p_hat for m in members}) > 1
        n_eff = effective_n(members, re)
        assert n_eff < 160.0
        assert n_eff == pytest.approx(156.5, abs=0.5)

    def test_headline_fixture_collapses_far_below_raw_pooled_n(self, headline_pair):
        # Brief §6.3: at I^2 = 0.89 the display gate refuses on n_eff before the gates are even
        # consulted — the raw pooled n = 42 becomes ~3 effective matches.
        re = dersimonian_laird(headline_pair)
        n_eff = effective_n(headline_pair, re)
        assert n_eff == pytest.approx(3.3, abs=0.1)

    def test_n_eff_is_non_increasing_in_tau2(self, headline_pair):
        import dataclasses

        re = dersimonian_laird(headline_pair)
        values = [
            effective_n(headline_pair, dataclasses.replace(re, tau2=tau2))
            for tau2 in (0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        ]
        assert all(a >= b for a, b in pairwise(values))
        assert values[0] > values[-1]

    @pytest.mark.parametrize(
        "tallies",
        [
            [("A", 0, 3), ("B", 3, 3)],
            [("A", 4, 13), ("B", 24, 29)],
            [("A", 5, 10), ("B", 10, 20), ("C", 1, 9)],
            [("A", 1, 2), ("B", 2, 3)],
            [("A", 30, 60), ("B", 45, 90), ("C", 10, 20), ("D", 2, 40)],
        ],
    )
    def test_n_eff_never_exceeds_raw_pooled_n(self, make_tally, tallies):
        members = [make_tally(a, wins=w, n=n) for a, w, n in tallies]
        re = dersimonian_laird(members)
        assert effective_n(members, re) <= sum(m.n for m in members)

    def test_empty_input_fails_fast(self, headline_pair):
        re = dersimonian_laird(headline_pair)
        with pytest.raises(ValueError, match="no member tallies"):
            effective_n([], re)


class TestConcentration:
    def test_headline_fixture_fails_the_gate(self, headline_pair):
        # Brief §6.3: HHI = 0.573, m_eff = 1.75 (< 2.0), top share 0.69 (>= 0.60 cap).
        result = concentration(headline_pair)
        assert result.hhi == pytest.approx(0.573, abs=1e-3)
        assert result.m_eff == pytest.approx(1.75, abs=5e-3)
        assert result.top_member == "Show and Tell"
        assert result.top_share == pytest.approx(29 / 42)
        assert result.passed is False

    def test_sixty_twenty_twenty_passes_m_eff_and_fails_only_the_cap(self, make_tally):
        # The K>=3 binding case (adversarial-read finding 3): m_eff = 2.27 clears the gate, so
        # only the (uncalibrated, project-owned) 0.60 top-share cap refuses it.
        members = [
            make_tally("Big", wins=15, n=30),
            make_tally("Small1", wins=5, n=10),
            make_tally("Small2", wins=5, n=10),
        ]
        result = concentration(members)
        assert result.m_eff == pytest.approx(2.27, abs=5e-3)
        assert result.m_eff >= 2.0
        assert result.top_share == pytest.approx(0.60)
        assert result.passed is False
        assert result.label is not None and "dominated by Big" in result.label

    def test_failing_cell_is_labelled_not_dropped(self, headline_pair):
        result = concentration(headline_pair)
        assert result.label == "dominated by Show and Tell (69% of pooled n)"
        assert "calibration" in result.calibration_note

    def test_even_split_passes_with_no_label(self, make_tally):
        members = [make_tally("A", wins=5, n=20), make_tally("B", wins=9, n=20)]
        result = concentration(members)
        assert result.passed is True
        assert result.label is None
        assert result.m_eff == pytest.approx(2.0)

    def test_single_member_concentrates_fully(self, make_tally):
        result = concentration([make_tally("Solo", wins=4, n=10)])
        assert result.hhi == pytest.approx(1.0)
        assert result.m_eff == pytest.approx(1.0)
        assert result.passed is False
        assert result.label == "dominated by Solo (100% of pooled n)"

    def test_empty_input_fails_fast(self):
        with pytest.raises(ValueError, match="no member tallies"):
            concentration([])

    def test_duplicate_member_names_fail_fast(self, make_tally):
        with pytest.raises(ValueError, match="duplicate member archetype"):
            concentration([make_tally("A", wins=1, n=5), make_tally("A", wins=2, n=5)])

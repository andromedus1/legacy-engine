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
    I2_ONE_SIDED_NOTE,
    Heterogeneity,
    MemberTally,
    _logit_with_correction,
    _pooled_ci,
    aggregate_cluster_cell,
    concentration,
    dersimonian_laird,
    effective_n,
    heterogeneity,
    imputation_license,
    impute_cell,
    prior_strength,
)
from legacy_engine.confidence import tier_for_sample


def _walk_values(obj):
    """Every leaf value reachable from a (nested) dataclass result, for honesty scans."""
    import dataclasses

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        obj = dataclasses.asdict(obj)
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _walk_values(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from _walk_values(value)
    else:
        yield obj


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

    def test_m_eff_arm_binds_alone_under_the_share_cap(self, make_tally):
        # 55/45: top share clears the 0.60 cap, so only m_eff = 1.98 < 2.0 refuses — this pins
        # the m_eff arm independently of the cap (the headline fixture trips both).
        members = [make_tally("A", wins=5, n=11), make_tally("B", wins=4, n=9)]
        result = concentration(members)
        assert result.top_share == pytest.approx(0.55)
        assert result.top_share < 0.60
        assert result.m_eff == pytest.approx(1.98, abs=5e-3)
        assert result.passed is False
        assert result.label == "dominated by A (55% of pooled n)"

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


class TestHeterogeneity:
    def test_headline_fixture_is_refused_on_i2(self, headline_pair):
        # I^2 = 0.89 > 0.75: the refuse band — but note the spread guard would ALSO fire here;
        # the guard is checked first, so pin the I^2 branch on a guard-silent variant below.
        re = dersimonian_laird(headline_pair)
        result = heterogeneity(headline_pair, re)
        assert result.band == "refused"
        assert result.one_sided_note == I2_ONE_SIDED_NOTE

    def test_i2_refuse_band_fires_without_the_spread_guard(self, make_tally):
        # Spread 0.24 stays under the 0.25 guard, but the members are big enough that the
        # disagreement is far beyond sampling error: I^2 > 0.75 refuses on its own.
        members = [make_tally("A", wins=76, n=200), make_tally("B", wins=124, n=200)]
        re = dersimonian_laird(members)
        result = heterogeneity(members, re)
        assert max(m.p_hat for m in members) - min(m.p_hat for m in members) < 0.25
        assert result.i2 is not None and result.i2 > 0.75
        assert result.band == "refused"
        assert "I^2" in result.reason and "refused" in result.reason

    def test_direction_guard_forces_refusal_even_at_low_i2(self, make_tally):
        # Two n>=10 members 0.30 vs 0.60: I^2 = 0.38 (would pool freely), but the spread guard
        # treats the cell as if I^2 exceeded 0.75 regardless.
        members = [make_tally("A", wins=3, n=10), make_tally("B", wins=6, n=10)]
        re = dersimonian_laird(members)
        assert re.i2 is not None and re.i2 <= 0.40
        result = heterogeneity(members, re)
        assert result.band == "refused"
        assert "direction/spread guard" in result.reason
        assert result.spread == pytest.approx(0.30)

    def test_spread_guard_ignores_thin_members(self, make_tally):
        # A wild 0% member at n=5 (computable, but under the guard's n>=10 floor) must not trip
        # the guard: among the n>=10 members the spread is 0.08, and the cell pools freely.
        members = [
            make_tally("A", wins=0, n=5),
            make_tally("B", wins=6, n=12),
            make_tally("C", wins=5, n=12),
        ]
        re = dersimonian_laird(members)
        result = heterogeneity(members, re)
        assert result.spread == pytest.approx(0.5)
        assert "direction/spread guard" not in result.reason
        assert result.band == "free"

    def test_below_computability_floor_makes_no_claim_either_way(self, make_tally):
        # One member at n>=5 is not enough: band is not "free" (that would be a homogeneity
        # claim), i2 is None, and the one-sided note still rides.
        members = [make_tally("A", wins=1, n=4), make_tally("B", wins=5, n=9)]
        re = dersimonian_laird(members)
        result = heterogeneity(members, re)
        assert result.band == "not-computable"
        assert result.band != "free"
        assert result.i2 is None
        assert result.one_sided_note == I2_ONE_SIDED_NOTE
        assert "no homogeneity claim in either direction" in result.reason

    def test_dilution_fixtures_from_the_real_corpus_do_not_pool_freely(self, make_tally):
        # Feature file, 2026-07-31 measurement: Cradle vs colorless prison 25.0% (n=4) ->
        # 46.2% (n=13) and Aluren vs same 100% (n=3) -> 50.0% (n=12) — large swings driven by
        # adding a differently-shaped member. Low-power I^2 would wave both through; the
        # computability floor is what stops the confident wrong number.
        cradle = [make_tally("Mystic Forge", wins=1, n=4), make_tally("Tron", wins=5, n=9)]
        aluren = [make_tally("Mystic Forge", wins=3, n=3), make_tally("Tron", wins=3, n=9)]
        for members in (cradle, aluren):
            result = heterogeneity(members, dersimonian_laird(members))
            assert result.band != "free"
            assert result.band == "not-computable"
            assert result.one_sided_note == I2_ONE_SIDED_NOTE

    def test_labelled_band_carries_a_note_naming_the_spread(self, make_tally):
        members = [
            make_tally("A", wins=2, n=9),
            make_tally("B", wins=7, n=14),
            make_tally("C", wins=7, n=9),
        ]
        re = dersimonian_laird(members)
        assert re.i2 is not None and 0.40 < re.i2 <= 0.75
        result = heterogeneity(members, re)
        assert result.band == "labelled"
        assert result.note is not None
        assert "heterogeneous pool" in result.note
        assert "0.222" in result.note and "0.778" in result.note

    def test_free_band_at_low_i2(self, make_tally):
        members = [make_tally("A", wins=5, n=12), make_tally("B", wins=6, n=13)]
        re = dersimonian_laird(members)
        result = heterogeneity(members, re)
        assert result.band == "free"
        assert result.note is None
        assert result.one_sided_note == I2_ONE_SIDED_NOTE

    def test_q_zero_branch_is_named_not_nan(self, make_tally):
        members = [make_tally("A", wins=5, n=10), make_tally("B", wins=5, n=10)]
        re = dersimonian_laird(members)
        result = heterogeneity(members, re)
        assert result.band == "free"
        assert "Q = 0.0" in result.reason
        assert "absence of evidence" in result.reason

    def test_band_vocabulary_fails_fast(self):
        with pytest.raises(ValueError, match="band 'bogus' must be one of"):
            Heterogeneity(
                band="bogus", i2=None, q=0.0, spread=None, note=None,
                one_sided_note=I2_ONE_SIDED_NOTE, reason="x",
            )

    def test_mismatched_single_member_fit_degrades_with_a_name(self, make_tally):
        # Defensive branch: two computable members but a RandomEffects fitted on one.
        members = [make_tally("A", wins=5, n=10), make_tally("B", wins=6, n=10)]
        re = dersimonian_laird(members[:1])
        result = heterogeneity(members, re)
        assert result.band == "not-computable"
        assert "carries no I^2" in result.reason

    def test_empty_input_fails_fast(self, headline_pair):
        re = dersimonian_laird(headline_pair)
        with pytest.raises(ValueError, match="no member tallies"):
            heterogeneity([], re)


class TestPriorStrength:
    """The adversarial read's behaviour-changing finding: strength is evidence-gated, never
    tau^2-gated. The brief's §4.5 would award these fixtures the exact opposite."""

    def test_two_tiny_members_with_tau2_zero_land_near_the_floor(self, make_tally):
        # Under the brief's §4.5 as written, tau2 = 0 -> s unbounded -> clamp at the MAXIMUM 30.
        # The evidence gate replaces that: two n=3 members carry almost no evidence, so the zero
        # (which only means "we cannot see spread") buys a ceiling barely above the floor.
        members = [make_tally("A", wins=1, n=3), make_tally("B", wins=1, n=3)]
        re = dersimonian_laird(members)
        assert re.tau2 == 0.0
        result = prior_strength(members, re)
        assert result.strength == pytest.approx(6.67, abs=0.05)
        assert result.strength < 10.0
        assert result.strength < 30.0
        assert "evidence-gated" in result.reason
        assert "never as coherence" in result.reason
        assert result.moment_matched is None

    def test_many_large_coherent_members_reach_the_ceiling(self, make_tally):
        members = [make_tally(name, wins=15, n=30) for name in ("A", "B", "C", "D")]
        re = dersimonian_laird(members)
        assert re.tau2 == 0.0
        result = prior_strength(members, re)
        assert result.strength == pytest.approx(30.0)
        assert result.ceiling == pytest.approx(30.0)

    def test_strength_is_non_increasing_in_tau2_at_fixed_evidence(self, make_tally):
        import dataclasses

        members = [make_tally(name, wins=15, n=30) for name in ("A", "B", "C", "D")]
        re = dersimonian_laird(members)
        strengths = [
            prior_strength(members, dataclasses.replace(re, tau2=tau2)).strength
            for tau2 in (0.0, 0.05, 0.2, 0.5, 1.0, 5.0, 50.0)
        ]
        assert all(a >= b for a, b in pairwise(strengths))
        assert strengths[0] == pytest.approx(30.0)
        assert strengths[-1] == pytest.approx(5.0)

    def test_incoherent_cluster_falls_to_the_floor(self, headline_pair):
        # Headline pair: tau2 = 2.24 -> moment-matched s = 0.86, clamped up to the floor.
        re = dersimonian_laird(headline_pair)
        result = prior_strength(headline_pair, re)
        assert result.strength == pytest.approx(5.0)
        assert result.moment_matched is not None
        assert result.moment_matched < 5.0
        assert "clamped to the floor" in result.reason
        assert "uncalibrated" in result.reason

    def test_dispersion_binds_below_the_ceiling_and_is_named(self, make_tally):
        import dataclasses

        members = [make_tally(name, wins=15, n=30) for name in ("A", "B", "C", "D")]
        re = dataclasses.replace(dersimonian_laird(members), tau2=0.2)
        result = prior_strength(members, re)
        # mu = 0.5 -> s = 1/(0.2 * 0.25) - 1 = 19: below the evidence ceiling of 30.
        assert result.moment_matched == pytest.approx(19.0)
        assert result.strength == pytest.approx(19.0)
        assert "binds below the ceiling" in result.reason

    def test_empty_input_fails_fast(self, headline_pair):
        re = dersimonian_laird(headline_pair)
        with pytest.raises(ValueError, match="no member tallies"):
            prior_strength([], re)


class TestAggregateClusterCell:
    def test_headline_fixture_is_refused_by_both_gates(self, headline_pair):
        # THE validation this feature exists for (brief §6.3): naive pooling gives a confident
        # 66.7% on n=42; both gates refuse it independently and the number appears nowhere.
        cell = aggregate_cluster_cell("Dimir Tempo", "sa-009", headline_pair)
        assert cell.pooled_p is None
        assert cell.ci_low is None and cell.ci_high is None
        assert cell.refused_reason is not None
        assert "heterogeneity gate" in cell.refused_reason
        assert "concentration gate also fails" in cell.refused_reason
        assert "dominated by Show and Tell" in cell.refused_reason
        # The member split is what the surface renders instead.
        assert [(s.archetype, s.wins, s.n) for s in cell.member_split] == [
            ("Aluren", 4, 13),
            ("Show and Tell", 24, 29),
        ]
        assert all(s.tier == "speculative" for s in cell.member_split)

    def test_headline_pooled_number_appears_nowhere_in_the_result(self, headline_pair):
        cell = aggregate_cluster_cell("Dimir Tempo", "sa-009", headline_pair)
        for value in _walk_values(cell):
            if isinstance(value, bool) or value is None:
                continue
            if isinstance(value, (int, float)):
                assert value != 42, "raw pooled n leaked into the result"
                assert abs(float(value) - 28 / 42) > 0.005, "pooled 66.7% leaked into the result"
                assert abs(float(value) - 66.7) > 0.05, "pooled 66.7 leaked into the result"
            elif isinstance(value, str):
                assert "66.7" not in value
                assert "0.667" not in value

    def test_headline_gate_diagnostics_ride_the_refused_cell(self, headline_pair):
        cell = aggregate_cluster_cell("Dimir Tempo", "sa-009", headline_pair)
        assert cell.concentration is not None and cell.concentration.passed is False
        assert cell.concentration.m_eff == pytest.approx(1.75, abs=5e-3)
        assert cell.heterogeneity is not None and cell.heterogeneity.band == "refused"
        assert cell.heterogeneity.one_sided_note == I2_ONE_SIDED_NOTE
        assert cell.n_eff == pytest.approx(3.3, abs=0.1)
        assert cell.tier == "speculative"
        assert any(
            line.startswith("refused with concentration label:")
            for line in cell.provenance
        )
        assert not any(
            line.startswith("served with concentration label:")
            for line in cell.provenance
        )

    def test_dilution_fixtures_serve_with_labels_never_a_free_pool(self, make_tally):
        # Real-corpus dilution cells (feature file, 2026-07-31): thin members of different shape
        # produce large swings; the cell must carry an honesty label, never pool freely.
        fixtures = {
            "Cradle Control": [
                make_tally("Mystic Forge", wins=1, n=4),
                make_tally("Tron", wins=5, n=9),
            ],
            "Aluren": [
                make_tally("Mystic Forge", wins=3, n=3),
                make_tally("Tron", wins=3, n=9),
            ],
        }
        for subject, members in fixtures.items():
            cell = aggregate_cluster_cell(subject, "sa-046", members)
            assert cell.heterogeneity is not None
            assert cell.heterogeneity.band != "free"
            assert cell.heterogeneity.band == "not-computable"
            assert cell.heterogeneity.one_sided_note == I2_ONE_SIDED_NOTE
            # Served (coverage is the point) but under the concentration label fallback.
            assert cell.pooled_p is not None
            assert any("dominated by Tron" in line for line in cell.provenance)
            assert any(
                line.startswith("served with heterogeneity label: heterogeneity not computable:")
                for line in cell.provenance
            )

    def test_tier_derives_from_n_eff_never_raw_pooled_n(self, make_tally):
        # Sum(n) = 32 would read "evolving"; the heterogeneous pool's n_eff ~ 12 reads
        # "speculative". The tier must follow n_eff.
        members = [
            make_tally("A", wins=2, n=9),
            make_tally("B", wins=7, n=14),
            make_tally("C", wins=7, n=9),
        ]
        cell = aggregate_cluster_cell("Subject", "sa-001", members)
        raw_n = sum(m.n for m in members)
        assert cell.pooled_p is not None  # labelled band — served, not refused
        assert cell.n_eff < raw_n
        assert cell.tier == tier_for_sample(round(cell.n_eff)) == "speculative"
        assert tier_for_sample(raw_n) == "evolving"
        assert cell.tier != tier_for_sample(raw_n)

    def test_served_cell_carries_re_pooled_rate_and_ci(self, make_tally):
        members = [make_tally("A", wins=5, n=12), make_tally("B", wins=6, n=13)]
        cell = aggregate_cluster_cell("Subject", "sa-001", members)
        assert cell.refused_reason is None
        assert cell.pooled_p is not None and 0.0 < cell.pooled_p < 1.0
        assert cell.ci_low is not None and cell.ci_high is not None
        assert 0.0 <= cell.ci_low < cell.pooled_p < cell.ci_high <= 1.0

    def test_self_mirror_is_excluded_and_reported_siblings_count_flagged(self, make_tally):
        # Subject vs its own 3-member cluster: the exact self-mirror leaves the rate (n reported),
        # sibling tallies count and stay flagged (epic decision: counted, never silently excluded).
        members = [
            make_tally("Aluren", wins=5, n=10),  # the exact self-mirror
            make_tally("Show and Tell", wins=11, n=19, intra_cluster=True),
            make_tally("Sneak Attack", wins=6, n=12, intra_cluster=True),
        ]
        cell = aggregate_cluster_cell("Aluren", "sa-009", members)
        assert cell.mirror_n == 10
        assert cell.intra_cluster_n == 31
        assert cell.intra_cluster_share == pytest.approx(1.0)
        assert any("self-mirror excluded" in line for line in cell.exclusions)
        assert {s.archetype for s in cell.member_split} == {"Show and Tell", "Sneak Attack"}
        assert all(s.intra_cluster for s in cell.member_split)
        assert cell.pooled_p is not None  # served: siblings are real matches vs the family

    def test_assignee_tallies_are_excluded_with_a_named_reason(self, make_tally):
        # Era addendum #2 rule 1 (contribute-vs-receive): assignees never contribute.
        members = [
            make_tally("Definer A", wins=5, n=12),
            make_tally("Definer B", wins=6, n=13),
            make_tally("Maverick", wins=9, n=10, definer=False),
        ]
        cell = aggregate_cluster_cell("Subject", "sa-004", members)
        assert {s.archetype for s in cell.member_split} == {"Definer A", "Definer B"}
        assert any(
            "Maverick: assignee tally excluded" in line and "contribute-vs-receive" in line
            for line in cell.exclusions
        )
        # The 90% assignee tally must not have polluted the pool.
        assert cell.pooled_p is not None and cell.pooled_p < 0.6

    def test_all_assignee_pool_is_refused_with_a_named_reason(self, make_tally):
        members = [
            make_tally("Maverick", wins=9, n=10, definer=False),
            make_tally("Elves", wins=2, n=10, definer=False),
        ]
        cell = aggregate_cluster_cell("Subject", "sa-004", members)
        assert cell.pooled_p is None
        assert cell.refused_reason is not None
        assert "no contributor tallies remain" in cell.refused_reason
        assert len(cell.exclusions) == 2

    def test_single_member_cluster_is_refused_not_a_pool(self, make_tally):
        cell = aggregate_cluster_cell("Subject", "sa-020", [make_tally("Solo", wins=20, n=40)])
        assert cell.pooled_p is None
        assert cell.refused_reason is not None
        assert "single-member cluster — not a pool at all" in cell.refused_reason
        assert "Solo" in cell.refused_reason
        # Diagnostics still ride: the caller can see what the one member looks like.
        assert cell.member_split[0].archetype == "Solo"
        assert cell.heterogeneity is not None and cell.heterogeneity.band == "not-computable"

    def test_empty_input_is_refused_with_a_named_reason(self):
        cell = aggregate_cluster_cell("Subject", "sa-001", [])
        assert cell.pooled_p is None
        assert cell.refused_reason == "no member tallies supplied — nothing to pool"
        assert cell.member_split == ()
        assert cell.concentration is None and cell.heterogeneity is None and cell.prior is None
        assert cell.n_eff == 0.0

    @pytest.mark.parametrize(
        "tallies",
        [
            [],
            [("Solo", 20, 40, True)],
            [("A", 0, 3, True), ("B", 3, 3, True)],
            [("Aluren", 4, 13, True), ("Show and Tell", 24, 29, True)],
            [("A", 5, 12, True), ("B", 6, 13, True), ("C", 9, 10, False)],
        ],
    )
    def test_no_nan_or_inf_ever_escapes(self, make_tally, tallies):
        members = [make_tally(a, wins=w, n=n, definer=d) for a, w, n, d in tallies]
        cell = aggregate_cluster_cell("Dimir Tempo", "sa-001", members)
        for value in _walk_values(cell):
            if isinstance(value, float):
                assert math.isfinite(value), f"non-finite {value!r} escaped into the cell"
        # And every refusal is named, never silent.
        if cell.pooled_p is None:
            assert cell.refused_reason

    def test_freshness_passthrough_rides_untouched(self, make_tally, headline_pair):
        # Era addendum #2 rule 3: the kernel never computes windows and never drops them. A pool
        # below the page's muting floor still returns, with the share attached for the surface.
        served = aggregate_cluster_cell(
            "Subject",
            "sa-001",
            [make_tally("A", wins=5, n=12), make_tally("B", wins=6, n=13)],
            window_note="2026-05-11..2026-07-31 (adaptive multi-split)",
            current_regime_share=0.12,
        )
        assert served.window_note == "2026-05-11..2026-07-31 (adaptive multi-split)"
        assert served.current_regime_share == 0.12
        assert served.pooled_p is not None
        refused = aggregate_cluster_cell(
            "Dimir Tempo",
            "sa-009",
            headline_pair,
            window_note="w",
            current_regime_share=0.05,
        )
        assert refused.window_note == "w"
        assert refused.current_regime_share == 0.05

    def test_blank_subject_or_cluster_fails_fast(self, headline_pair):
        with pytest.raises(ValueError, match="subject"):
            aggregate_cluster_cell(" ", "sa-001", headline_pair)
        with pytest.raises(ValueError, match="cluster_id"):
            aggregate_cluster_cell("Subject", "", headline_pair)

    def test_calibration_audit_note_always_rides(self, make_tally, headline_pair):
        for cell in (
            aggregate_cluster_cell("Dimir Tempo", "sa-009", headline_pair),
            aggregate_cluster_cell(
                "S", "sa-001", [make_tally("A", wins=5, n=12), make_tally("B", wins=6, n=13)]
            ),
        ):
            assert any("project calibrations" in line for line in cell.provenance)


@pytest.fixture
def sa024_profile(make_tally):
    """A sa-024-shaped coherent profile: 10 evaluable columns, per-column spread 0.05, zero
    significantly divergent (the white-creature family the epic's probe measured)."""
    return {
        f"Opponent {i:02d}": [
            make_tally("Death & Taxes", wins=9, n=20),
            make_tally("Energy", wins=10, n=20),
        ]
        for i in range(10)
    }


@pytest.fixture
def granted_license(sa024_profile):
    return imputation_license("sa-024", sa024_profile)


class TestImputationLicense:
    def test_coherent_profile_earns_the_license(self, granted_license):
        assert granted_license.granted is True
        assert granted_license.cols_evaluated == 10
        assert granted_license.sig_divergent_cols == 0
        assert granted_license.tau_profile == pytest.approx(0.05)
        assert "license granted" in granted_license.reason

    def test_comparability_desert_is_refused_with_a_named_reason(self, make_tally):
        # Only 2 of 4 columns have >= 2 members at n >= 12 — one big member + long tail is the
        # measured shape of 6 of 12 families. No evidence, no license.
        profile = {
            "Opp A": [make_tally("Big", wins=15, n=30), make_tally("Tail", wins=2, n=5)],
            "Opp B": [make_tally("Big", wins=10, n=25), make_tally("Tail", wins=1, n=4)],
            "Opp C": [make_tally("Big", wins=8, n=20), make_tally("Mid", wins=6, n=14)],
            "Opp D": [make_tally("Big", wins=9, n=18), make_tally("Mid", wins=7, n=15)],
        }
        license_ = imputation_license("sa-046", profile)
        assert license_.granted is False
        assert license_.cols_evaluated == 2
        assert license_.reason.startswith("insufficient shared columns (2 < 3)")

    def test_divergent_profile_is_refused_with_a_named_reason(self, make_tally):
        coherent = [make_tally("A", wins=9, n=20), make_tally("B", wins=10, n=20)]
        divergent = [make_tally("A", wins=2, n=20), make_tally("B", wins=18, n=20)]
        profile = {
            "Opp 1": divergent,
            "Opp 2": divergent,
            "Opp 3": coherent,
            "Opp 4": coherent,
        }
        license_ = imputation_license("sa-003", profile)
        assert license_.granted is False
        assert license_.sig_divergent_cols == 2
        assert "divergent profile" in license_.reason
        assert "0.50 > 0.25" in license_.reason

    def test_divergence_share_at_the_cap_still_grants(self, make_tally):
        coherent = [make_tally("A", wins=9, n=20), make_tally("B", wins=10, n=20)]
        divergent = [make_tally("A", wins=2, n=20), make_tally("B", wins=18, n=20)]
        profile = {
            "Opp 1": divergent,
            "Opp 2": coherent,
            "Opp 3": coherent,
            "Opp 4": coherent,
        }
        license_ = imputation_license("sa-024", profile)
        assert license_.granted is True
        assert license_.sig_divergent_cols == 1

    def test_assignee_tallies_never_qualify_a_column(self, make_tally):
        # Contribute-vs-receive applies to the license evidence too: three columns whose second
        # member is an assignee are not evaluable, so the license is refused.
        profile = {
            f"Opp {i}": [
                make_tally("Definer", wins=9, n=20),
                make_tally("Assignee", wins=10, n=20, definer=False),
            ]
            for i in range(4)
        }
        license_ = imputation_license("sa-024", profile)
        assert license_.granted is False
        assert license_.cols_evaluated == 0
        assert license_.tau_profile is None

    def test_all_extreme_column_is_agreement_not_nan(self, make_tally):
        # Total wins = 0 across qualifying members: the chi2 margin is degenerate; the named
        # branch reads it as agreement (identical extreme rates), never NaN or a crash.
        profile = {
            f"Opp {i}": [make_tally("A", wins=0, n=15), make_tally("B", wins=0, n=15)]
            for i in range(3)
        }
        license_ = imputation_license("sa-001", profile)
        assert license_.granted is True
        assert license_.sig_divergent_cols == 0
        assert license_.tau_profile == pytest.approx(0.0)

    def test_blank_cluster_id_fails_fast(self):
        with pytest.raises(ValueError, match="cluster_id"):
            imputation_license("  ", {})


class TestImputeCell:
    def test_granted_license_imputes_a_labeled_lean(self, granted_license, make_tally):
        siblings = [
            make_tally("Death & Taxes", wins=10, n=20),
            make_tally("Energy", wins=8, n=20),
        ]
        cell = impute_cell("Orzhov Midrange", "Delver", granted_license, siblings)
        assert cell.reason is None
        assert cell.p == pytest.approx(18 / 40)
        assert cell.pool_n == 40
        assert cell.siblings == ("Death & Taxes", "Energy")
        assert cell.license is granted_license

    def test_imputed_ci_is_strictly_wider_than_the_raw_pooled_ci(
        self, granted_license, make_tally
    ):
        siblings = [
            make_tally("Death & Taxes", wins=10, n=20),
            make_tally("Energy", wins=8, n=20),
        ]
        cell = impute_cell("Orzhov Midrange", "Delver", granted_license, siblings)
        base_low, base_high = _pooled_ci(18, 40)
        assert granted_license.tau_profile is not None and granted_license.tau_profile > 0
        assert cell.ci_low is not None and cell.ci_high is not None
        assert cell.ci_low < base_low
        assert cell.ci_high > base_high
        assert (cell.ci_high - cell.ci_low) - (base_high - base_low) == pytest.approx(
            granted_license.tau_profile
        )

    def test_no_license_refuses_with_the_licenses_reason(self, make_tally):
        desert = imputation_license(
            "sa-046",
            {"Only": [make_tally("Big", wins=15, n=30), make_tally("Mid", wins=7, n=15)]},
        )
        assert desert.granted is False
        cell = impute_cell(
            "Cradle Control",
            "Delver",
            desert,
            [make_tally("Big", wins=15, n=30), make_tally("Mid", wins=7, n=15)],
        )
        assert cell.p is None
        assert cell.reason is not None
        assert cell.reason.startswith("no license: insufficient shared columns")

    def test_local_veto_refuses_even_under_a_granted_license(
        self, granted_license, make_tally
    ):
        # THE per-cell honesty rule: this column's members measurably diverge (chi2 p << .05),
        # so it never imputes — the family-wide license does not override local evidence.
        siblings = [
            make_tally("Death & Taxes", wins=2, n=20),
            make_tally("Energy", wins=18, n=20),
        ]
        cell = impute_cell("Orzhov Midrange", "Doomsday", granted_license, siblings)
        assert granted_license.granted is True
        assert cell.p is None
        assert cell.reason is not None and cell.reason.startswith("local veto")
        assert "license or not" in cell.reason

    def test_intra_family_target_is_refused(self, granted_license, make_tally):
        siblings = [
            make_tally("Death & Taxes", wins=10, n=20),
            make_tally("Energy", wins=8, n=20),
        ]
        cell = impute_cell("Orzhov Midrange", "Energy", granted_license, siblings)
        assert cell.p is None
        assert cell.reason is not None and cell.reason.startswith("intra-family target")
        mirror = impute_cell("Orzhov Midrange", "Orzhov Midrange", granted_license, siblings)
        assert mirror.p is None
        assert mirror.reason is not None and "intra-family target" in mirror.reason

    def test_pool_too_thin_is_refused_by_the_floor(self, granted_license, make_tally):
        siblings = [
            make_tally("Death & Taxes", wins=6, n=12),
            make_tally("Energy", wins=5, n=12),
        ]
        cell = impute_cell("Orzhov Midrange", "Delver", granted_license, siblings)
        assert cell.p is None
        assert cell.reason == "pool too thin (24 < 25)"
        assert cell.pool_n == 24

    def test_assignee_sibling_is_excluded_with_a_named_reason(
        self, granted_license, make_tally
    ):
        # Era addendum: an assignee's 94% tally must not pollute the imputation pool.
        siblings = [
            make_tally("Death & Taxes", wins=10, n=20),
            make_tally("Energy", wins=8, n=20),
            make_tally("Maverick", wins=15, n=16, definer=False),
        ]
        cell = impute_cell("Orzhov Midrange", "Delver", granted_license, siblings)
        assert cell.p == pytest.approx(18 / 40)
        assert cell.pool_n == 40
        assert "Maverick" not in cell.siblings
        assert any(
            "Maverick: assignee tally excluded" in line and "contribute-vs-receive" in line
            for line in cell.exclusions
        )

    def test_all_assignee_siblings_refuse_with_a_named_reason(
        self, granted_license, make_tally
    ):
        siblings = [
            make_tally("Maverick", wins=15, n=16, definer=False),
            make_tally("Elves", wins=8, n=20, definer=False),
        ]
        cell = impute_cell("Orzhov Midrange", "Delver", granted_license, siblings)
        assert cell.p is None
        assert cell.reason is not None and cell.reason.startswith("no contributor siblings")
        assert len(cell.exclusions) == 2

    def test_subjects_own_tally_is_left_out(self, granted_license, make_tally):
        siblings = [
            make_tally("Orzhov Midrange", wins=12, n=14),  # the subject's own thin cell
            make_tally("Death & Taxes", wins=10, n=20),
            make_tally("Energy", wins=8, n=20),
        ]
        cell = impute_cell("Orzhov Midrange", "Delver", granted_license, siblings)
        assert cell.p == pytest.approx(18 / 40)
        assert any("leave-subject-out" in line for line in cell.exclusions)

    def test_freshness_passthrough_rides_untouched(self, granted_license, make_tally):
        siblings = [
            make_tally("Death & Taxes", wins=10, n=20),
            make_tally("Energy", wins=8, n=20),
        ]
        cell = impute_cell(
            "Orzhov Midrange",
            "Delver",
            granted_license,
            siblings,
            window_note="2026-05-11..2026-07-31 (adaptive)",
            current_regime_share=0.08,
        )
        assert cell.window_note == "2026-05-11..2026-07-31 (adaptive)"
        assert cell.current_regime_share == 0.08
        assert cell.p is not None  # a below-muting-floor share still returns, share attached

    def test_no_nan_or_inf_escapes_any_path(self, granted_license, make_tally):
        cells = [
            impute_cell("S", "Delver", granted_license, []),
            impute_cell(
                "S",
                "Delver",
                granted_license,
                [make_tally("A", wins=0, n=20), make_tally("B", wins=20, n=20)],
            ),
            impute_cell(
                "S",
                "Delver",
                granted_license,
                [make_tally("A", wins=0, n=20), make_tally("B", wins=0, n=20)],
            ),
        ]
        for cell in cells:
            for value in _walk_values(cell):
                if isinstance(value, float):
                    assert math.isfinite(value)
            if cell.p is None:
                assert cell.reason

    def test_blank_names_fail_fast(self, granted_license):
        with pytest.raises(ValueError, match="subject"):
            impute_cell(" ", "Delver", granted_license, [])
        with pytest.raises(ValueError, match="opponent"):
            impute_cell("S", "", granted_license, [])


class TestPooledCiParity:
    @pytest.mark.parametrize("n", [1, 5, 12, 25, 40, 41, 60, 150])
    def test_mirror_matches_matchup_wilson_or_jeffreys(self, n):
        # _pooled_ci reimplements matchup.wilson_or_jeffreys_ci (the import is refused: matchup
        # transitively imports duckdb). This parity pin is what stops the two from drifting.
        from legacy_engine.analytics.matchup import wilson_or_jeffreys_ci

        for wins in {0, 1, n // 2, n - 1, n}:
            ours = _pooled_ci(wins, n)
            theirs = wilson_or_jeffreys_ci(wins, n)
            assert ours[0] == pytest.approx(theirs[0], abs=1e-9)
            assert ours[1] == pytest.approx(theirs[1], abs=1e-9)

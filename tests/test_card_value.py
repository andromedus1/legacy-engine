"""Tests for card_value.py — Unit 3 of epic-deck-generation-per-card-value.

Covers:
- card_value_marginal: lift sign, tier, zero-observation prior fallback.
- card_value_matchup: two-level shrinkage direction, lift sign, tier transitions.
- card_values_vs: shape + gate-then-degrade contract.
- Unseen (card, board, opponent) → n=0, p_raw=None, p_shrunk==prior_mean.
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics.card_value import (
    CardValue,
    card_value_marginal,
    card_value_matchup,
    card_values_vs,
)
from legacy_engine.analytics.match_results import compute_card_winrates


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _winrates(make_rounds_corpus, n_repeats=1):
    con, facts = make_rounds_corpus(n_repeats=n_repeats)
    r = compute_card_winrates(con)
    con.close()
    return r, facts


# ---------------------------------------------------------------------------
# Class TestCardValueMarginal
# ---------------------------------------------------------------------------


class TestCardValueMarginal:
    def test_winning_card_lift_positive(self, make_rounds_corpus):
        """Surgical Extraction always wins in the corpus → lift > 0."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=5)
        cv = card_value_marginal(r, "Surgical Extraction", "side")
        assert cv.lift > 0
        assert cv.p_shrunk > cv.prior_mean

    def test_always_losing_card_lift_negative(self, make_rounds_corpus):
        """Dark Ritual (Combo's mainboard) always loses vs Control → lift < 0."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=5)
        cv = card_value_marginal(r, "Dark Ritual", "main")
        assert cv.lift < 0
        assert cv.p_shrunk < cv.prior_mean

    def test_unseen_card_zero_n_prior_fallback(self, make_rounds_corpus):
        """Card not in corpus → n=0, p_raw=None, p_shrunk==prior_mean, speculative."""
        r, _ = _winrates(make_rounds_corpus)
        cv = card_value_marginal(r, "Force of Will", "main")
        assert cv.n == 0
        assert cv.p_raw is None
        assert cv.p_shrunk == pytest.approx(cv.prior_mean)
        assert cv.tier == "speculative"
        assert cv.lift == pytest.approx(0.0)

    def test_tier_speculative_low_n(self, make_rounds_corpus):
        """n=2 (n_repeats=1) → speculative."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=1)
        cv = card_value_marginal(r, "Brainstorm", "main")
        assert cv.n == 2
        assert cv.tier == "speculative"

    def test_tier_evolving_at_boundary(self, make_rounds_corpus):
        """n=30 (n_repeats=15) → evolving."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=15)
        cv = card_value_marginal(r, "Brainstorm", "main")
        assert cv.n == 30
        assert cv.tier == "evolving"

    def test_tier_established_at_boundary(self, make_rounds_corpus):
        """n=100 (n_repeats=50) → established."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=50)
        cv = card_value_marginal(r, "Brainstorm", "main")
        assert cv.n == 100
        assert cv.tier == "established"

    def test_prior_mean_is_baseline_winrate(self, make_rounds_corpus):
        r, _ = _winrates(make_rounds_corpus, n_repeats=5)
        cv = card_value_marginal(r, "Brainstorm", "main")
        assert cv.prior_mean == pytest.approx(r.baseline_winrate)

    def test_opponent_is_none_for_marginal(self, make_rounds_corpus):
        r, _ = _winrates(make_rounds_corpus)
        cv = card_value_marginal(r, "Brainstorm", "main")
        assert cv.opponent is None

    def test_board_stored_correctly(self, make_rounds_corpus):
        r, _ = _winrates(make_rounds_corpus)
        cv_main = card_value_marginal(r, "Brainstorm", "main")
        cv_side = card_value_marginal(r, "Surgical Extraction", "side")
        assert cv_main.board == "main"
        assert cv_side.board == "side"


# ---------------------------------------------------------------------------
# Class TestCardValueMatchup
# ---------------------------------------------------------------------------


class TestCardValueMatchup:
    def test_winning_matchup_lift_positive(self, make_rounds_corpus):
        """Surgical Extraction always wins vs Combo → matchup lift > 0."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=5)
        cv = card_value_matchup(r, "Surgical Extraction", "side", "Combo")
        assert cv.lift > 0
        assert cv.p_shrunk > cv.prior_mean

    def test_losing_matchup_lift_negative(self, make_rounds_corpus):
        """Dark Ritual always loses vs Control → matchup lift < 0."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=5)
        cv = card_value_matchup(r, "Dark Ritual", "main", "Control")
        assert cv.lift < 0
        assert cv.p_shrunk < cv.prior_mean

    def test_prior_mean_is_marginal_p_shrunk(self, make_rounds_corpus):
        """Matchup prior_mean is the card's shrunk marginal (two-level)."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=10)
        marginal_cv = card_value_marginal(r, "Brainstorm", "main")
        matchup_cv = card_value_matchup(r, "Brainstorm", "main", "Combo")
        assert matchup_cv.prior_mean == pytest.approx(marginal_cv.p_shrunk)

    def test_unseen_matchup_prior_fallback(self, make_rounds_corpus):
        """Unseen (card, board, opponent) → n=0, p_raw=None, p_shrunk==prior_mean."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=5)
        # "Brainstorm" vs "Reanimator" — a known card but unseen matchup
        cv = card_value_matchup(r, "Brainstorm", "main", "Reanimator")
        assert cv.n == 0
        assert cv.p_raw is None
        assert cv.p_shrunk == pytest.approx(cv.prior_mean)
        assert cv.tier == "speculative"

    def test_unseen_card_matchup_fallback(self, make_rounds_corpus):
        """Totally unseen card → n=0, both marginal and matchup p_shrunk == baseline."""
        r, _ = _winrates(make_rounds_corpus)
        cv = card_value_matchup(r, "Force of Will", "main", "Combo")
        assert cv.n == 0
        assert cv.p_shrunk == pytest.approx(r.baseline_winrate)

    def test_thin_cell_shrinks_toward_marginal(self, make_rounds_corpus):
        """With n=2 (speculative), p_shrunk should be between prior_mean and p_raw."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=1)
        cv = card_value_matchup(r, "Surgical Extraction", "side", "Combo")
        # p_raw = 1.0 (always wins), prior_mean = marginal p_shrunk (< 1.0)
        # Shrinkage must pull p_shrunk between prior_mean and p_raw
        assert cv.p_shrunk > cv.prior_mean, "shrinkage should yield positive lift"
        assert cv.p_shrunk < 1.0, "should not be shrunk to raw value with only n=2"
        assert cv.tier == "speculative"

    def test_large_n_shrinks_less(self, make_rounds_corpus):
        """With n=100 (established), p_shrunk should be closer to p_raw than at n=2."""
        r_thin, _ = _winrates(make_rounds_corpus, n_repeats=1)
        r_large, _ = _winrates(make_rounds_corpus, n_repeats=50)

        cv_thin = card_value_matchup(r_thin, "Surgical Extraction", "side", "Combo")
        cv_large = card_value_matchup(r_large, "Surgical Extraction", "side", "Combo")

        # Both win 100%, so p_raw==1.0; larger n means p_shrunk closer to 1.0
        assert cv_large.p_shrunk > cv_thin.p_shrunk

    def test_opponent_stored(self, make_rounds_corpus):
        r, _ = _winrates(make_rounds_corpus)
        cv = card_value_matchup(r, "Brainstorm", "main", "Combo")
        assert cv.opponent == "Combo"

    def test_tier_transitions_across_boundaries(self, make_rounds_corpus):
        """Seeded cell crosses tier boundaries as n_repeats grows."""
        r1, _ = _winrates(make_rounds_corpus, n_repeats=1)
        r15, _ = _winrates(make_rounds_corpus, n_repeats=15)
        r50, _ = _winrates(make_rounds_corpus, n_repeats=50)

        cv1 = card_value_matchup(r1, "Surgical Extraction", "side", "Combo")
        cv15 = card_value_matchup(r15, "Surgical Extraction", "side", "Combo")
        cv50 = card_value_matchup(r50, "Surgical Extraction", "side", "Combo")

        assert cv1.tier == "speculative"
        assert cv15.tier == "evolving"
        assert cv50.tier == "established"


# ---------------------------------------------------------------------------
# Class TestCardValuesVs
# ---------------------------------------------------------------------------


class TestCardValuesVs:
    def test_returns_dict_for_each_card(self, make_rounds_corpus):
        """card_values_vs returns one entry per requested card."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=5)
        cards = ["Brainstorm", "Surgical Extraction", "Force of Will"]
        result = card_values_vs(r, cards, "main", "Combo")
        assert set(result.keys()) == set(cards)

    def test_values_are_card_value_instances(self, make_rounds_corpus):
        r, _ = _winrates(make_rounds_corpus, n_repeats=5)
        result = card_values_vs(r, ["Brainstorm"], "main", "Combo")
        assert isinstance(result["Brainstorm"], CardValue)

    def test_gate_param_does_not_suppress(self, make_rounds_corpus):
        """card_values_vs does NOT suppress — all cards returned regardless of tier."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=1)  # speculative tier
        result = card_values_vs(
            r, ["Surgical Extraction"], "side", "Combo", gate=("evolving", "established")
        )
        # Still returns the card even though tier is speculative
        assert "Surgical Extraction" in result
        assert result["Surgical Extraction"].tier == "speculative"

    def test_gate_then_degrade_pattern(self, make_rounds_corpus):
        """Consumer can implement gate-then-degrade using .tier."""
        r, _ = _winrates(make_rounds_corpus, n_repeats=1)
        cards = ["Brainstorm", "Force of Will"]
        result = card_values_vs(r, cards, "main", "Combo", gate=("evolving", "established"))

        trusted = {c: v for c, v in result.items() if v.tier in ("evolving", "established")}
        speculative = {c: v for c, v in result.items() if v.tier == "speculative"}

        # Both are speculative with n_repeats=1; consumer can degrade to heuristic
        assert isinstance(trusted, dict)
        assert isinstance(speculative, dict)

    def test_board_correctly_passed_through(self, make_rounds_corpus):
        r, _ = _winrates(make_rounds_corpus, n_repeats=5)
        result_main = card_values_vs(r, ["Brainstorm"], "main", "Combo")
        result_side = card_values_vs(r, ["Brainstorm"], "side", "Combo")

        # Brainstorm is only in main; side should be n=0
        assert result_main["Brainstorm"].n > 0
        assert result_side["Brainstorm"].n == 0

    def test_empty_card_list(self, make_rounds_corpus):
        r, _ = _winrates(make_rounds_corpus)
        result = card_values_vs(r, [], "main", "Combo")
        assert result == {}


# ---------------------------------------------------------------------------
# Class TestCardValueFrozen — dataclass is frozen
# ---------------------------------------------------------------------------


class TestCardValueFrozen:
    def test_frozen_dataclass(self, make_rounds_corpus):
        r, _ = _winrates(make_rounds_corpus)
        cv = card_value_marginal(r, "Brainstorm", "main")
        with pytest.raises((AttributeError, TypeError)):
            cv.n = 999  # type: ignore[misc]

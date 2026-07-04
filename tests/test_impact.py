"""Tests for advisory/impact.py (Units B1 + B2 of feature-sb-field-weighted-scorer).

All inputs are hand-built (no DB) — objective-search-split: the module under test is pure,
so these tests exercise it directly with fixture-built HoserCard/Linchpin instances.
"""

from __future__ import annotations

import math

import pytest

from legacy_engine.advisory.impact import (
    _BO3_CARDS_SEEN,
    _CENTRALITY_BASELINE,
    _SYMMETRY_FLOOR,
    ImpactBreakdown,
    castability_factor,
    centrality_factor,
    draw_probability,
    hoser_capabilities,
    impact,
    symmetry_factor,
)


# ---------------------------------------------------------------------------
# hoser_capabilities (Unit B2)
# ---------------------------------------------------------------------------


class TestHoserCapabilities:
    def test_known_catalog_card_maps_to_capability(self, make_hoser):
        null_rod = make_hoser(name="Null Rod", attacks=frozenset({"ramp"}))
        assert hoser_capabilities(null_rod) == frozenset({"artifact-ability-lock"})

    def test_case_insensitive_name_match(self, make_hoser):
        hoser = make_hoser(name="null ROD")
        assert hoser_capabilities(hoser) == frozenset({"artifact-ability-lock"})

    def test_unknown_card_returns_empty(self, make_hoser):
        hoser = make_hoser(name="Some Uncataloged Card")
        assert hoser_capabilities(hoser) == frozenset()

    def test_edict_effect_gets_no_capability_credit(self, make_hoser):
        # Sheoldred's Edict: opponent chooses the sacrifice, so it cannot reliably be
        # credited with answering one SPECIFIC named linchpin.
        hoser = make_hoser(name="Sheoldred's Edict")
        assert hoser_capabilities(hoser) == frozenset()

    def test_hand_disruption_gets_no_capability_credit(self, make_hoser):
        hoser = make_hoser(name="Thoughtseize")
        assert hoser_capabilities(hoser) == frozenset()


# ---------------------------------------------------------------------------
# centrality_factor
# ---------------------------------------------------------------------------


class TestCentralityFactor:
    def test_linchpin_hit_returns_that_linchpins_centrality(self, make_hoser, make_linchpin):
        hoser = make_hoser(name="Null Rod")  # -> artifact-ability-lock
        linchpin = make_linchpin(
            archetype="Painter",
            name="Grindstone",
            centrality=1.0,
            neutralized_by=frozenset({"artifact-ability-lock", "artifact-removal"}),
        )
        assert centrality_factor(hoser, "Painter", [linchpin]) == 1.0

    def test_no_hit_returns_baseline(self, make_hoser, make_linchpin):
        hoser = make_hoser(name="Null Rod")  # -> artifact-ability-lock
        linchpin = make_linchpin(
            archetype="Reanimator",
            name="Reanimate",
            centrality=1.0,
            neutralized_by=frozenset({"exile-graveyard", "counter-on-cast"}),
        )
        assert centrality_factor(hoser, "Reanimator", [linchpin]) == _CENTRALITY_BASELINE

    def test_uncapable_hoser_returns_baseline(self, make_hoser, make_linchpin):
        # A hoser with no recognized capability (e.g. hand disruption) never confirms a hit.
        hoser = make_hoser(name="Thoughtseize")
        linchpin = make_linchpin(neutralized_by=frozenset({"counter-on-cast"}))
        assert centrality_factor(hoser, "Test Archetype", [linchpin]) == _CENTRALITY_BASELINE

    def test_no_linchpins_returns_baseline(self, make_hoser):
        hoser = make_hoser(name="Null Rod")
        assert centrality_factor(hoser, "Painter", []) == _CENTRALITY_BASELINE

    def test_max_centrality_among_multiple_hits(self, make_hoser, make_linchpin):
        hoser = make_hoser(name="Force of Will")  # -> counter-on-cast
        weak = make_linchpin(
            archetype="Storm", name="Tendrils", centrality=0.4,
            neutralized_by=frozenset({"counter-on-cast"}),
        )
        strong = make_linchpin(
            archetype="Storm", name="Ad Nauseam", centrality=0.9,
            neutralized_by=frozenset({"counter-on-cast"}),
        )
        assert centrality_factor(hoser, "Storm", [weak, strong]) == 0.9

    def test_other_archetype_linchpins_ignored(self, make_hoser, make_linchpin):
        hoser = make_hoser(name="Null Rod")
        other = make_linchpin(
            archetype="Painter", name="Grindstone", centrality=1.0,
            neutralized_by=frozenset({"artifact-ability-lock"}),
        )
        # Querying centrality for a DIFFERENT opponent archetype should not pick up the hit.
        assert centrality_factor(hoser, "Eldrazi", [other]) == _CENTRALITY_BASELINE


# ---------------------------------------------------------------------------
# symmetry_factor
# ---------------------------------------------------------------------------


class TestSymmetryFactor:
    def test_asymmetric_always_full_value(self, make_hoser):
        hoser = make_hoser(symmetry="asymmetric", attacks=frozenset({"graveyard-recursion"}))
        assert symmetry_factor(hoser, frozenset({"graveyard-recursion"})) == 1.0

    def test_symmetric_shared_axis_hits_floor(self, make_hoser):
        # Grafdigger's Cage-shaped case: symmetric graveyard hate AND my deck itself does
        # graveyard-recursion -> self-hosing -> floor.
        hoser = make_hoser(
            name="Grafdigger's Cage",
            symmetry="symmetric",
            attacks=frozenset({"graveyard-recursion"}),
        )
        my_tags = frozenset({"graveyard-recursion", "plays-blue"})
        assert symmetry_factor(hoser, my_tags) == _SYMMETRY_FLOOR

    def test_symmetric_not_exposed_near_full_value(self, make_hoser):
        # Symmetric card, but my deck isn't exposed on that axis -> not a self-hoser.
        hoser = make_hoser(
            name="Toxic Deluge",
            symmetry="symmetric",
            attacks=frozenset({"creature-based"}),
        )
        my_tags = frozenset({"graveyard-recursion", "plays-blue"})
        assert symmetry_factor(hoser, my_tags) == 1.0

    def test_symmetric_empty_vulnerability_tags(self, make_hoser):
        hoser = make_hoser(symmetry="symmetric", attacks=frozenset({"ramp"}))
        assert symmetry_factor(hoser, frozenset()) == 1.0

    def test_symmetric_shared_color_axis_hits_floor(self, make_hoser):
        """gate-tests-symmetry-color-axis: the shared-axis floor was previously only ever
        exercised via graveyard-recursion (Grafdigger's Cage-shaped case above). Pyroblast-shaped
        case: a symmetric plays-<color> hoser boarded in by a deck that itself plays that same
        color is self-hosing on the color axis, same as any other shared tag."""
        hoser = make_hoser(
            name="Pyroblast", symmetry="symmetric", attacks=frozenset({"plays-blue"}),
        )
        my_tags = frozenset({"plays-blue", "combo"})
        assert symmetry_factor(hoser, my_tags) == _SYMMETRY_FLOOR

    def test_symmetric_color_axis_not_shared_stays_full_value(self, make_hoser):
        """Complement of the above: my deck isn't exposed on the SAME color axis this
        symmetric hoser hits -> not self-hosing -> full value."""
        hoser = make_hoser(
            name="Pyroblast", symmetry="symmetric", attacks=frozenset({"plays-blue"}),
        )
        my_tags = frozenset({"plays-red", "combo"})
        assert symmetry_factor(hoser, my_tags) == 1.0


# ---------------------------------------------------------------------------
# castability_factor
# ---------------------------------------------------------------------------


class TestCastabilityFactor:
    def test_subset_colors_castable(self, make_hoser):
        hoser = make_hoser(colors=frozenset({"B"}))
        assert castability_factor(hoser, frozenset({"U", "B"}), "Painter") == 1.0

    def test_off_color_non_any_color_hard_gates_to_zero(self, make_hoser):
        hoser = make_hoser(colors=frozenset({"R"}), castable_any_color=False)
        assert castability_factor(hoser, frozenset({"U", "B"}), "Painter") == 0.0

    def test_castable_any_color_bypasses_color_check(self, make_hoser):
        hoser = make_hoser(colors=frozenset({"B"}), castable_any_color=True)
        assert castability_factor(hoser, frozenset({"U"}), "Painter") == 1.0

    def test_cast_requires_satisfied(self, make_hoser):
        hoser = make_hoser(colors=frozenset({"W"}), cast_requires="opp_controls_plains")
        opp_cards = frozenset({"Plains", "Swords to Plowshares"})
        assert castability_factor(hoser, frozenset({"U"}), "Death and Taxes", opp_cards) == 1.0

    def test_cast_requires_unsatisfied_hard_gates_to_zero(self, make_hoser):
        hoser = make_hoser(colors=frozenset({"W"}), cast_requires="opp_controls_plains")
        opp_cards = frozenset({"Wasteland", "Karakas"})
        assert castability_factor(hoser, frozenset({"U"}), "Death and Taxes", opp_cards) == 0.0

    def test_cast_requires_no_opp_cards_provided_hard_gates_to_zero(self, make_hoser):
        hoser = make_hoser(colors=frozenset({"W"}), cast_requires="opp_controls_plains")
        assert castability_factor(hoser, frozenset({"U"}), "Death and Taxes", None) == 0.0

    def test_cast_requires_snow_covered_plains_satisfies(self, make_hoser):
        hoser = make_hoser(colors=frozenset({"W"}), cast_requires="opp_controls_plains")
        opp_cards = {"Snow-Covered Plains": 4}
        assert castability_factor(hoser, frozenset({"U"}), "Death and Taxes", opp_cards) == 1.0

    def test_cast_requires_bypasses_color_check_when_satisfied(self, make_hoser):
        # Off-color deck, but the free-cast condition fires -> still castable.
        hoser = make_hoser(colors=frozenset({"W"}), cast_requires="opp_controls_plains")
        opp_cards = frozenset({"Plains"})
        assert castability_factor(hoser, frozenset({"B"}), "Death and Taxes", opp_cards) == 1.0


# ---------------------------------------------------------------------------
# draw_probability
# ---------------------------------------------------------------------------


class TestDrawProbability:
    def test_zero_copies_is_zero(self):
        assert draw_probability(0) == 0.0

    def test_negative_copies_is_zero(self):
        assert draw_probability(-1) == 0.0

    def test_monotonic_in_copies(self):
        values = [draw_probability(k) for k in range(0, 5)]
        assert values == sorted(values)
        # Strictly increasing for copies 1..4 (no ties across meaningfully different counts).
        for a, b in zip(values, values[1:]):
            assert b > a

    def test_marginal_is_positive_and_concave(self):
        values = [draw_probability(k) for k in range(0, 5)]
        marginals = [b - a for a, b in zip(values, values[1:])]
        assert all(m > 0 for m in marginals)
        # Concave (tapering): each successive marginal is smaller than the last.
        for m1, m2 in zip(marginals, marginals[1:]):
            assert m2 < m1

    def test_matches_hand_computed_hypergeometric(self):
        # P(>=1 of 4 copies in 24 draws from 60) = 1 - C(56,24)/C(60,24)
        expected = 1.0 - math.comb(56, 24) / math.comb(60, 24)
        assert draw_probability(4, deck_size=60, cards_seen=_BO3_CARDS_SEEN) == pytest.approx(
            expected
        )

    def test_full_deck_seen_is_certain(self):
        assert draw_probability(1, deck_size=10, cards_seen=10) == pytest.approx(1.0)

    def test_copies_clamped_to_deck_size(self):
        # Requesting more copies than the deck holds shouldn't error; clamps to deck_size.
        assert draw_probability(999, deck_size=60, cards_seen=24) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# ImpactBreakdown.score() + impact() — multiplicative hard-gate behavior
# ---------------------------------------------------------------------------


class TestImpactBreakdownScore:
    def test_score_is_product_of_factors(self):
        breakdown = ImpactBreakdown(centrality=0.8, symmetry=0.5, castability=1.0, draw_prob=0.4)
        assert breakdown.score() == pytest.approx(0.8 * 0.5 * 1.0 * 0.4)

    def test_zero_castability_hard_gates_to_zero(self):
        breakdown = ImpactBreakdown(centrality=1.0, symmetry=1.0, castability=0.0, draw_prob=1.0)
        assert breakdown.score() == 0.0

    def test_zero_draw_prob_hard_gates_to_zero(self):
        breakdown = ImpactBreakdown(centrality=1.0, symmetry=1.0, castability=1.0, draw_prob=0.0)
        assert breakdown.score() == 0.0

    def test_symmetry_floor_does_not_zero_the_score(self):
        # Floors (symmetry, centrality baseline) keep a merely-awkward card above 0.
        breakdown = ImpactBreakdown(
            centrality=_CENTRALITY_BASELINE, symmetry=_SYMMETRY_FLOOR, castability=1.0,
            draw_prob=0.4,
        )
        assert breakdown.score() > 0.0


class TestImpactBreakdownScoreWithoutDrawProb:
    """feature-sfv-weights: the element-weight factor excludes draw_prob entirely."""

    def test_excludes_draw_prob_factor(self):
        breakdown = ImpactBreakdown(centrality=0.8, symmetry=0.5, castability=1.0, draw_prob=0.4)
        assert breakdown.score_without_draw_prob() == pytest.approx(0.8 * 0.5 * 1.0)

    def test_independent_of_draw_prob_value(self):
        """The SAME centrality/symmetry/castability with wildly different draw_prob values
        must produce the identical score_without_draw_prob() — draw_prob genuinely excluded,
        not just numerically negligible."""
        low = ImpactBreakdown(centrality=0.8, symmetry=0.5, castability=1.0, draw_prob=0.01)
        high = ImpactBreakdown(centrality=0.8, symmetry=0.5, castability=1.0, draw_prob=0.99)
        assert low.score_without_draw_prob() == pytest.approx(high.score_without_draw_prob())

    def test_zero_castability_still_hard_gates_to_zero(self):
        """The remaining three factors still multiplicatively hard-gate."""
        breakdown = ImpactBreakdown(centrality=1.0, symmetry=1.0, castability=0.0, draw_prob=1.0)
        assert breakdown.score_without_draw_prob() == 0.0

    def test_zero_draw_prob_no_longer_zeroes_this_score(self):
        """The whole point of the split: a 0-copies (draw_prob=0) card still has a nonzero
        score_without_draw_prob() — copy-count gating is the per-copy taper's job now, not
        the element weight's."""
        breakdown = ImpactBreakdown(centrality=1.0, symmetry=1.0, castability=1.0, draw_prob=0.0)
        assert breakdown.score_without_draw_prob() == pytest.approx(1.0)


class TestImpactOrchestration:
    def test_impact_combines_all_four_factors(self, make_hoser, make_linchpin):
        hoser = make_hoser(
            name="Null Rod",
            colors=frozenset({"G"}),
            attacks=frozenset({"ramp", "greedy-manabase"}),
            symmetry="symmetric",
        )
        linchpin = make_linchpin(
            archetype="Painter", name="Grindstone", centrality=1.0,
            neutralized_by=frozenset({"artifact-ability-lock"}),
        )
        breakdown = impact(
            hoser,
            "Painter",
            opp_linchpins=[linchpin],
            my_vulnerability_tags=frozenset({"plays-blue"}),  # not exposed to ramp/manabase
            my_colors=frozenset({"G", "U"}),
            copies=4,
        )
        assert breakdown.centrality == 1.0
        assert breakdown.symmetry == 1.0  # not self-hosing
        assert breakdown.castability == 1.0
        assert breakdown.draw_prob == pytest.approx(draw_probability(4))
        assert breakdown.score() > 0.0

    def test_impact_uncastable_hard_gates_whole_score(self, make_hoser):
        hoser = make_hoser(colors=frozenset({"R"}), castable_any_color=False)
        breakdown = impact(
            hoser,
            "Painter",
            opp_linchpins=[],
            my_vulnerability_tags=frozenset(),
            my_colors=frozenset({"U", "B"}),
            copies=4,
        )
        assert breakdown.castability == 0.0
        assert breakdown.score() == 0.0

    def test_impact_zero_copies_hard_gates_whole_score(self, make_hoser):
        hoser = make_hoser(colors=frozenset({"B"}))
        breakdown = impact(
            hoser,
            "Painter",
            opp_linchpins=[],
            my_vulnerability_tags=frozenset(),
            my_colors=frozenset({"B"}),
            copies=0,
        )
        assert breakdown.draw_prob == 0.0
        assert breakdown.score() == 0.0

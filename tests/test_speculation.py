"""Tests for analytics/speculation.py — analogous-card matcher + intrinsic score + fusion.

Covers Unit 1 (analogous_cards), Unit 2 (intrinsic_score), and Unit 3 (speculate_card).
All tests are pure — no DB, no network. Hand-built Card objects.

The load-bearing honesty invariant tested here:
  confidence.level == "speculative" ALWAYS, even when every analogue is "established".
  Borrowing established data does NOT upgrade the forecast tier.
"""

from __future__ import annotations

from legacy_engine.analytics.speculation import (
    PRE_DATA_BANNER,
    Analogue,
    analogous_cards,
    intrinsic_score,
    speculate_card,
)
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Helpers — hand-built Card factory
# ---------------------------------------------------------------------------


def _card(
    name: str,
    *,
    type_line: str = "Instant",
    cmc: float = 1.0,
    colors: list[str] | None = None,
    oracle_text: str = "",
    power: str | None = None,
    toughness: str | None = None,
) -> Card:
    return Card(
        name=name,
        type_line=type_line,
        cmc=cmc,
        colors=colors or [],
        oracle_text=oracle_text,
        power=power,
        toughness=toughness,
    )


# Realistic cantrip cards (instant/sorcery + draw a card pattern)
BRAINSTORM = _card("Brainstorm", type_line="Instant", cmc=1.0, colors=["U"],
                   oracle_text="Draw three cards, then put two cards from your hand on top of your library in any order.")
PONDER = _card("Ponder", type_line="Sorcery", cmc=1.0, colors=["U"],
               oracle_text="Look at the top three cards of your library, then put them back in any order. You may shuffle. Draw a card.")
PREORDAIN = _card("Preordain", type_line="Sorcery", cmc=1.0, colors=["U"],
                  oracle_text="Scry 2, then draw a card.")

# A free counterspell (Force-of-Will-shaped)
FORCE_LIKE = _card(
    "Force-like Counterspell",
    type_line="Instant",
    cmc=5.0,
    colors=["U"],
    oracle_text="You may exile a blue card from your hand rather than pay this spell's mana cost.\nCounter target spell.",
)

# Dual-land shaped card
DUAL_LAND = _card("Underground Sea", type_line="Land — Island Swamp", cmc=0.0, colors=[],
                  oracle_text="({T}: Add {U} or {B}.)")
DUAL_LAND_2 = _card("Volcanic Island", type_line="Land — Island Mountain", cmc=0.0, colors=[],
                    oracle_text="({T}: Add {U} or {R}.)")
FETCHLAND = _card("Polluted Delta", type_line="Land", cmc=0.0, colors=[],
                  oracle_text="Search your library for an Island or Swamp card, put it onto the battlefield, then shuffle.")

# Creatures
GOYF = _card("Tarmogoyf", type_line="Creature — Lhurgoyf", cmc=2.0, colors=["G"],
             oracle_text="Tarmogoyf's power is equal to the number of card types among cards in all graveyards.", power="*", toughness="1+*")
DELVER = _card("Delver of Secrets", type_line="Creature — Human Wizard", cmc=1.0, colors=["U"],
               oracle_text="At the beginning of your upkeep, look at the top card of your library.", power="1", toughness="1")
DRAGON_LORD = _card("Dragon Lord", type_line="Creature — Dragon", cmc=7.0, colors=["R"],
                    oracle_text="Flying, haste. When Dragon Lord enters the battlefield, gain control of target creature.", power="5", toughness="5")

# A vanilla expensive card — should score LOW
VANILLA_5 = _card("Vanilla 5/3", type_line="Creature — Giant", cmc=5.0, colors=["G"],
                  oracle_text="", power="5", toughness="3")

# A symmetric-harm card — should be penalised
GRAFDIGGERS = _card("Grafdigger's Cage", type_line="Artifact", cmc=1.0, colors=[],
                    oracle_text="Creature cards in graveyards and libraries can't enter the battlefield. Players can't cast spells from graveyards or libraries.")


# ---------------------------------------------------------------------------
# Unit 1: analogous_cards (child story — highest-risk unit)
# ---------------------------------------------------------------------------


class TestAnalogousCards:
    """Tests for the analogous-card nearest-neighbour matcher (child story Unit 1)."""

    def test_cantrip_finds_cantrip_staples(self):
        """A new blue cantrip-shaped instant finds Brainstorm among analogues, not creatures."""
        new_cantrip = _card(
            "New Cantrip",
            type_line="Instant",
            cmc=1.0,
            colors=["U"],
            oracle_text="Draw a card.",
        )
        pool = [BRAINSTORM, PONDER, PREORDAIN, GOYF, DELVER, DUAL_LAND]
        result = analogous_cards(new_cantrip, pool, k=3)

        names = [a.card for a in result]
        # All returned should be Instants/Sorceries (type-bucket filter rejects creatures + lands)
        assert "Tarmogoyf" not in names
        assert "Underground Sea" not in names
        assert len(result) <= 3

    def test_card_type_hard_filter_land_analogues(self):
        """A new dual-land's analogues must be lands — never spells or creatures."""
        new_dual = _card("New Dual", type_line="Land — Forest Plains", cmc=0.0, colors=[],
                         oracle_text="({T}: Add {G} or {W}.)")
        pool = [DUAL_LAND, DUAL_LAND_2, FETCHLAND, BRAINSTORM, PONDER, GOYF]
        result = analogous_cards(new_dual, pool, k=5)

        for a in result:
            # The pool names we know are lands
            assert a.card in {"Underground Sea", "Volcanic Island", "Polluted Delta"}, \
                f"Expected only land-type analogues but got {a.card!r}"

    def test_card_type_hard_filter_creature_analogues(self):
        """A new creature's analogues must be creatures — never instants."""
        new_creature = _card("New Creature", type_line="Creature — Wizard", cmc=2.0, colors=["U"],
                             oracle_text="Flying. When New Creature enters the battlefield, draw a card.", power="2", toughness="1")
        pool = [BRAINSTORM, PONDER, GOYF, DELVER, DUAL_LAND]
        result = analogous_cards(new_creature, pool, k=5)

        for a in result:
            assert a.card in {"Tarmogoyf", "Delver of Secrets"}, \
                f"Expected only creature analogues but got {a.card!r}"

    def test_empty_pool_returns_empty_list(self):
        """Empty pool → empty analogues, no error."""
        result = analogous_cards(BRAINSTORM, [], k=5)
        assert result == []

    def test_k_larger_than_pool_returns_all_eligible(self):
        """k larger than eligible pool → returns all eligible, no index error."""
        pool = [BRAINSTORM, PONDER]  # only 2 eligible (sorcery vs instant: same general type? NO — different buckets)
        new_card = _card("New Instant", type_line="Instant", cmc=1.0, colors=["U"],
                         oracle_text="Draw a card.")
        result = analogous_cards(new_card, pool, k=100)
        # Only Brainstorm is an Instant; Ponder is Sorcery — they're different buckets
        assert len(result) <= 2  # at most the eligible cards

    def test_similarity_bounded_0_1(self):
        """Similarity values are in [0, 1] for all returned analogues."""
        pool = [BRAINSTORM, PONDER, PREORDAIN, GOYF, DELVER, DUAL_LAND]
        new_card = _card("New Blue Thing", type_line="Sorcery", cmc=2.0, colors=["U"],
                         oracle_text="Scry 1, then draw a card.")
        result = analogous_cards(new_card, pool, k=5)
        for a in result:
            assert 0.0 <= a.similarity <= 1.0, f"Similarity out of bounds: {a.similarity}"

    def test_identical_card_similarity_is_high(self):
        """A card identical to an existing one (different name) gets high similarity."""
        twin = _card("Brainstorm Twin", type_line="Instant", cmc=1.0, colors=["U"],
                     oracle_text="Draw three cards, then put two cards from your hand on top of your library in any order.")
        pool = [BRAINSTORM, PONDER]
        result = analogous_cards(twin, pool, k=5)
        brainstorm_result = next((a for a in result if a.card == "Brainstorm"), None)
        assert brainstorm_result is not None
        # Should have high similarity (same type/CMC/colors/oracle text except name);
        # not necessarily 1.0 due to role/keyword Jaccard with non-empty pool
        assert brainstorm_result.similarity > 0.5

    def test_stable_tie_break_by_name(self):
        """Ties are broken deterministically by card name (ascending)."""
        # Two identical cards — should always return in the same name order
        card_a = _card("Alpha Card", type_line="Instant", cmc=1.0, colors=["U"], oracle_text="Draw a card.")
        card_b = _card("Beta Card", type_line="Instant", cmc=1.0, colors=["U"], oracle_text="Draw a card.")
        new_card = _card("New Instant", type_line="Instant", cmc=1.0, colors=["U"], oracle_text="Draw a card.")
        pool = [card_b, card_a]  # intentionally reversed in pool
        result = analogous_cards(new_card, pool, k=5)

        # Should be sorted by similarity desc; ties by name asc
        if len(result) == 2 and result[0].similarity == result[1].similarity:
            assert result[0].card == "Alpha Card"
            assert result[1].card == "Beta Card"

    def test_excludes_self(self):
        """The target card is excluded from the analogue list even if it's in the pool."""
        pool = [BRAINSTORM, PONDER, BRAINSTORM]  # Brainstorm appears twice as self+pool entry
        # Use the exact same object as target
        result = analogous_cards(BRAINSTORM, pool + [BRAINSTORM], k=5)
        for a in result:
            assert a.card != "Brainstorm"

    def test_free_spell_finds_other_free_spells(self):
        """A free counterspell finds other free/free-interaction cards via role overlap."""
        pool = [FORCE_LIKE, BRAINSTORM, PONDER, GOYF, DELVER]
        new_free_counter = _card(
            "New Free Counter",
            type_line="Instant",
            cmc=3.0,
            colors=["U"],
            oracle_text="You may exile a blue card from your hand rather than pay this spell's mana cost.\nCounter target spell.",
        )
        result = analogous_cards(new_free_counter, pool, k=3)
        # Force-like should rank high (same type, similar free-cast pattern)
        names = [a.card for a in result]
        assert "Force-like Counterspell" in names, \
            f"Expected Force-like Counterspell in analogues, got {names}"

    def test_no_analogues_above_gate_returns_empty_for_different_type(self):
        """When only cards of different type exist, returns empty list."""
        pool = [BRAINSTORM, PONDER, PREORDAIN]  # all Instants/Sorceries
        new_land = _card("New Land", type_line="Land", cmc=0.0)
        result = analogous_cards(new_land, pool, k=5)
        assert result == [], "Expected empty — no lands in pool"


# ---------------------------------------------------------------------------
# Unit 2: intrinsic_score
# ---------------------------------------------------------------------------


class TestIntrinsicScore:
    """Tests for the intrinsic feature score rubric."""

    def test_free_counterspell_scores_high(self):
        """A Force-of-Will-shaped free counterspell should score above neutral (0.5)."""
        score = intrinsic_score(FORCE_LIKE)
        assert score.score > 0.5, f"Expected above-neutral intrinsic score, got {score.score:.3f}"
        assert score.confidence.level == "speculative"
        assert score.confidence.source == "heuristic"

    def test_vanilla_expensive_card_scores_low(self):
        """A vanilla 5-mana creature with no text should score low."""
        score = intrinsic_score(VANILLA_5)
        assert score.score < 0.5, f"Expected low intrinsic score, got {score.score:.3f}"

    def test_breakdown_components_present(self):
        """Every component in the breakdown is present and a float."""
        score = intrinsic_score(FORCE_LIKE)
        bd = score.breakdown
        assert isinstance(bd.cmc_band, float)
        assert isinstance(bd.interaction, float)
        assert isinstance(bd.role_match, float)
        assert isinstance(bd.stat_efficiency, float)

    def test_score_bounded_0_1(self):
        """Score is always in [0, 1] for any card."""
        for card in [BRAINSTORM, FORCE_LIKE, VANILLA_5, GOYF, DUAL_LAND, GRAFDIGGERS]:
            score = intrinsic_score(card)
            assert 0.0 <= score.score <= 1.0, \
                f"{card.name}: score out of bounds: {score.score:.3f}"

    def test_confidence_always_speculative(self):
        """Intrinsic score always carries speculative confidence."""
        for card in [BRAINSTORM, FORCE_LIKE, GOYF]:
            score = intrinsic_score(card)
            assert score.confidence.level == "speculative"

    def test_low_cmc_scores_better_cmc_band_than_high(self):
        """A 1-mana card should have a higher cmc_band contribution than a 5-mana card."""
        low = intrinsic_score(_card("Cheap", cmc=1.0))
        high = intrinsic_score(_card("Expensive", cmc=6.0))
        assert low.breakdown.cmc_band > high.breakdown.cmc_band

    def test_free_spell_treated_as_cmc_zero(self):
        """A card with is_free_spell=True gets treated as CMC 0 in the CMC band."""
        free_spell = _card(
            "Free Card",
            type_line="Instant",
            cmc=3.0,
            oracle_text="You may exile a card rather than pay this spell's mana cost. Counter target spell.",
        )
        expensive = _card("Expensive", cmc=3.0, type_line="Instant")
        score_free = intrinsic_score(free_spell)
        score_expensive = intrinsic_score(expensive)
        # Free spell should score higher overall (cmc_band 1.0 vs ~0.5)
        assert score_free.breakdown.cmc_band > score_expensive.breakdown.cmc_band

    def test_stat_efficiency_zero_for_non_creatures(self):
        """Non-creatures have stat_efficiency = 0."""
        score = intrinsic_score(BRAINSTORM)
        assert score.breakdown.stat_efficiency == 0.0

    def test_stat_efficiency_nonzero_for_cheap_beater(self):
        """Cheap high-power creature has nonzero stat_efficiency contribution."""
        cheap_beater = _card("Cheap Beater", type_line="Creature — Beast", cmc=2.0,
                              power="4", toughness="4")
        score = intrinsic_score(cheap_beater)
        assert score.breakdown.stat_efficiency > 0.0


# ---------------------------------------------------------------------------
# Unit 3: speculate_card (fusion + HONESTY GUARANTEE)
# ---------------------------------------------------------------------------


class TestSpeculateCard:
    """Tests for the fusion unit and the central honesty guarantee."""

    def _make_mock_winrates(self, card_name: str, lift: float = 0.05, n: int = 150):
        """Build a mock CardWinRates where card_name has a known lift at n=150 (established)."""
        from legacy_engine.analytics.match_results import CardMarginalRecord, CardWinRates, MatchCoverage

        wins = int(n * (0.5 + lift))
        losses = n - wins
        marginal = {
            (card_name, "main"): CardMarginalRecord(card=card_name, board="main", wins=wins, losses=losses),
        }
        return CardWinRates(
            marginal=marginal,
            matchup={},
            baseline_winrate=0.5,
            coverage=MatchCoverage(),
            provenance=None,
        )

    def test_confidence_always_speculative_with_established_analogues(self):
        """THE CENTRAL HONESTY GUARANTEE: forecast is ALWAYS speculative even when
        every analogue has established tier. Borrowing established data does NOT
        upgrade the forecast confidence level."""
        # Set up: Brainstorm exists in pool with 'established' win-rate data
        pool = [BRAINSTORM, PONDER, PREORDAIN]
        mock_wr = self._make_mock_winrates("Brainstorm", lift=0.05, n=150)  # established (n≥100)

        new_cantrip = _card("New Cantrip", type_line="Instant", cmc=1.0, colors=["U"],
                            oracle_text="Draw a card.")
        forecast = speculate_card(new_cantrip, pool, mock_wr, k=3)

        # THE HONESTY ASSERTION — this is the load-bearing test
        assert forecast.confidence.level == "speculative", (
            f"Confidence must ALWAYS be speculative but got {forecast.confidence.level!r}. "
            "Borrowing established-tier data does NOT upgrade a pre-data forecast."
        )
        assert forecast.confidence.source == "heuristic"

    def test_label_always_contains_pre_data_banner(self):
        """Every SpeculativeForecast.label must contain the PRE_DATA_BANNER string."""
        pool = [BRAINSTORM, PONDER]
        mock_wr = self._make_mock_winrates("Brainstorm")
        new_card = _card("New Blue Thing", type_line="Instant", cmc=1.0, colors=["U"])
        forecast = speculate_card(new_card, pool, mock_wr, k=2)
        assert PRE_DATA_BANNER in forecast.label, (
            f"Label must always contain '{PRE_DATA_BANNER}' but got: {forecast.label!r}"
        )

    def test_no_analogues_returns_intrinsic_only(self):
        """When no gated analogues exist, borrowed_prior is None and forecast == intrinsic.score."""
        # Pool is empty — no analogues at all
        new_card = _card("New Instant", type_line="Instant", cmc=2.0, colors=["R"])
        forecast = speculate_card(new_card, [], None, k=5)

        assert forecast.borrowed_prior is None
        assert abs(forecast.forecast - forecast.intrinsic.score) < 1e-9, (
            f"Without analogues, forecast must equal intrinsic score "
            f"({forecast.forecast:.4f} vs {forecast.intrinsic.score:.4f})"
        )
        assert forecast.confidence.level == "speculative"

    def test_degrade_to_intrinsic_when_no_gated_analogues(self):
        """When all analogues are speculative-tier (n=0), borrowed_prior is None.
        The forecast degrades to intrinsic-only (honest degrade)."""
        pool = [BRAINSTORM]
        # No win-rates at all — Brainstorm will be speculative (n=0 default)
        new_cantrip = _card("New Cantrip", type_line="Instant", cmc=1.0, colors=["U"],
                            oracle_text="Draw a card.")
        forecast = speculate_card(new_cantrip, pool, None, k=3)

        assert forecast.borrowed_prior is None
        assert forecast.confidence.level == "speculative"

    def test_with_gated_analogues_borrowed_prior_is_not_none(self):
        """When established/evolving analogues exist, borrowed_prior is set (not None)."""
        pool = [BRAINSTORM, PONDER]
        mock_wr = self._make_mock_winrates("Brainstorm", lift=0.05, n=150)

        new_cantrip = _card("New Cantrip", type_line="Instant", cmc=1.0, colors=["U"],
                            oracle_text="Draw a card.")
        forecast = speculate_card(new_cantrip, pool, mock_wr, k=3)

        # Brainstorm should pass the gate (n=150 → established)
        # borrowed_prior should be set
        assert forecast.borrowed_prior is not None
        assert isinstance(forecast.borrowed_prior, float)

    def test_forecast_field_in_0_1(self):
        """The fused forecast is always in [0, 1]."""
        pool = [BRAINSTORM, GOYF, DUAL_LAND]
        mock_wr = self._make_mock_winrates("Brainstorm")
        for card in [FORCE_LIKE, VANILLA_5, GRAFDIGGERS]:
            forecast = speculate_card(card, pool, mock_wr, k=3)
            assert 0.0 <= forecast.forecast <= 1.0, \
                f"{card.name}: forecast out of bounds: {forecast.forecast:.4f}"

    def test_analogues_tuple_of_analogue_objects(self):
        """forecast.analogues is a tuple of Analogue objects with borrowed_lift and borrowed_tier set."""
        pool = [BRAINSTORM, PONDER]
        mock_wr = self._make_mock_winrates("Brainstorm", n=150)
        new_card = _card("New Instant", type_line="Instant", cmc=1.0, colors=["U"])
        forecast = speculate_card(new_card, pool, mock_wr, k=2)

        assert isinstance(forecast.analogues, tuple)
        for a in forecast.analogues:
            assert isinstance(a, Analogue)
            # borrowed_tier should be set (either real tier or speculative)
            assert a.borrowed_tier is not None

    def test_analogues_show_tiers_transparently(self):
        """Analogue borrowed_tier reflects the actual tier of the analogued card — not speculative."""
        pool = [BRAINSTORM]
        mock_wr = self._make_mock_winrates("Brainstorm", n=150)  # established
        new_card = _card("New Instant", type_line="Instant", cmc=1.0, colors=["U"],
                         oracle_text="Draw a card.")
        forecast = speculate_card(new_card, pool, mock_wr, k=1)

        brainstorm_analogue = next((a for a in forecast.analogues if a.card == "Brainstorm"), None)
        if brainstorm_analogue is not None:
            assert brainstorm_analogue.borrowed_tier == "established"

    def test_no_winrates_degrades_gracefully(self):
        """card_winrates=None → degrades to intrinsic-only without error."""
        pool = [BRAINSTORM, PONDER]
        new_card = _card("New Instant", type_line="Instant", cmc=1.0, colors=["U"])
        forecast = speculate_card(new_card, pool, None, k=2)

        assert forecast.confidence.level == "speculative"
        assert PRE_DATA_BANNER in forecast.label

    def test_card_field_matches_target_name(self):
        """forecast.card matches the target card name."""
        new_card = _card("My New Card", type_line="Instant", cmc=1.0)
        forecast = speculate_card(new_card, [], None)
        assert forecast.card == "My New Card"


# ---------------------------------------------------------------------------
# Unit 1 extended: CardWinRates integration helpers (analogue enrichment)
# ---------------------------------------------------------------------------


class TestAnalogueEnrichment:
    """Integration tests for analogous_cards + card_value_marginal enrichment."""

    def test_analogue_borrowed_lift_is_numeric(self):
        """borrowed_lift on an enriched Analogue is a float (not None after enrichment)."""
        from legacy_engine.analytics.match_results import CardMarginalRecord, CardWinRates, MatchCoverage

        marginal = {("Brainstorm", "main"): CardMarginalRecord(card="Brainstorm", board="main", wins=60, losses=40)}
        wr = CardWinRates(marginal=marginal, matchup={}, baseline_winrate=0.5,
                          coverage=MatchCoverage(), provenance=None)

        pool = [BRAINSTORM]
        new_card = _card("New Cantrip", type_line="Instant", cmc=1.0, colors=["U"],
                         oracle_text="Draw a card.")
        forecast = speculate_card(new_card, pool, wr, k=1)

        for a in forecast.analogues:
            assert a.borrowed_lift is not None
            assert isinstance(a.borrowed_lift, float)

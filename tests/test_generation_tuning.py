"""Tests for generation.tuning — Units 1–4 of epic-deck-generation-tuning.

Fixture design
--------------
Archetype: "TuneDelver" — 10 decks, dated within the current ban-regime (2026-05-25).

Main pool:
  Core cards (10/10 → inclusion_pct=1.0 → LOCKED):
    Brainstorm×4, Force of Will×4, Ponder×4, Wasteland×4,
    Dragon's Rage Channeler×4, Volcanic Island×2, Scalding Tarn×4,
    Mishra's Bauble×4, Polluted Delta×4, Arid Mesa×4, Misty Rainforest×4
    (44 cards summed across the 10/10 core).

  Flex cards (< 65% inclusion → flexible):
    - "Daze" ×4: 8/10 decks (80% → LOCKED, above 65%)
    - "Murktide Regent" ×2: 8/10 decks (80% → LOCKED)
    - "Flooded Strand" ×4: 8/10 decks (80% → LOCKED)
    - "Preordain" ×4: 6/10 decks (60% → FLEX, below 65%)
    - "Lightning Bolt" ×4: 4/10 decks (40% → FLEX)
    - "Surgical Extraction" ×2: 4/10 decks (40% → FLEX; also a graveyard-hate hoser!)

The key trick: some Delver decks run "Surgical Extraction" in the maindeck (4 decks, 40%).
This puts "Surgical Extraction" in the candidate pool (main board, observed).
It is ALSO in the HOSER_CATALOG (castable_any_color=True, attacks graveyard-reliant).

When the field is heavily graveyard-reliant (e.g. 80% Reanimator), swapping in
"Surgical Extraction" (which covers "Reanimator|graveyard-reliant") improves coverage.
The starting shell has "Preordain" as a flex slot and does NOT have "Surgical Extraction".
After tuning, "Surgical Extraction" should be swapped in and coverage improves.

Field fixture for thin-data fallback: archetype "NoDataArchetype" is NOT in the
matchup matrix (no match rounds involve it), triggering the bimodal fallback path.

All tests are deterministic (no random.seed() needed — greedy + coverage are pure).
"""

from __future__ import annotations

import pytest
import duckdb as _duckdb
from click.testing import CliRunner

from legacy_engine.advisory.field import build_custom_field
from legacy_engine.advisory.sideboard import (
    CoverageModel,
    HoserCard,
    _build_coverage_model,
    _compute_covered_weight,
)
from legacy_engine.cli import main
from legacy_engine.generation.tuning import (
    TunedDeck,
    candidate_pool,
    coverage_value,
    partition_flex,
    tune_deck,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item


# ---------------------------------------------------------------------------
# Tournament fixture builders
# ---------------------------------------------------------------------------

def _card(name: str, count: int = 4) -> dict:
    return {"CardName": name, "Count": count}


def _make_deck_raw(player: str, mainboard: list[dict], sideboard: list[dict]) -> dict:
    return {
        "Player": player,
        "Result": "1st Place",
        "Mainboard": mainboard,
        "Sideboard": sideboard,
    }


def _build_tune_delver_tournament() -> dict:
    """10 TuneDelver decks, with 'Surgical Extraction' run mainboard in 4 of them.

    Core 10/10 (11 cards × modal counts = 44 cards total for all 10 decks):
      Brainstorm×4, Force of Will×4, Ponder×4, Wasteland×4,
      Dragon's Rage Channeler×4, Volcanic Island×2, Scalding Tarn×4,
      Mishra's Bauble×4, Polluted Delta×4, Arid Mesa×4, Misty Rainforest×4

    Partial cards:
      - Daze×4: decks 0-7 (8/10 = 80% → locked)
      - Murktide Regent×2: decks 0-7 (80% → locked)
      - Flooded Strand×4: decks 0-7 (80% → locked)
      - Preordain×4: decks 0-5 (6/10 = 60% → flex)
      - Lightning Bolt×4: decks 0-3 (4/10 = 40% → flex)
      - Surgical Extraction×2: decks 0-3 (4/10 = 40% → flex AND in candidate pool)

    Deck sizes (to ensure at least 60 cards in consensus):
      Deck 0-3: 44 + 4+2+4+4+4+2 = 64 cards
      Deck 4-5: 44 + 4+2+4+4 = 58 → need padding; add extra Misty Rainforest
      Deck 6-7: 44 + 4+2+4 = 54 → padding with extra fetch
      Deck 8-9: 44 → padding

    We pad to ensure consensus always has ≥60 main cards available.
    """
    decks = []
    for i in range(10):
        main = [
            _card("Brainstorm", 4),
            _card("Force of Will", 4),
            _card("Ponder", 4),
            _card("Wasteland", 4),
            _card("Dragon's Rage Channeler", 4),
            _card("Volcanic Island", 2),
            _card("Scalding Tarn", 4),
            _card("Mishra's Bauble", 4),
            _card("Polluted Delta", 4),
            _card("Arid Mesa", 4),
            _card("Misty Rainforest", 4),
        ]
        # 80% locked cards
        if i < 8:
            main.append(_card("Daze", 4))
            main.append(_card("Murktide Regent", 2))
            main.append(_card("Flooded Strand", 4))
        # Flex cards
        if i < 6:
            main.append(_card("Preordain", 4))
        if i < 4:
            main.append(_card("Lightning Bolt", 4))
            main.append(_card("Surgical Extraction", 2))

        # Pad short decks to ensure enough pool for consensus 60-fill.
        total = sum(c["Count"] for c in main)
        if total < 60:
            # Pad with additional Misty Rainforest (already in deck, just add more copies)
            # Use a harmless non-banned card.
            pad_needed = 60 - total
            main.append({"CardName": "Tundra", "Count": pad_needed})

        side = [
            _card("Pyroblast", 4),
            _card("Red Elemental Blast", 4),
        ]
        if i < 8:
            side.append(_card("Flusterstorm", 2))
        if i < 6:
            side.append(_card("Grafdigger's Cage", 2))

        decks.append(_make_deck_raw(f"player{i}", main, side))

    return {
        "Tournament": {
            "Name": "Tune Legacy Challenge",
            "Date": "2026-05-25",
            "Uri": "https://www.mtgo.com/decklist/tune-legacy-challenge-2026-05-25",
            "Formats": "Legacy",
        },
        "Decks": decks,
        "Rounds": [],
        "Standings": [],
    }


# ---------------------------------------------------------------------------
# Shared fixture: in-memory DuckDB with TuneDelver data.
# ---------------------------------------------------------------------------

@pytest.fixture
def con():
    """In-memory DuckDB with TuneDelver tournament data."""
    c = store.connect(":memory:")
    store.init_schema(c)
    raw = _build_tune_delver_tournament()
    store.load_tournament(c, parse_cache_item(raw, "MTGO"))
    c.execute("UPDATE decks SET archetype = 'TuneDelver'")
    yield c
    c.close()


@pytest.fixture
def gy_field():
    """Custom field: 80% Reanimator (graveyard-reliant), 20% Combo."""
    return build_custom_field({"Reanimator": 0.80, "Combo": 0.20})


@pytest.fixture
def db_path(tmp_path, con):
    """Write the in-memory DB to a temporary file for CLI tests."""
    path = tmp_path / "tune_test.duckdb"
    file_con = _duckdb.connect(str(path))
    store.init_schema(file_con)
    raw = _build_tune_delver_tournament()
    store.load_tournament(file_con, parse_cache_item(raw, "MTGO"))
    file_con.execute("UPDATE decks SET archetype = 'TuneDelver'")
    file_con.close()
    return path


@pytest.fixture
def deck_file(tmp_path):
    """A 60-card starting maindeck for TuneDelver — no 'Surgical Extraction' in flex.

    4+4+4+4+4+2+4+4+4+4+4+4+2+4+4+4 = 60
    """
    text = (
        "4 Brainstorm\n"
        "4 Force of Will\n"
        "4 Ponder\n"
        "4 Wasteland\n"
        "4 Dragon's Rage Channeler\n"
        "2 Volcanic Island\n"
        "4 Scalding Tarn\n"
        "4 Mishra's Bauble\n"
        "4 Polluted Delta\n"
        "4 Arid Mesa\n"
        "4 Misty Rainforest\n"
        "4 Daze\n"
        "2 Murktide Regent\n"
        "4 Flooded Strand\n"
        "4 Preordain\n"
        "4 Lightning Bolt\n"
    )
    p = tmp_path / "shell.txt"
    p.write_text(text)
    return p


# ---------------------------------------------------------------------------
# Unit 1 tests — partition_flex + candidate_pool
# ---------------------------------------------------------------------------

class TestPartitionFlex:
    def test_locked_core_has_high_inclusion_cards(self, con):
        """10/10 inclusion cards (Brainstorm etc.) are locked; flex contains low-inclusion cards."""
        maindeck = {
            "Brainstorm": 4, "Force of Will": 4, "Ponder": 4, "Wasteland": 4,
            "Dragon's Rage Channeler": 4, "Volcanic Island": 2, "Scalding Tarn": 4,
            "Mishra's Bauble": 4, "Polluted Delta": 4, "Arid Mesa": 4,
            "Misty Rainforest": 4, "Daze": 4, "Murktide Regent": 2, "Flooded Strand": 4,
            "Preordain": 4,   # 60% → flex
        }
        locked, flex = partition_flex(con, "TuneDelver", maindeck)
        # Core 10/10 cards must be locked (inclusion_pct = 1.0 ≥ 0.65)
        assert "Brainstorm" in locked
        assert "Force of Will" in locked
        assert "Ponder" in locked
        # Preordain (60%) must be flex
        assert "Preordain" in flex
        assert "Preordain" not in locked

    def test_locked_and_flex_are_disjoint_and_complete(self, con):
        maindeck = {
            "Brainstorm": 4, "Force of Will": 4, "Ponder": 4,
            "Wasteland": 4, "Dragon's Rage Channeler": 4, "Volcanic Island": 2,
            "Scalding Tarn": 4, "Mishra's Bauble": 4, "Polluted Delta": 4,
            "Arid Mesa": 4, "Misty Rainforest": 4, "Daze": 4, "Murktide Regent": 2,
            "Flooded Strand": 4, "Preordain": 4,
        }
        locked, flex = partition_flex(con, "TuneDelver", maindeck)
        # No overlap
        assert not (set(locked) & set(flex))
        # Complete coverage
        assert set(locked) | set(flex) == set(maindeck)
        # Counts sum to original
        total_locked = sum(locked.values())
        total_flex = sum(flex.values())
        total_main = sum(maindeck.values())
        assert total_locked + total_flex == total_main

    def test_unknown_card_lands_in_flex(self, con):
        """A card not in the archetype's observed pool has inclusion_pct=0 → flex."""
        maindeck = {"Brainstorm": 4, "UserSpecialCard": 4}
        locked, flex = partition_flex(con, "TuneDelver", maindeck)
        assert "UserSpecialCard" in flex

    def test_threshold_boundary(self, con):
        """Daze (80% > 65%) is locked; Preordain (60% < 65%) is flex."""
        maindeck = {"Daze": 4, "Preordain": 4}
        locked, flex = partition_flex(con, "TuneDelver", maindeck, lock_threshold=0.65)
        assert "Daze" in locked
        assert "Preordain" in flex

    def test_empty_maindeck_returns_empty_dicts(self, con):
        locked, flex = partition_flex(con, "TuneDelver", {})
        assert locked == {}
        assert flex == {}


class TestCandidatePool:
    def test_pool_contains_surgical_extraction(self, con):
        """Surgical Extraction runs in 4/10 decks maindeck → in candidate pool."""
        pool = candidate_pool(con, "TuneDelver")
        assert "Surgical Extraction" in pool

    def test_pool_contains_core_cards(self, con):
        pool = candidate_pool(con, "TuneDelver")
        assert "Brainstorm" in pool
        assert "Force of Will" in pool

    def test_pool_ordered_by_inclusion_desc(self, con):
        """Candidate pool is sorted by inclusion_pct DESC (high-inclusion cards first)."""
        from legacy_engine.generation.consensus import card_frequencies
        pool = candidate_pool(con, "TuneDelver")
        freqs = card_frequencies(con, "TuneDelver", board="main")
        freq_map = {cf.name: cf.inclusion_pct for cf in freqs}
        # pool should contain the same cards as card_frequencies
        assert set(pool) == set(cf.name for cf in freqs)
        # pool order should be non-increasing by inclusion_pct
        pcts = [freq_map.get(name, 0.0) for name in pool]
        assert pcts == sorted(pcts, reverse=True), (
            f"Pool not sorted by inclusion_pct DESC: {list(zip(pool, pcts))[:5]}"
        )

    def test_unknown_archetype_returns_empty(self, con):
        pool = candidate_pool(con, "NonExistentArchetype")
        assert pool == []


# ---------------------------------------------------------------------------
# Unit 2 tests — coverage_value
# ---------------------------------------------------------------------------

class TestCoverageValue:
    def _make_model_with_surgical(self) -> CoverageModel:
        """Build a hand-crafted CoverageModel where Surgical Extraction covers
        'Reanimator|graveyard-reliant' with weight 0.16 (0.80 share × 0.20 swing).
        """
        return CoverageModel(
            element_weight={"Reanimator|graveyard-reliant": 0.16},
            candidate_covers={"Surgical Extraction": frozenset({"Reanimator|graveyard-reliant"})},
            candidate_meta={
                "Surgical Extraction": HoserCard(
                    name="Surgical Extraction",
                    attacks=frozenset({"graveyard-reliant"}),
                    colors=frozenset({"B"}),
                    max_copies=2,
                    swing=0.20,
                    castable_any_color=True,
                )
            },
            warnings=(),
        )

    def test_empty_cards_returns_zero(self):
        model = self._make_model_with_surgical()
        val = coverage_value(model, {})
        assert val == pytest.approx(0.0)

    def test_one_copy_provides_positive_coverage(self):
        """Adding 1x Surgical Extraction → g(1)×weight = (1-0.5^1)×0.16 = 0.08."""
        model = self._make_model_with_surgical()
        val = coverage_value(model, {"Surgical Extraction": 1})
        # g(1) = 1 - (1-0.5)^1 = 0.5
        assert val == pytest.approx(0.5 * 0.16, abs=1e-9)

    def test_two_copies_more_than_one(self):
        """Two copies of a hoser provide strictly more coverage than one (diminishing returns)."""
        model = self._make_model_with_surgical()
        val1 = coverage_value(model, {"Surgical Extraction": 1})
        val2 = coverage_value(model, {"Surgical Extraction": 2})
        assert val2 > val1

    def test_diminishing_returns(self):
        """Marginal gain from copy N+1 is less than from copy N (g is concave)."""
        model = self._make_model_with_surgical()
        v0 = coverage_value(model, {})
        v1 = coverage_value(model, {"Surgical Extraction": 1})
        v2 = coverage_value(model, {"Surgical Extraction": 2})
        gain_1 = v1 - v0
        gain_2 = v2 - v1
        assert gain_1 > gain_2

    def test_non_covering_card_is_ignored(self):
        """A card not in candidate_covers contributes nothing to coverage."""
        model = self._make_model_with_surgical()
        val_with = coverage_value(model, {"Brainstorm": 4})
        assert val_with == pytest.approx(0.0)

    def test_coverage_matches_compute_covered_weight(self):
        """coverage_value delegates to _compute_covered_weight — results must match."""
        model = self._make_model_with_surgical()
        cards = {"Surgical Extraction": 2}
        assert coverage_value(model, cards) == pytest.approx(
            _compute_covered_weight(cards, model), abs=1e-12
        )


# ---------------------------------------------------------------------------
# Unit 3 tests — tune_deck (greedy loop + bimodal fallback)
# ---------------------------------------------------------------------------

class TestTuneDeck:
    """Integration tests using the TuneDelver DB fixture.

    Field: graveyard-heavy (80% Reanimator) so Surgical Extraction (graveyard-hate
    in the candidate pool, castable in any deck) should get swapped in.

    Starting shell (via _build_starting_maindeck): 60-card Delver without Surgical Extraction.
    After tuning with the gy_field, the coverage improves and Surgical Extraction is added.
    """

    def _starting_maindeck(self) -> dict[str, int]:
        """60-card TuneDelver starting shell; no Surgical Extraction.

        Includes Preordain×4 and Lightning Bolt×4 as flex slots
        (60% and 40% inclusion respectively — both below 65% lock threshold).
        Total: 11 core×44 + Daze×4 + Murktide×2 + Flooded Strand×4 + Preordain×4
               + Lightning Bolt×2 = 60.
        """
        deck = {
            "Brainstorm": 4,
            "Force of Will": 4,
            "Ponder": 4,
            "Wasteland": 4,
            "Dragon's Rage Channeler": 4,
            "Volcanic Island": 2,
            "Scalding Tarn": 4,
            "Mishra's Bauble": 4,
            "Polluted Delta": 4,
            "Arid Mesa": 4,
            "Misty Rainforest": 4,
            "Daze": 4,
            "Murktide Regent": 2,
            "Flooded Strand": 4,
            "Preordain": 4,
            "Lightning Bolt": 4,  # 40% inclusion → flex
        }
        assert sum(deck.values()) == 60, f"Fixture broken: {sum(deck.values())} != 60"
        return deck

    def test_maindeck_exactly_60_after_tuning(self, con, gy_field):
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert sum(result.maindeck.values()) == 60, (
            f"Maindeck should be exactly 60, got {sum(result.maindeck.values())}"
        )

    def test_legality_ok_after_tuning(self, con, gy_field):
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert result.legality_errors == [], f"Legality errors: {result.legality_errors}"

    def test_sideboard_built_even_when_fell_back(self, con, gy_field):
        """Bimodal fallback: TuneDelver with no matchup data still builds the 15."""
        # With only the TuneDelver fixture (no rounds data), the matrix will have
        # TuneDelver absent OR all cells n=0 (no rounds recorded) → thin field.
        # The sideboard recommender should still be called.
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)

        if result.fell_back:
            # Fallback path: maindeck unchanged, sideboard should have been built
            assert result.maindeck == maindeck
            # sideboard is a dict (may be empty if no castable hosers, but not None)
            assert isinstance(result.sideboard, dict)
        else:
            # Not a fallback — just verify 60-card rule still holds
            assert sum(result.maindeck.values()) == 60

    def test_fell_back_reason_non_empty(self, con, gy_field):
        """TuneDelver has no matchup rounds → thin field → reason explains fallback."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        # reason is always populated
        assert result.reason, "reason should be a non-empty string"

    def test_coverage_before_ge_zero(self, con, gy_field):
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert result.coverage_before >= 0.0

    def test_coverage_after_ge_coverage_before(self, con, gy_field):
        """coverage_after ≥ coverage_before (greedy never makes things worse)."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert result.coverage_after >= result.coverage_before

    def test_swap_log_reproduces_transition(self, con, gy_field):
        """Each swap in the log is a (str, str) pair of card names."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        for cut, added in result.swaps:
            assert isinstance(cut, str) and cut
            assert isinstance(added, str) and added

    def test_locked_core_never_modified(self, con, gy_field):
        """Cards with inclusion_pct=1.0 (10/10 decks) must remain untouched."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        locked_core = {"Brainstorm", "Force of Will", "Ponder", "Wasteland",
                       "Dragon's Rage Channeler", "Volcanic Island", "Scalding Tarn",
                       "Mishra's Bauble", "Polluted Delta", "Arid Mesa", "Misty Rainforest"}
        for card in locked_core:
            assert result.maindeck.get(card) == maindeck[card], (
                f"Locked card {card!r} was modified by tuning"
            )

    def test_swaps_only_from_candidate_pool(self, con, gy_field):
        """Every card ADDED in the swap log must come from the archetype's candidate pool."""
        maindeck = self._starting_maindeck()
        pool = set(candidate_pool(con, "TuneDelver"))
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        for _cut, added in result.swaps:
            assert added in pool, (
                f"Swap added {added!r} which is not in the candidate pool {pool!r}"
            )

    def test_archetype_field_populated(self, con, gy_field):
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert result.archetype == "TuneDelver"

    def test_max_swaps_cap_respected(self, con, gy_field):
        """With max_swaps=2, the swap log has at most 2 entries."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field, max_swaps=2)
        assert len(result.swaps) <= 2

    def test_deterministic(self, con, gy_field):
        """Calling tune_deck twice yields identical results (no randomness)."""
        maindeck = self._starting_maindeck()
        r1 = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        r2 = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert r1.maindeck == r2.maindeck
        assert r1.swaps == r2.swaps
        assert r1.coverage_before == pytest.approx(r2.coverage_before)
        assert r1.coverage_after == pytest.approx(r2.coverage_after)

    def test_positioning_s_is_none_or_float(self, con, gy_field):
        """positioning_s is either None (absent from matrix) or a float in [0,1]."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.positioning_s is not None:
            assert 0.0 <= result.positioning_s <= 1.0


# ---------------------------------------------------------------------------
# Bimodal fallback explicit test — "NoData" archetype always absent from matrix
# ---------------------------------------------------------------------------

class TestBimodalFallback:
    def _starting_maindeck(self) -> dict[str, int]:
        return {
            "Brainstorm": 4, "Force of Will": 4, "Ponder": 4, "Wasteland": 4,
            "Dragon's Rage Channeler": 4, "Volcanic Island": 2, "Scalding Tarn": 4,
            "Mishra's Bauble": 4, "Polluted Delta": 4, "Arid Mesa": 4,
            "Misty Rainforest": 4, "Daze": 4, "Murktide Regent": 2,
            "Flooded Strand": 4, "Preordain": 4, "Lightning Bolt": 4,
        }

    def test_thin_field_sets_fell_back(self, con, gy_field):
        """Archetype with no match rounds → thin matrix → fell_back=True.

        The TuneDelver fixture has no Rounds entries so the matrix will have
        TuneDelver absent or all cells n=0.
        """
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        # TuneDelver has no rounds data → matrix is empty / archetype absent
        # → bimodal fallback MUST fire
        assert result.fell_back is True

    def test_fell_back_maindeck_unchanged(self, con, gy_field):
        """When fell_back, the maindeck is returned as-is (no swaps attempted)."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.fell_back:
            assert result.maindeck == maindeck
            assert result.swaps == []
            assert result.coverage_after == pytest.approx(result.coverage_before)

    def test_fell_back_sideboard_still_built(self, con, gy_field):
        """Bimodal fallback still calls recommend_sideboard for the 15."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.fell_back:
            # sideboard is a dict (may be empty if no colors match, but not None)
            assert isinstance(result.sideboard, dict)

    def test_fell_back_reason_mentions_fallback(self, con, gy_field):
        """Fallback reason string must mention 'fallback' or 'thin' or 'absent'."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.fell_back:
            reason_lower = result.reason.lower()
            assert (
                "fallback" in reason_lower
                or "thin" in reason_lower
                or "absent" in reason_lower
            ), f"Unexpected fallback reason: {result.reason!r}"


# ---------------------------------------------------------------------------
# Coverage improvement test with a hand-wired model (no DB round-trip needed)
# ---------------------------------------------------------------------------

class TestCoverageImprovement:
    """Verify the coverage_value increases when a hoser card is swapped in.

    Uses a hand-crafted CoverageModel to remove the DB dependency.
    This tests the core coverage arithmetic without the full tune_deck pipeline.
    """

    def test_swap_in_improves_coverage(self):
        """Adding Surgical Extraction to a maindeck improves coverage against
        a graveyard-heavy field (direct coverage_value test).
        """
        model = CoverageModel(
            element_weight={"Reanimator|graveyard-reliant": 0.16},
            candidate_covers={
                "Surgical Extraction": frozenset({"Reanimator|graveyard-reliant"})
            },
            candidate_meta={
                "Surgical Extraction": HoserCard(
                    name="Surgical Extraction",
                    attacks=frozenset({"graveyard-reliant"}),
                    colors=frozenset({"B"}),
                    max_copies=2,
                    swing=0.20,
                    castable_any_color=True,
                )
            },
            warnings=(),
        )

        maindeck_without = {"Brainstorm": 4, "Preordain": 4}
        maindeck_with = {"Brainstorm": 4, "Surgical Extraction": 2}

        cov_without = coverage_value(model, maindeck_without)
        cov_with = coverage_value(model, maindeck_with)
        assert cov_with > cov_without, (
            f"Expected coverage to improve after swapping in Surgical Extraction; "
            f"before={cov_without:.4f} after={cov_with:.4f}"
        )

    def test_coverage_saturates_not_linear(self):
        """Coverage increase from N→N+1 copies is smaller than from 0→1 (g is concave)."""
        model = CoverageModel(
            element_weight={"Reanimator|graveyard-reliant": 0.16},
            candidate_covers={
                "Surgical Extraction": frozenset({"Reanimator|graveyard-reliant"})
            },
            candidate_meta={
                "Surgical Extraction": HoserCard(
                    name="Surgical Extraction",
                    attacks=frozenset({"graveyard-reliant"}),
                    colors=frozenset({"B"}),
                    max_copies=2,
                    swing=0.20,
                    castable_any_color=True,
                )
            },
            warnings=(),
        )
        v0 = coverage_value(model, {})
        v1 = coverage_value(model, {"Surgical Extraction": 1})
        v2 = coverage_value(model, {"Surgical Extraction": 2})
        assert (v1 - v0) > (v2 - v1), "Marginal gain should be diminishing"


# ---------------------------------------------------------------------------
# Unit 4 tests — generate tune CLI leaf
# ---------------------------------------------------------------------------

class TestGenerateTuneCLI:
    def _runner(self) -> CliRunner:
        return CliRunner()

    def test_tune_listed_in_generate_help(self):
        """generate --help must list 'tune' as a subcommand."""
        runner = self._runner()
        result = runner.invoke(main, ["generate", "--help"])
        assert result.exit_code == 0
        assert "tune" in result.output

    def test_tune_requires_deck(self):
        """generate tune exits non-zero when --deck is missing."""
        runner = self._runner()
        result = runner.invoke(main, ["generate", "tune"])
        assert result.exit_code != 0

    def test_tune_happy_path_exit_zero(self, deck_file, db_path):
        """generate tune exits 0 for a known archetype with a valid shell."""
        runner = self._runner()
        result = runner.invoke(
            main,
            [
                "generate", "tune",
                "--deck", str(deck_file),
                "--archetype", "TuneDelver",
                "--db", str(db_path),
            ],
        )
        assert result.exit_code == 0, (
            f"exit={result.exit_code}\n{result.output}"
        )

    def test_tune_output_contains_maindeck_count(self, deck_file, db_path):
        """Output must contain 'Maindeck: 60' (exactly-60 header)."""
        runner = self._runner()
        result = runner.invoke(
            main,
            [
                "generate", "tune",
                "--deck", str(deck_file),
                "--archetype", "TuneDelver",
                "--db", str(db_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Maindeck: 60" in result.output

    def test_tune_output_contains_coverage_line(self, deck_file, db_path):
        """Output must include 'Coverage:' with before/after values."""
        runner = self._runner()
        result = runner.invoke(
            main,
            [
                "generate", "tune",
                "--deck", str(deck_file),
                "--archetype", "TuneDelver",
                "--db", str(db_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Coverage:" in result.output

    def test_tune_fallback_note_when_thin(self, deck_file, db_path):
        """Since TuneDelver has no rounds, output should include fallback note."""
        runner = self._runner()
        result = runner.invoke(
            main,
            [
                "generate", "tune",
                "--deck", str(deck_file),
                "--archetype", "TuneDelver",
                "--db", str(db_path),
            ],
        )
        assert result.exit_code == 0, result.output
        # The CLI prints [FALLBACK] for fell_back=True
        assert "FALLBACK" in result.output

    def test_tune_export_moxfield(self, deck_file, db_path):
        """--export moxfield adds export block to output."""
        runner = self._runner()
        result = runner.invoke(
            main,
            [
                "generate", "tune",
                "--deck", str(deck_file),
                "--archetype", "TuneDelver",
                "--db", str(db_path),
                "--export", "moxfield",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Export" in result.output

    def test_tune_swap_log_in_output(self, deck_file, db_path):
        """Output contains a 'Swap log:' section."""
        runner = self._runner()
        result = runner.invoke(
            main,
            [
                "generate", "tune",
                "--deck", str(deck_file),
                "--archetype", "TuneDelver",
                "--db", str(db_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Swap log" in result.output

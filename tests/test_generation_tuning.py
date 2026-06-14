"""Tests for generation.tuning rework (2026-05-31) — epic-deck-generation-tuning.

Rework design
-------------
Per-card field-weighted lift is now the SOLE maindeck-swap driver (fixes review
finding #4: the old coverage objective was hoser-blind and would hollow the
gameplan).  Coverage stays as a reported audit metric, NOT the swap driver.

Test structure
--------------
1. Unit 1 (partition_flex, candidate_pool) — unchanged, kept green.
2. Audit-metric (coverage_value) — renamed from "Unit 2"; still valid.
3. **Unit-level _greedy_tune tests (NO DB)**: hand-built fwv + trivial legal_swap
   → asserts the real swap happens, value_after > value_before (STRICT), locked
   core untouched, converges.  This is THE non-vacuous guarantee for the central AC
   and was the gap that made the old greedy tests vacuous.
4. **Integration on make_rounds_corpus**: a maindeck with a dead-vs-field flex card
   + a pool card with proven lift → tune_deck actually swaps through the REAL
   pipeline; asserts value_after > value_before, swaps non-empty, legality_errors
   == [], matchup_plans a dict.  Uses since="2025-01-01" so the per-card window
   includes the 2026-01 fixture corpus.
5. No-signal fallback: thin corpus → fell_back=True, objective="no-signal-skip",
   maindeck unchanged, sideboard still built.
6. Combined legality: returned TunedDeck always has legality_errors == []; a swap
   that would exceed 4 combined copies is rejected by _legal_swap_maindeck.
7. CLI output: updated assertions for new Value/Coverage headers + swap log +
   fallback note; also checks that matchup_plans is always a dict.

Consumed-module tests (test_sideboard.py, test_card_value.py, test_card_winrates.py,
test_advise_report.py) were NOT edited — this module consumes them, does not change
their contracts.
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
    _INCLUSION_CUT_RESISTANCE,
    _MIN_SWAP_GAIN,
    _greedy_tune,
    _legal_swap_maindeck,
    candidate_pool,
    coverage_value,
    field_weighted_values,
    has_value_signal,
    partition_flex,
    tune_deck,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.banlist import current_banlist
from legacy_engine.ingestion.cache import parse_cache_item


# ---------------------------------------------------------------------------
# Tournament fixture builders (TuneDelver — no rounds, tests thin-data path)
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

    Core 10/10 (11 cards x modal counts = 44 cards total for all 10 decks):
      Brainstorm x4, Force of Will x4, Ponder x4, Wasteland x4,
      Dragon's Rage Channeler x4, Volcanic Island x2, Scalding Tarn x4,
      Mishra's Bauble x4, Polluted Delta x4, Arid Mesa x4, Misty Rainforest x4

    Partial cards:
      - Daze x4: decks 0-7 (8/10 = 80% -> locked)
      - Murktide Regent x2: decks 0-7 (80% -> locked)
      - Flooded Strand x4: decks 0-7 (80% -> locked)
      - Preordain x4: decks 0-5 (6/10 = 60% -> flex)
      - Lightning Bolt x4: decks 0-3 (4/10 = 40% -> flex)
      - Surgical Extraction x2: decks 0-3 (4/10 = 40% -> flex AND in candidate pool)
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

        # Pad short decks to exactly 60.
        total = sum(c["Count"] for c in main)
        if total < 60:
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
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def con():
    """In-memory DuckDB with TuneDelver tournament data (no rounds)."""
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
    """A 60-card starting maindeck for TuneDelver — no Surgical Extraction in flex."""
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
            "Preordain": 4,   # 60% -> flex
        }
        locked, flex = partition_flex(con, "TuneDelver", maindeck)
        # Core 10/10 cards must be locked (inclusion_pct = 1.0 >= 0.65)
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
        """A card not in the archetype's observed pool has inclusion_pct=0 -> flex."""
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
        """Surgical Extraction runs in 4/10 decks maindeck -> in candidate pool."""
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
# Audit-metric tests — coverage_value (renamed from "Unit 2")
# coverage_value is now an AUDIT metric, not the swap driver.
# ---------------------------------------------------------------------------

class TestCoverageValue:
    def _make_model_with_surgical(self) -> CoverageModel:
        """Build a hand-crafted CoverageModel where Surgical Extraction covers
        'Reanimator|graveyard-reliant' with weight 0.16 (0.80 share x 0.20 swing).
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
        """Adding 1x Surgical Extraction -> g(1) x weight = (1-0.5^1) x 0.16 = 0.08."""
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
# Unit 1 rework tests — field_weighted_values + has_value_signal
# ---------------------------------------------------------------------------

class TestFieldWeightedValues:
    """Tests for field_weighted_values on a rounds-bearing corpus."""

    def test_no_rounds_returns_all_zeros(self, con, gy_field):
        """TuneDelver fixture has no rounds -> all fwv values are 0.0."""
        cards = ["Brainstorm", "Surgical Extraction"]
        fwv = field_weighted_values(con, gy_field, cards)
        assert all(v == 0.0 for v in fwv.values())

    def test_has_value_signal_false_when_all_zeros(self, con, gy_field):
        """No rounds -> has_value_signal is False."""
        cards = ["Brainstorm"]
        fwv = field_weighted_values(con, gy_field, cards)
        assert not has_value_signal(fwv)

    def test_has_value_signal_true_with_rounds(self, make_rounds_corpus):
        """With n_repeats=15 rounds corpus (n=30, evolving), signal clears the gate."""
        con, facts = make_rounds_corpus(n_repeats=15)
        field = build_custom_field({"Combo": 1.0})
        cards = ["Brainstorm", "Dark Ritual"]
        fwv = field_weighted_values(con, field, cards, since="2025-01-01")
        # Brainstorm is in Control's main and wins vs Combo -> positive lift
        # Dark Ritual is in Combo's main and loses vs Control -> negative lift in
        # this reversed perspective (Brainstorm holder is the Control player).
        # At minimum, has_value_signal should detect a non-zero entry.
        assert has_value_signal(fwv), (
            f"Expected value signal with n=30 evolving data; fwv={fwv}"
        )
        con.close()

    def test_empty_card_list_returns_empty(self, con, gy_field):
        fwv = field_weighted_values(con, gy_field, [])
        assert fwv == {}

    def test_fwv_keys_match_cards(self, con, gy_field):
        """fwv has exactly one entry per card in the input list."""
        cards = ["Brainstorm", "Force of Will", "Surgical Extraction"]
        fwv = field_weighted_values(con, gy_field, cards)
        assert set(fwv.keys()) == set(cards)


# ---------------------------------------------------------------------------
# Unit 2 rework tests — _greedy_tune (NO DB — hand-built fwv + trivial legal_swap)
# These are the central non-vacuous guarantee tests.
# ---------------------------------------------------------------------------

class TestGreedyTune:
    """Pure unit tests for _greedy_tune with hand-built fwv and trivial legal_swap.

    No DB required.  This is the fix for review finding #2 (vacuous tests) and
    the test that proves the central AC: given an fwv where a flex card scores
    low and a pool card scores high, the real swap happens and value_after >
    value_before (STRICT, not >=).
    """

    def _trivial_legal_swap(self, current, cut, add):
        """Trivial legal_swap: always valid if cut is in current; exactly-60 net-zero."""
        if current.get(cut, 0) <= 0:
            return False, current
        new = dict(current)
        if new[cut] == 1:
            del new[cut]
        else:
            new[cut] -= 1
        new[add] = new.get(add, 0) + 1
        if sum(new.values()) != 60:
            return False, current
        return True, new

    def test_real_swap_happens_value_strictly_improves(self):
        """THE central non-vacuous AC: flex card scores low, pool card scores high
        -> swap happens and value_after > value_before (STRICT).
        """
        # fwv: "BadFlex" scores -0.1 (dead vs field), "GoodPool" scores +0.3 (proven lift)
        fwv = {"BadFlex": -0.1, "GoodPool": 0.3}

        # 60-card maindeck: 59 locked + 1 flex (BadFlex)
        locked = {f"LockedCard{i}": 1 for i in range(59)}
        flex = {"BadFlex": 1}
        maindeck = dict(locked)
        maindeck["BadFlex"] = 1
        assert sum(maindeck.values()) == 60

        pool = ["GoodPool"]

        final_main, swaps, v_before, v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8,
            legal_swap=self._trivial_legal_swap,
        )

        # THE central AC: the swap happened
        assert len(swaps) == 1, f"Expected 1 swap, got {swaps}"
        assert swaps[0] == ("BadFlex", "GoodPool"), (
            f"Expected (BadFlex -> GoodPool), got {swaps[0]}"
        )

        # THE central AC: value strictly improved (not just >=)
        assert v_after > v_before, (
            f"value_after ({v_after:.4f}) must be STRICTLY greater than "
            f"value_before ({v_before:.4f})"
        )

        # GoodPool is now in maindeck; BadFlex is gone
        assert "GoodPool" in final_main
        assert "BadFlex" not in final_main

    def test_locked_core_never_cut(self):
        """Locked core cards are NEVER in the cut side of any swap."""
        # fwv: locked card has low value but is locked (should not be cut)
        fwv = {"LockedCard": -0.5, "GoodPool": 0.5, "FlexCard": -0.2}
        locked = {"LockedCard": 4}
        flex = {"FlexCard": 4}
        maindeck = {"LockedCard": 4, "FlexCard": 4}
        # Pad to 60 with more locked cards
        for i in range(52):
            k = f"Pad{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["GoodPool"]

        _final_main, swaps, _v_before, _v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8,
            legal_swap=self._trivial_legal_swap,
        )

        # LockedCard must never appear as cut in any swap
        for cut, add in swaps:
            assert cut != "LockedCard", (
                f"Locked card 'LockedCard' was cut in swap ({cut} -> {add})"
            )

    def test_no_strictly_improving_swap_at_stop(self):
        """After convergence, no strictly-improving swap remains."""
        # fwv: GoodFlex has higher value than anything in pool -> no swap should happen
        fwv = {"GoodFlex": 0.5, "BadPool": -0.2}
        locked = {}
        flex = {"GoodFlex": 1}
        maindeck = {"GoodFlex": 1}
        # Pad to 60
        for i in range(59):
            k = f"Pad{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["BadPool"]

        _final_main, swaps, _v_before, _v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8,
            legal_swap=self._trivial_legal_swap,
        )

        # No swap should have been made (gain would be negative)
        assert swaps == [], f"Expected no swaps (all would reduce value), got {swaps}"

    def test_max_swaps_cap_respected(self):
        """With max_swaps=2, the swap log has at most 2 entries."""
        # fwv: 4 flex cards each score -0.1, 4 pool cards each score +0.1
        fwv = {
            "Flex1": -0.1, "Flex2": -0.1, "Flex3": -0.1, "Flex4": -0.1,
            "Pool1": 0.1, "Pool2": 0.1, "Pool3": 0.1, "Pool4": 0.1,
        }
        locked = {}
        flex = {"Flex1": 1, "Flex2": 1, "Flex3": 1, "Flex4": 1}
        maindeck = dict(flex)
        for i in range(56):
            k = f"PadLock{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["Pool1", "Pool2", "Pool3", "Pool4"]

        _final_main, swaps, _v_before, _v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=2,
            legal_swap=self._trivial_legal_swap,
        )

        assert len(swaps) <= 2, f"max_swaps=2 but got {len(swaps)} swaps: {swaps}"

    def test_deterministic_same_fwv(self):
        """Calling _greedy_tune twice with identical inputs yields identical results."""
        fwv = {"FlexA": -0.1, "FlexB": -0.05, "PoolX": 0.3, "PoolY": 0.2}
        locked = {}
        flex = {"FlexA": 2, "FlexB": 2}
        maindeck = {"FlexA": 2, "FlexB": 2}
        for i in range(56):
            k = f"Pad{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["PoolX", "PoolY"]

        r1 = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8, legal_swap=self._trivial_legal_swap,
        )
        r2 = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8, legal_swap=self._trivial_legal_swap,
        )

        assert r1[0] == r2[0]  # same final_main
        assert r1[1] == r2[1]  # same swaps

    def test_illegal_swap_rejected(self):
        """A swap rejected by legal_swap is skipped; only legal swaps proceed."""
        # legal_swap always returns False (nothing is legal).
        def _always_reject(current, cut, add):
            return False, current

        fwv = {"BadFlex": -0.5, "GoodPool": 0.9}
        locked = {}
        flex = {"BadFlex": 1}
        maindeck = {"BadFlex": 1}
        for i in range(59):
            k = f"Pad{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["GoodPool"]

        final_main, swaps, v_before, v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8,
            legal_swap=_always_reject,
        )

        # No swaps should happen since all are rejected
        assert swaps == [], f"Expected no swaps (all rejected by legal_swap), got {swaps}"
        assert final_main == maindeck

    def test_value_before_after_computed_correctly(self):
        """value_before and value_after correctly reflect Sum(copies * fwv[card])."""
        fwv = {"FlexCard": -0.1, "PoolCard": 0.4}
        locked = {}
        flex = {"FlexCard": 1}
        maindeck = {"FlexCard": 1}
        for i in range(59):
            k = f"Pad{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["PoolCard"]

        final_main, swaps, v_before, v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8,
            legal_swap=self._trivial_legal_swap,
        )

        # Expected: value_before = sum(copies * fwv.get(card, 0.0) for card, copies in maindeck.items())
        # = 1 * (-0.1) + 59 * 0.0 = -0.1
        assert v_before == pytest.approx(-0.1, abs=1e-9)

        # After swap: FlexCard -> PoolCard; value_after = 1 * 0.4 + 59 * 0.0 = 0.4
        assert v_after == pytest.approx(0.4, abs=1e-9)
        assert v_after > v_before  # strict improvement

    # ── Core-protection tests (fix-tuner-core-protection) ────────────────────

    def test_epsilon_gain_does_not_cut_high_inclusion_flex_card(self):
        """A high-inclusion flex card (60% archetype adoption) must NOT be cut when the
        only available swap gains are sub-threshold (epsilon lift).

        This is the failing-then-passing test for fix-tuner-core-protection:
        - Nethergoyf-equivalent: inclusion=0.60, fwv=0.10 (positive, but modest)
        - PoolReplacement: fwv=0.10 + epsilon (trivially better by 0.001)
        - required gain for cut = max(_MIN_SWAP_GAIN, 0.60 * _INCLUSION_CUT_RESISTANCE)
        - At calibrated thresholds: required > 0.001 → swap is BLOCKED.

        The core card should remain in the maindeck at its original count.
        """
        epsilon = 0.001
        high_inclusion = 0.60
        fwv = {"Nethergoyf": 0.10, "PoolReplacement": 0.10 + epsilon}
        inclusion_pcts = {"Nethergoyf": high_inclusion}

        locked = {}
        flex = {"Nethergoyf": 3}
        maindeck = {"Nethergoyf": 3}
        for i in range(57):
            k = f"Pad{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["PoolReplacement"]

        final_main, swaps, v_before, v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8,
            legal_swap=self._trivial_legal_swap,
            inclusion_pcts=inclusion_pcts,
        )

        # The sub-threshold swap must be BLOCKED by the core-protection gate.
        assert swaps == [], (
            f"High-inclusion flex card should NOT be cut on epsilon lift "
            f"(gain={epsilon:.4f} < required={max(_MIN_SWAP_GAIN, high_inclusion * _INCLUSION_CUT_RESISTANCE):.4f}); "
            f"swaps={swaps}"
        )
        assert final_main.get("Nethergoyf") == 3, (
            f"Nethergoyf must stay at 3 copies; final_main={final_main}"
        )

    def test_large_gain_still_cuts_high_inclusion_flex_card(self):
        """A clearly superior swap (large gain >> threshold) MUST still execute even for
        a high-inclusion flex card.  The protection must not over-freeze the deck.

        Scenario: Nethergoyf at 60% inclusion, fwv=0.05.  PoolBetter at fwv=0.30.
        Gain = 0.25.  Required gate = max(0.02, 0.60 * 0.08) = max(0.02, 0.048) = 0.048.
        0.25 >> 0.048 → swap proceeds.
        """
        fwv = {"Nethergoyf": 0.05, "PoolBetter": 0.30}
        inclusion_pcts = {"Nethergoyf": 0.60}

        locked = {}
        flex = {"Nethergoyf": 3}
        maindeck = {"Nethergoyf": 3}
        for i in range(57):
            k = f"Pad{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["PoolBetter"]

        final_main, swaps, v_before, v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8,
            legal_swap=self._trivial_legal_swap,
            inclusion_pcts=inclusion_pcts,
        )

        # The large-gain swap MUST proceed (no over-freezing).
        assert len(swaps) > 0, (
            f"A clearly superior swap (gain=0.25 >> required) must still execute "
            f"for a high-inclusion flex card; swaps={swaps}"
        )
        assert v_after > v_before, (
            f"value must improve on a legitimate large-gain swap; "
            f"v_before={v_before:.4f} v_after={v_after:.4f}"
        )

    def test_flat_noise_floor_blocks_epsilon_on_zero_inclusion_card(self):
        """The flat _MIN_SWAP_GAIN floor blocks epsilon swaps even on cards with 0% inclusion
        (e.g. user-injected cards with no archetype history).

        Gain = 0.001 < _MIN_SWAP_GAIN → blocked regardless of inclusion.
        """
        epsilon = 0.001
        fwv = {"UserCard": 0.10, "PoolCard": 0.10 + epsilon}
        inclusion_pcts = {}  # no data for UserCard → 0.0 inclusion

        locked = {}
        flex = {"UserCard": 1}
        maindeck = {"UserCard": 1}
        for i in range(59):
            k = f"Pad{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["PoolCard"]

        final_main, swaps, _v_before, _v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8,
            legal_swap=self._trivial_legal_swap,
            inclusion_pcts=inclusion_pcts,
        )

        assert swaps == [], (
            f"Epsilon gain ({epsilon}) must be blocked by the flat _MIN_SWAP_GAIN floor "
            f"({_MIN_SWAP_GAIN}); swaps={swaps}"
        )

    def test_inclusion_pcts_none_uses_flat_floor_only(self):
        """When inclusion_pcts is None (old callers / tests), only the flat floor applies.
        A gain just above _MIN_SWAP_GAIN must proceed.
        """
        gain = _MIN_SWAP_GAIN + 0.01  # just above the flat floor
        fwv = {"FlexCard": 0.0, "PoolCard": gain}
        # No inclusion_pcts supplied (None) — backward-compatible path.

        locked = {}
        flex = {"FlexCard": 1}
        maindeck = {"FlexCard": 1}
        for i in range(59):
            k = f"Pad{i}"
            locked[k] = 1
            maindeck[k] = 1
        assert sum(maindeck.values()) == 60

        pool = ["PoolCard"]

        final_main, swaps, _v_before, _v_after = _greedy_tune(
            fwv, maindeck, locked, flex, pool,
            max_swaps=8,
            legal_swap=self._trivial_legal_swap,
            inclusion_pcts=None,   # backward-compatible: no inclusion data
        )

        assert len(swaps) == 1, (
            f"A gain just above _MIN_SWAP_GAIN ({gain:.4f} > {_MIN_SWAP_GAIN}) must "
            f"proceed when inclusion_pcts=None; swaps={swaps}"
        )


# ---------------------------------------------------------------------------
# Unit 3 rework tests — _legal_swap_maindeck (combined legality, fix #3)
# ---------------------------------------------------------------------------

class TestLegalSwapMaindeck:
    """Tests for the combined main+side legality enforcement (fix #3)."""

    def _snapshot(self):
        return current_banlist()

    def _base_main(self) -> dict[str, int]:
        """59-card maindeck with slot for one swap."""
        d = {"Island": 1}
        for i in range(58):
            d[f"PadCard{i}"] = 1
        assert sum(d.values()) == 59
        return d

    def test_valid_swap_returns_true(self):
        """A legal swap (60 cards, no ban violation) returns True."""
        main = {"Brainstorm": 4}
        for i in range(56):
            main[f"Pad{i}"] = 1
        assert sum(main.values()) == 60

        snap = self._snapshot()
        ok, new_main = _legal_swap_maindeck(
            main, "Brainstorm", "Ponder", {},
            banlist_snapshot=snap,
        )
        # Brainstorm -> Ponder: both legal, 4-copy rule fine
        assert ok
        assert new_main.get("Brainstorm") == 3
        assert new_main.get("Ponder") == 1
        assert sum(new_main.values()) == 60

    def test_combined_copy_limit_enforced(self):
        """A swap adding a card already at 4 copies combined (3 main + 1 side) is rejected."""
        snap = self._snapshot()
        # Target card: Ponder (3 copies in main, 1 in sideboard = 4 combined).
        # Swapping in one more Ponder would make 4 main + 1 side = 5 combined -> illegal.
        main = {"Brainstorm": 1, "Ponder": 3}
        for i in range(56):
            main[f"Pad{i}"] = 1
        assert sum(main.values()) == 60

        side = {"Ponder": 1}

        ok, new_main = _legal_swap_maindeck(
            main, "Brainstorm", "Ponder", side,
            banlist_snapshot=snap,
        )
        assert not ok, (
            "Swap adding Ponder when 3 main + 1 side = 4 combined should be rejected "
            "(would exceed 4 combined)"
        )

    def test_cut_card_not_in_main_rejected(self):
        """Attempting to cut a card not in the maindeck is rejected."""
        snap = self._snapshot()
        main = {"Brainstorm": 4}
        for i in range(56):
            main[f"Pad{i}"] = 1
        assert sum(main.values()) == 60

        ok, _ = _legal_swap_maindeck(
            main, "NotInDeck", "Ponder", {},
            banlist_snapshot=snap,
        )
        assert not ok

    def test_basic_land_exemption(self):
        """Basic lands are exempt from the 4-copy limit; adding a 5th Island is legal."""
        snap = self._snapshot()
        main = {"Island": 4, "Brainstorm": 1}
        for i in range(55):
            main[f"Pad{i}"] = 1
        assert sum(main.values()) == 60

        ok, new_main = _legal_swap_maindeck(
            main, "Brainstorm", "Island", {},
            banlist_snapshot=snap,
        )
        assert ok, "Basic land (Island) should not be copy-limited"
        assert new_main.get("Island") == 5

    def test_exactly_60_preserved(self):
        """Result maindeck is exactly 60 (net-zero swap: -1 cut, +1 add)."""
        snap = self._snapshot()
        main = {"Brainstorm": 4}
        for i in range(56):
            main[f"Pad{i}"] = 1
        assert sum(main.values()) == 60

        ok, new_main = _legal_swap_maindeck(
            main, "Brainstorm", "Ponder", {},
            banlist_snapshot=snap,
        )
        if ok:
            assert sum(new_main.values()) == 60


# ---------------------------------------------------------------------------
# tune_deck integration — no-signal fallback (TuneDelver has no rounds)
# ---------------------------------------------------------------------------

class TestTuneDeckNoSignalFallback:
    """tune_deck with no per-card data -> fell_back=True, objective="no-signal-skip"."""

    def _starting_maindeck(self) -> dict[str, int]:
        return {
            "Brainstorm": 4, "Force of Will": 4, "Ponder": 4, "Wasteland": 4,
            "Dragon's Rage Channeler": 4, "Volcanic Island": 2, "Scalding Tarn": 4,
            "Mishra's Bauble": 4, "Polluted Delta": 4, "Arid Mesa": 4,
            "Misty Rainforest": 4, "Daze": 4, "Murktide Regent": 2,
            "Flooded Strand": 4, "Preordain": 4, "Lightning Bolt": 4,
        }

    def test_fell_back_true_when_no_rounds(self, con, gy_field):
        """TuneDelver fixture has no rounds -> no per-card signal -> fell_back=True."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert result.fell_back is True, (
            f"Expected fell_back=True (no rounds data), got fell_back={result.fell_back}"
        )

    def test_objective_no_signal_skip(self, con, gy_field):
        """fell_back path sets objective='no-signal-skip'."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.fell_back:
            assert result.objective == "no-signal-skip", (
                f"Expected objective='no-signal-skip', got {result.objective!r}"
            )

    def test_maindeck_unchanged_on_fallback(self, con, gy_field):
        """fell_back -> maindeck is returned as-is (no swaps attempted)."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.fell_back:
            assert result.maindeck == maindeck
            assert result.swaps == []

    def test_value_before_equals_value_after_on_fallback(self, con, gy_field):
        """fell_back -> value_before == value_after (no swaps; both 0.0 on thin data)."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.fell_back:
            assert result.value_before == pytest.approx(result.value_after)

    def test_sideboard_still_built_on_fallback(self, con, gy_field):
        """fell_back -> sideboard recommender is still called (returns a dict)."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.fell_back:
            assert isinstance(result.sideboard, dict)

    def test_matchup_plans_is_dict_on_fallback(self, con, gy_field):
        """matchup_plans is always a dict (may be empty on thin data)."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert isinstance(result.matchup_plans, dict)

    def test_legality_errors_empty_on_fallback(self, con, gy_field):
        """Unit 3 guarantee: legality_errors is always [] on return."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert result.legality_errors == [], (
            f"legality_errors must always be [] on return; got {result.legality_errors}"
        )

    def test_reason_non_empty(self, con, gy_field):
        """reason is always populated."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert result.reason, "reason should be a non-empty string"

    def test_reason_mentions_fallback_when_thin(self, con, gy_field):
        """Fallback reason string must mention 'signal' or 'skip' or 'absent' or 'thin'."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.fell_back:
            reason_lower = result.reason.lower()
            assert any(kw in reason_lower for kw in ("signal", "skip", "absent", "thin")), (
                f"Unexpected fallback reason: {result.reason!r}"
            )

    def test_maindeck_exactly_60_on_fallback(self, con, gy_field):
        """Maindeck is exactly 60 even on the fallback path."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert sum(result.maindeck.values()) == 60

    def test_coverage_before_ge_zero(self, con, gy_field):
        """coverage_before >= 0 (audit metric, always non-negative)."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert result.coverage_before >= 0.0

    def test_archetype_field_populated(self, con, gy_field):
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert result.archetype == "TuneDelver"

    def test_deterministic(self, con, gy_field):
        """Calling tune_deck twice yields identical results (no randomness)."""
        maindeck = self._starting_maindeck()
        r1 = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        r2 = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        assert r1.maindeck == r2.maindeck
        assert r1.swaps == r2.swaps
        assert r1.fell_back == r2.fell_back

    def test_positioning_s_is_none_or_float(self, con, gy_field):
        """positioning_s is either None (absent from matrix) or a float."""
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "TuneDelver", maindeck, {}, field=gy_field)
        if result.positioning_s is not None:
            assert isinstance(result.positioning_s, float)

    def test_positioning_s_none_at_zero_coverage(self, con, gy_field):
        """Fix 4: TunedDeck.positioning_s must be None (not NaN) when s_computable=False.

        Zero coverage occurs when the archetype has no measured (n≥30) opponent cells.
        Before this fix, tune_deck assigned pos.s_mean directly — NaN when not computable.
        After the fix, the guard 'pos.s_mean if pos.s_computable else None' prevents NaN.
        """
        import math
        # Use an archetype that is in the DB but has zero matchup coverage (no rounds).
        # "TuneDelver" archetype was labeled in the corpus fixture but the no-signal
        # path here uses an archetype that is NOT in the matrix archetypes set.
        # Simplest: use an archetype not present in the matrix at all → positioning_s=None.
        maindeck = self._starting_maindeck()
        result = tune_deck(con, "NonexistentArchNoMatch", maindeck, {}, field=gy_field)
        # Either None (not in matrix) or a non-NaN float (has coverage).
        if result.positioning_s is not None:
            assert not math.isnan(result.positioning_s), (
                "positioning_s must never be NaN — use None when not computable"
            )


# ---------------------------------------------------------------------------
# Integration — tune_deck on rounds-bearing corpus (non-vacuous central AC)
# ---------------------------------------------------------------------------

class TestTuneDeckIntegration:
    """Integration test on make_rounds_corpus: the greedy path actually fires.

    Design
    ------
    Corpus: make_rounds_corpus(n_repeats=15) -> n=30 decisive matches (evolving tier).
    Archetypes: "Control" (Brainstorm main) vs "Combo" (Dark Ritual main).
    Per-card signal: Brainstorm has positive lift vs Combo (Control wins 2x/repeat).

    Maindeck for "Control" archetype: we craft a maindeck where:
    - "DeadCard" is a flex card with NO rounds data (fwv=0, lift=-something
      because we need a card that scores worse than "Brainstorm").
    - "Brainstorm" has proven positive lift vs Combo (n=30, evolving) -> high fwv.

    To make the swap happen in the greedy loop:
    - The maindeck has "DeadCard" in a flex slot (NOT Brainstorm).
    - The candidate pool (from card_frequencies on "Control" corpus) includes
      Brainstorm.
    - fwv[Brainstorm] > fwv[DeadCard] -> greedy swaps them.

    Wait: the make_rounds_corpus "Control" archetype has Brainstorm in the main
    (all 10 "Control" decks run it). So Brainstorm has high inclusion -> LOCKED.
    We need to pass a maindeck that has a genuinely flex card (low/zero fwv) and
    does NOT have the high-fwv card.

    Adjusted design:
    - Use archetype "Control" with since="2025-01-01" to get real data.
    - Maindeck: 59 copies of Island (locked, or all flex -- doesn't matter, they
      have no fwv signal since Island isn't in the corpus at all) + 1 copy of
      "Dark Ritual" (a flex slot).  Dark Ritual is a COMBO card that loses vs
      Control -> if "Control" is the archetype and field has "Combo" only, then
      we expect Dark Ritual to have negative lift vs Combo opponents from Control's
      perspective: wait, we need to think carefully.

    Better design:
    - From Control's perspective vs Combo: Brainstorm (Control main) wins -> high
      fwv[Brainstorm vs Combo]; Dark Ritual (Combo main, LOSER) -> when attributed
      to the loser, Dark Ritual vs Control gets losses, NOT wins. So from Control's
      perspective, Dark Ritual has negative matchup-n vs Control.

    The key: field_weighted_values computes fwv for cards "as a Control player"
    (board="main", vs opponent "Combo"). So:
    - "Brainstorm" in main vs "Combo" -> n=30 wins, 0 losses -> high positive lift.
    - "Dark Ritual" in main vs "Combo" is never in Control's main -> no entry ->
      lift=0.0 (treated as speculative/no-data).

    BUT we need Dark Ritual IN the starting maindeck as a flex slot. Then fwv["Dark
    Ritual"] = 0.0 (no data) and fwv["Brainstorm"] > 0. Since 0.4 - 0.0 > 0, the
    greedy should swap Dark Ritual -> Brainstorm IF Dark Ritual is in the maindeck
    and Brainstorm is in the candidate pool.

    Maindeck design: 59x Island (fills 59 slots), 1x "Dark Ritual" (flex slot).
    total = 60. Island is a basic land -> unlimited copies, not in corpus -> fwv=0.
    Dark Ritual: fwv=0 (no data as a Control main card). Brainstorm: fwv=+X (proven).

    Candidate pool: card_frequencies(con, "Control") includes Brainstorm (all 10
    decks run it -> 100% inclusion -> LOCKED, not in pool but also is "high-inclusion"
    so it won't be cut from the maindeck anyway). Hmm -- but it IS in the pool.

    Let's check: candidate_pool returns ALL card names from card_frequencies(archetype,
    board="main"). So Brainstorm will be in the pool even though it's also locked.

    The _greedy_tune inner loop has a guard:
        if add_card in locked_cards and add_card in current_main: continue
    This prevents adding a card already IN the locked core OF THE CURRENT MAINDECK.
    Since Brainstorm is NOT currently in our maindeck (we start with Dark Ritual +
    Islands), Brainstorm is in locked_cards (it would be locked IF it were in the
    maindeck) but it is NOT in current_main. So the guard does NOT skip it!

    This means: the swap Dark Ritual -> Brainstorm is legal (Brainstorm not in main
    yet), gain > 0 -> it proceeds. After the swap, Brainstorm is in flex (not locked
    since it wasn't in the original locked partition -- wait, locked is computed from
    the starting maindeck, not the pool).

    Correction: locked is computed from partition_flex(starting_maindeck). Starting
    maindeck = {Island: 59, Dark Ritual: 1}. card_frequencies(con, "Control") will
    have Brainstorm with inclusion=1.0 -> threshold 0.65 -> Brainstorm would be locked
    IF it were in the starting maindeck. But it's NOT. So locked = {Island: 59} (if
    Islands have high inclusion... but "Control" in the corpus uses Brainstorm, not
    Islands).

    Let's trace: card_frequencies(con, "Control", board="main") returns the cards
    Control decks run: Brainstorm (4/4 = 100%). Island is not in the corpus at all
    -> inclusion=0.0 -> flex. Dark Ritual: 0/4 inclusion -> flex.

    So locked = {} (Island has 0% inclusion in Control, and Dark Ritual also 0%).
    flex = {Island: 59, Dark Ritual: 1}.
    pool = ["Brainstorm"] (the only card in Control's main corpus).

    fwv: Brainstorm has proven lift vs Combo, so fwv["Brainstorm"] > 0.
    fwv["Dark Ritual"] = 0.0 (not a Control main card, no entries).
    fwv["Island"] = 0.0 (not in corpus at all).

    gain of swapping Dark Ritual -> Brainstorm = fwv["Brainstorm"] - fwv["Dark Ritual"]
    = (some positive value) - 0.0 > 0. The swap proceeds!

    This test WILL exercise the real greedy path and produce value_after > value_before.
    """

    def test_tune_deck_swaps_on_rounds_corpus(self, make_rounds_corpus):
        """THE integration non-vacuous AC: tune_deck swaps on n=30 corpus (evolving tier)."""
        con, facts = make_rounds_corpus(n_repeats=15)
        # n=30 decisive matches -> Brainstorm (Control main) vs Combo: evolving tier

        # Field: 100% Combo (the opponent Control wants to beat)
        field = build_custom_field({"Combo": 1.0})

        # Maindeck: 59x Island (flex, no signal) + 1x Dark Ritual (flex, no signal as Control main card)
        # The candidate pool (card_frequencies for "Control") will include Brainstorm.
        # fwv[Brainstorm] > 0 -> greedy swaps Dark Ritual for Brainstorm.
        maindeck = {"Island": 59, "Dark Ritual": 1}
        assert sum(maindeck.values()) == 60

        result = tune_deck(
            con, "Control", maindeck, {},
            field=field,
            since="2025-01-01",   # wide window to include 2026-01 fixture corpus
        )

        # The central AC, asserted UNCONDITIONALLY to harden against a silent vacuous
        # regression: an n=30 corpus MUST produce evolving-tier per-card signal, so the
        # real swap path MUST run (no fallback). If a future fixture change pushed this
        # into the fallback branch, this assertion fails loudly rather than degrading to
        # a vacuous warning. (Deep-review nit, 2026-05-31.)
        assert result.fell_back is False, (
            f"n=30 corpus must yield per-card signal and run the real swap path, not the "
            f"no-signal fallback — vacuous-test guard. reason={result.reason!r}"
        )
        assert result.objective == "per-card-value"
        # Per-card signal found: value must strictly improve and at least one swap happens.
        assert result.value_after > result.value_before, (
            f"value_after ({result.value_after:.4f}) must be STRICTLY greater than "
            f"value_before ({result.value_before:.4f}); swaps={result.swaps}"
        )
        assert len(result.swaps) > 0, (
            f"Expected at least 1 swap when per-card signal present; swaps={result.swaps}"
        )

        # Regardless of path: these must always hold
        assert result.legality_errors == [], (
            f"legality_errors must always be [] on return; got {result.legality_errors}"
        )
        assert sum(result.maindeck.values()) == 60
        assert isinstance(result.matchup_plans, dict)
        con.close()

    def test_tune_deck_computes_card_winrates_exactly_once(self, make_rounds_corpus, monkeypatch):
        """Perf guard (idea-tuning-sideboard-winrate-reuse): the heavy compute_card_winrates
        full-corpus scan runs ONCE per tune_deck — threaded through field_weighted_values +
        recommend_sideboard's two passes — not 3x. Regresses silently without this assertion."""
        import legacy_engine.analytics.match_results as mr

        con, _facts = make_rounds_corpus(n_repeats=15)  # gate-clearing → exercises the plan path too
        field = build_custom_field({"Combo": 1.0})

        real = mr.compute_card_winrates
        calls = {"n": 0}

        def _counting(*args, **kwargs):
            calls["n"] += 1
            return real(*args, **kwargs)

        monkeypatch.setattr(mr, "compute_card_winrates", _counting)

        result = tune_deck(con, "Control", {"Island": 59, "Dark Ritual": 1}, {}, field=field, since="2025-01-01")

        assert result.fell_back is False  # ensure the gate-clearing path (which also plans) actually ran
        assert calls["n"] == 1, (
            f"compute_card_winrates must run exactly once per tune_deck (threaded aggregate); "
            f"ran {calls['n']}x"
        )
        con.close()

    def test_tune_deck_no_signal_fallback_thin_corpus(self, make_rounds_corpus):
        """With n_repeats=1 (speculative, n=2 < 30), no gate-clearing signal -> fell_back=True."""
        con, facts = make_rounds_corpus(n_repeats=1)
        # n=2 decisive matches -> all cells are speculative tier -> gate fails

        field = build_custom_field({"Combo": 1.0})
        maindeck = {"Island": 59, "Dark Ritual": 1}
        assert sum(maindeck.values()) == 60

        result = tune_deck(
            con, "Control", maindeck, {},
            field=field,
            since="2025-01-01",
        )

        # With n=2 (speculative), the gate should NOT clear -> fell_back=True
        # (all cells are speculative -> fwv all zeros -> has_value_signal=False)
        # This is the correct honest behavior: don't fabricate an edge from thin data.
        assert result.fell_back is True, (
            f"Expected fell_back=True with speculative-only data (n=2); "
            f"fell_back={result.fell_back}, reason={result.reason!r}"
        )
        assert result.objective == "no-signal-skip"
        assert result.swaps == []
        assert result.legality_errors == []
        assert isinstance(result.matchup_plans, dict)
        con.close()

    def test_tune_deck_legality_errors_always_empty(self, make_rounds_corpus):
        """Unit 3 guarantee: returned TunedDeck always has legality_errors == []."""
        con, facts = make_rounds_corpus(n_repeats=15)
        field = build_custom_field({"Combo": 1.0})
        maindeck = {"Island": 59, "Dark Ritual": 1}

        result = tune_deck(
            con, "Control", maindeck, {},
            field=field,
            since="2025-01-01",
        )
        assert result.legality_errors == [], (
            f"legality_errors must ALWAYS be [] on return (Unit 3 guarantee); "
            f"got {result.legality_errors}"
        )
        con.close()

    def test_matchup_plans_is_dict(self, make_rounds_corpus):
        """matchup_plans is always a dict (may be empty if no per-card data gates)."""
        con, facts = make_rounds_corpus(n_repeats=15)
        field = build_custom_field({"Combo": 1.0})
        maindeck = {"Island": 59, "Dark Ritual": 1}

        result = tune_deck(
            con, "Control", maindeck, {},
            field=field,
            since="2025-01-01",
        )
        assert isinstance(result.matchup_plans, dict)
        con.close()

    def test_final_legality_revert_path(self, make_rounds_corpus, monkeypatch):
        """Final-legality revert path: when validate_deck fails after greedy, tune_deck
        reverts to the consensus (input) maindeck + empty sideboard and returns
        legality_errors == [].

        Strategy:
        1. Monkeypatch recommend_sideboard in legacy_engine.generation.tuning to
           return a SideboardPackage containing a synthetic card "SYNTHETIC_BANNED"
           in its cards dict.
        2. Monkeypatch validate_deck in the same module to fail when it sees
           "SYNTHETIC_BANNED" in the combined deck (simulating a banned card).
           All other validation calls (including _legal_swap_maindeck during greedy)
           pass through to the real implementation.
        3. Assert:
           - legality_errors == [] (guarantee always holds)
           - "REVERTED" in result.reason (revert branch fired)
           - result.maindeck == input_maindeck (consensus main returned)
           - result.fell_back is False (greedy path ran → revert is non-vacuous)
        """
        import legacy_engine.generation.tuning as _tuning_mod
        from legacy_engine.advisory.sideboard import SideboardPackage
        from legacy_engine.ingestion.banlist import validate_deck as _real_validate_deck

        con, _facts = make_rounds_corpus(n_repeats=15)  # n=30 → evolving, greedy fires
        field = build_custom_field({"Combo": 1.0})
        input_maindeck = {"Island": 59, "Dark Ritual": 1}

        # Stub recommend_sideboard to return a sideboard with a synthetic bad card.
        _SENTINEL = "SYNTHETIC_BANNED"

        def _stub_recommend_sideboard(con_arg, field_arg, deck_arg, **kwargs):
            return SideboardPackage(
                cards={_SENTINEL: 1},
                trace=[],
                covered_weight=0.0,
                budget=15,
                reserved=0,
                solver_used="greedy",
                field_source=field_arg.field_source,
                heuristic_note="stub",
                warnings=(),
                matchup_plans={},
                value_informed=False,
                plan_window=(None, None),
            )

        def _patched_validate_deck(maindeck_arg, sideboard_arg, snapshot_arg=None):
            """Fail when the sentinel bad card appears anywhere."""
            combined = dict(maindeck_arg)
            for card, count in (sideboard_arg or {}).items():
                combined[card] = combined.get(card, 0) + count
            if _SENTINEL in combined:
                return [f"{_SENTINEL} is banned (synthetic test error)"]
            return _real_validate_deck(maindeck_arg, sideboard_arg, snapshot_arg)

        monkeypatch.setattr(_tuning_mod, "recommend_sideboard", _stub_recommend_sideboard)
        monkeypatch.setattr(_tuning_mod, "validate_deck", _patched_validate_deck)

        result = tune_deck(
            con, "Control", input_maindeck, {},
            field=field,
            since="2025-01-01",
        )

        try:
            # Core guarantee: legality_errors must always be [] on return.
            assert result.legality_errors == [], (
                f"legality_errors must be [] after revert; got {result.legality_errors}"
            )

            # Revert assertion 1: reason must mention REVERTED.
            assert "REVERTED" in result.reason, (
                f"Expected 'REVERTED' in reason after legality failure; "
                f"reason={result.reason!r}"
            )

            # Revert assertion 2: maindeck must equal the consensus input exactly.
            assert result.maindeck == dict(input_maindeck), (
                f"After revert, maindeck must be the consensus input; "
                f"result.maindeck={result.maindeck}"
            )

            # Non-vacuousness: the corpus has evolving-tier per-card data, so the
            # greedy path must have run (fell_back=False).  If fell_back=True here,
            # the corpus shrank and the revert assertion is vacuous — fail loudly.
            assert result.fell_back is False, (
                f"Expected fell_back=False (greedy path ran) so the revert is "
                f"non-vacuous; fell_back={result.fell_back}, reason={result.reason!r}"
            )
        finally:
            con.close()


# ---------------------------------------------------------------------------
# CLI output tests — updated for rework output format
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
        """Output must include 'Coverage' (audit context line in header)."""
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
        assert "Coverage" in result.output

    def test_tune_output_contains_value_line(self, deck_file, db_path):
        """Output must include 'Value' (per-card field-weighted objective)."""
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
        assert "Value" in result.output

    def test_tune_fallback_note_when_thin(self, deck_file, db_path):
        """Since TuneDelver has no rounds, output should include [FALLBACK] note."""
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
        """Output contains a 'Swap log' section."""
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

    def test_tune_no_signal_note_in_output(self, deck_file, db_path):
        """TuneDelver (no rounds) -> output contains 'no-signal' or 'no swaps' indicator."""
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
        # Either the FALLBACK note or 'no-signal' appears (both indicate thin data)
        output_lower = result.output.lower()
        assert "fallback" in output_lower or "no-signal" in output_lower or "no swaps" in output_lower, (
            f"Expected fallback/no-signal note in output for thin corpus. Output:\n{result.output}"
        )

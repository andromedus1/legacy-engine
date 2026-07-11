"""Tests for the per-camp win-rate extension to analytics.subgroup — Unit 4 of
epic-subarchetype-resolution-card-winrate.

``subgroup_compositions(..., with_winrates=True)`` computes each camp's decisive match
win-rate (wins/n) restricted to decks belonging to the requested archetype, split by
presence/absence of the signature card. Default ``with_winrates=False`` must leave the
four new SubgroupSplit fields ``None`` and must not run the extra query at all (gated-
additive; byte-identical to the pre-existing behaviour, covered separately in
test_byte_identical_defaults.py).
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics.subgroup import SubgroupSplit, subgroup_compositions
from legacy_engine.confidence import tier_for_sample
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item


def _card(name: str, count: int = 4) -> dict:
    return {"CardName": name, "Count": count}


def _deck(player: str, main: list[dict]) -> dict:
    return {"Player": player, "Result": "1st", "Mainboard": main, "Sideboard": []}


def _build_camp_split_corpus() -> dict:
    """Dimir Tempo split into a with-Bauble camp (2W/1L) and a without-Bauble camp (1W/2L).

    Plus one archetype-level mirror (Dimir Tempo vs Dimir Tempo) that must be excluded
    from every counter, matching the project's existing mirror-exclusion convention.
    """
    decks = [
        _deck("bauble_0", [_card("Mishra's Bauble"), _card("Brainstorm")]),
        _deck("bauble_1", [_card("Mishra's Bauble"), _card("Brainstorm")]),
        _deck("bauble_2", [_card("Mishra's Bauble"), _card("Brainstorm")]),
        _deck("nobauble_0", [_card("Barrowgoyf"), _card("Brainstorm")]),
        _deck("nobauble_1", [_card("Barrowgoyf"), _card("Brainstorm")]),
        _deck("nobauble_2", [_card("Barrowgoyf"), _card("Brainstorm")]),
        _deck("opp_0", [_card("Filler")]),
        _deck("opp_1", [_card("Filler")]),
        _deck("opp_2", [_card("Filler")]),
        _deck("opp_3", [_card("Filler")]),
        _deck("opp_4", [_card("Filler")]),
        _deck("opp_5", [_card("Filler")]),
        # Mirror pair — both Dimir Tempo, must be excluded entirely.
        _deck("bauble_mirror", [_card("Mishra's Bauble"), _card("Brainstorm")]),
        _deck("nobauble_mirror", [_card("Barrowgoyf"), _card("Brainstorm")]),
    ]
    rounds = [
        {"Player1": "bauble_0", "Player2": "opp_0", "Result": "2-0"},   # with wins
        {"Player1": "bauble_1", "Player2": "opp_1", "Result": "2-0"},   # with wins
        {"Player1": "opp_2", "Player2": "bauble_2", "Result": "2-0"},   # with loses
        {"Player1": "opp_3", "Player2": "nobauble_0", "Result": "2-0"},  # without loses
        {"Player1": "opp_4", "Player2": "nobauble_1", "Result": "2-0"},  # without loses
        {"Player1": "nobauble_2", "Player2": "opp_5", "Result": "2-0"},  # without wins
        # Archetype-level mirror — excluded from camp win-rates (same convention as
        # compute_match_results/compute_card_winrates).
        {"Player1": "bauble_mirror", "Player2": "nobauble_mirror", "Result": "2-0"},
    ]
    return {
        "Tournament": {
            "Name": "Camp Split Test", "Date": "2026-06-01",
            "Uri": "https://test.com/camp-split", "Formats": "Legacy",
        },
        "Decks": decks,
        "Rounds": rounds,
        "Standings": [],
    }


@pytest.fixture
def camp_split_con():
    con = store.connect(":memory:")
    store.init_schema(con)
    store.load_tournament(con, parse_cache_item(_build_camp_split_corpus(), "MTGO"))
    con.execute(
        "UPDATE decks SET archetype = 'Dimir Tempo' "
        "WHERE player IN ('bauble_0','bauble_1','bauble_2','nobauble_0','nobauble_1',"
        "'nobauble_2','bauble_mirror','nobauble_mirror')"
    )
    con.execute(
        "UPDATE decks SET archetype = 'Opponent Pool' "
        "WHERE player IN ('opp_0','opp_1','opp_2','opp_3','opp_4','opp_5')"
    )
    yield con
    con.close()


class TestSubgroupWinrateDefaultOff:
    """with_winrates=False (the default) leaves the new fields None."""

    def test_fields_none_by_default(self, camp_split_con):
        split = subgroup_compositions(
            camp_split_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-01-01", until="2027-01-01",
        )
        assert split.wins_with is None
        assert split.n_matches_with is None
        assert split.wins_without is None
        assert split.n_matches_without is None


class TestSubgroupWinrateComputed:
    """with_winrates=True computes the per-camp W/L split from rounds."""

    def test_with_camp_wins_and_n(self, camp_split_con):
        split = subgroup_compositions(
            camp_split_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-01-01", until="2027-01-01", with_winrates=True,
        )
        assert split.wins_with == 2
        assert split.n_matches_with == 3

    def test_without_camp_wins_and_n(self, camp_split_con):
        split = subgroup_compositions(
            camp_split_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-01-01", until="2027-01-01", with_winrates=True,
        )
        assert split.wins_without == 1
        assert split.n_matches_without == 3

    def test_mirror_excluded_from_both_camps(self, camp_split_con):
        """The archetype-level mirror (bauble_mirror vs nobauble_mirror) contributes to neither
        camp — Σ(n_matches_with, n_matches_without) == 6, not 7."""
        split = subgroup_compositions(
            camp_split_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-01-01", until="2027-01-01", with_winrates=True,
        )
        assert split.n_matches_with + split.n_matches_without == 6

    def test_thin_win_rate_sample_matches_tier_for_sample(self, camp_split_con):
        """n=3 for both camps → speculative tier (below the n<30 floor)."""
        split = subgroup_compositions(
            camp_split_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-01-01", until="2027-01-01", with_winrates=True,
        )
        assert tier_for_sample(split.n_matches_with) == "speculative"
        assert tier_for_sample(split.n_matches_without) == "speculative"

    def test_returns_subgroup_split_instance(self, camp_split_con):
        split = subgroup_compositions(
            camp_split_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-01-01", until="2027-01-01", with_winrates=True,
        )
        assert isinstance(split, SubgroupSplit)

    def test_composition_diffs_unaffected_by_with_winrates_flag(self, camp_split_con):
        """Turning on with_winrates must not change the (unrelated) composition diffs."""
        split_off = subgroup_compositions(
            camp_split_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-01-01", until="2027-01-01", with_winrates=False,
        )
        split_on = subgroup_compositions(
            camp_split_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-01-01", until="2027-01-01", with_winrates=True,
        )
        assert split_off.diffs == split_on.diffs
        assert split_off.n_with == split_on.n_with
        assert split_off.n_without == split_on.n_without


class TestSubgroupWinrateEmptyArchetype:
    def test_nonexistent_archetype_zero_matches(self, camp_split_con):
        split = subgroup_compositions(
            camp_split_con, "Nonexistent Archetype", "Mishra's Bauble",
            since="2026-01-01", until="2027-01-01", with_winrates=True,
        )
        assert split.wins_with == 0
        assert split.n_matches_with == 0
        assert split.wins_without == 0
        assert split.n_matches_without == 0

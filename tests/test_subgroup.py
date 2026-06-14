"""Tests for analytics.subgroup — subgroup-diff tool (Unit 1 of feature-subarchetype-variants).

House style: pure hand-built-input tests for diff_compositions; one DB-backed test reproducing
the shape of the validated Dimir-Tempo-on-Bauble result; thin-subgroup flagging.
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics.subgroup import CardDiff, SubgroupSplit, diff_compositions, subgroup_compositions
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item


# ---------------------------------------------------------------------------
# Pure unit tests — diff_compositions (no DB)
# ---------------------------------------------------------------------------

class TestDiffCompositions:
    def test_basic_delta_signs(self):
        with_avg = {"Brainstorm": 4.0, "Daze": 3.5, "Force of Will": 4.0}
        without_avg = {"Brainstorm": 4.0, "Daze": 3.0, "Barrowgoyf": 2.0}
        diffs = diff_compositions(with_avg, without_avg)
        by_name = {d.name: d for d in diffs}
        assert by_name["Daze"].delta == pytest.approx(0.5)
        assert by_name["Barrowgoyf"].delta == pytest.approx(-2.0)  # only in without
        assert by_name["Brainstorm"].delta == pytest.approx(0.0)
        assert by_name["Force of Will"].delta == pytest.approx(4.0)  # only in with

    def test_sorted_by_abs_delta_descending(self):
        with_avg = {"A": 4.0, "B": 2.0, "C": 1.0}
        without_avg = {"A": 1.0, "B": 2.5, "C": 0.0}
        diffs = diff_compositions(with_avg, without_avg)
        abs_deltas = [abs(d.delta) for d in diffs]
        assert abs_deltas == sorted(abs_deltas, reverse=True)

    def test_card_only_in_with_gets_zero_without(self):
        with_avg = {"Nethergoyf": 2.43}
        without_avg: dict[str, float] = {}
        diffs = diff_compositions(with_avg, without_avg)
        assert len(diffs) == 1
        d = diffs[0]
        assert d.avg_with == pytest.approx(2.43)
        assert d.avg_without == pytest.approx(0.0)
        assert d.delta == pytest.approx(2.43)

    def test_card_only_in_without_gets_zero_with(self):
        with_avg: dict[str, float] = {}
        without_avg = {"Barrowgoyf": 1.06}
        diffs = diff_compositions(with_avg, without_avg)
        assert len(diffs) == 1
        d = diffs[0]
        assert d.avg_with == pytest.approx(0.0)
        assert d.avg_without == pytest.approx(1.06)
        assert d.delta == pytest.approx(-1.06)

    def test_empty_inputs_returns_empty(self):
        assert diff_compositions({}, {}) == []

    def test_both_empty_is_symmetric(self):
        diffs = diff_compositions({}, {})
        assert diffs == []

    def test_identical_inputs_all_zero_delta(self):
        avg = {"Brainstorm": 4.0, "Wasteland": 3.5}
        diffs = diff_compositions(avg, avg)
        for d in diffs:
            assert d.delta == pytest.approx(0.0)

    def test_deterministic_tie_break_by_name(self):
        """Two cards with equal |delta| — sort should be stable by name."""
        with_avg = {"Alpha": 3.0, "Beta": 1.0}
        without_avg = {"Alpha": 1.0, "Beta": 3.0}
        diffs = diff_compositions(with_avg, without_avg)
        # Both have |delta|=2.0; tie-break by name: Alpha before Beta.
        assert diffs[0].name == "Alpha"
        assert diffs[1].name == "Beta"

    def test_negative_delta_for_without_dominant_card(self):
        """A card more prevalent in without → negative delta."""
        diffs = diff_compositions({"X": 1.0}, {"X": 3.5})
        assert diffs[0].delta == pytest.approx(-2.5)


# ---------------------------------------------------------------------------
# DB-backed test — reproduces the shape of the validated result
# ---------------------------------------------------------------------------

def _make_card(name: str, count: int = 4) -> dict:
    return {"CardName": name, "Count": count}


def _make_deck_raw(player: str, main: list[dict], side: list[dict] | None = None) -> dict:
    return {"Player": player, "Result": "1st Place", "Mainboard": main, "Sideboard": side or []}


def _build_bauble_tournament() -> dict:
    """12 decks split ~8 with Mishra's Bauble, ~4 without.

    With-Bauble decks: Mishra's Bauble + Nethergoyf (extra 2) + Daze (extra 1).
    Without-Bauble decks: Barrowgoyf instead of Nethergoyf.

    Expected Δ shape (mirrors the validated method):
    - Bauble:      only in with → delta > 0
    - Nethergoyf:  with > without → delta > 0
    - Barrowgoyf:  without > with → delta < 0
    """
    decks = []
    for i in range(8):  # with-Bauble decks
        main = [
            _make_card("Mishra's Bauble", 4),
            _make_card("Nethergoyf", 4),      # avg ~4 in with
            _make_card("Daze", 4),
            _make_card("Brainstorm", 4),
            _make_card("Force of Will", 4),
            _make_card("Wasteland", 4),
            _make_card("Underground Sea", 4),
            _make_card("Polluted Delta", 4),
        ]
        decks.append(_make_deck_raw(f"bauble_{i}", main))

    for i in range(4):  # without-Bauble decks
        main = [
            _make_card("Barrowgoyf", 4),      # avg ~4 in without, ~0 in with
            _make_card("Nethergoyf", 2),      # avg ~2 in without (less than with)
            _make_card("Daze", 3),
            _make_card("Brainstorm", 4),
            _make_card("Force of Will", 4),
            _make_card("Wasteland", 4),
            _make_card("Underground Sea", 4),
            _make_card("Polluted Delta", 4),
        ]
        decks.append(_make_deck_raw(f"no_bauble_{i}", main))

    return {
        "Tournament": {
            "Name": "Subgroup Test Tourney",
            "Date": "2026-05-25",
            "Uri": "https://test.com/subgroup",
            "Formats": "Legacy",
        },
        "Decks": decks,
        "Rounds": [],
        "Standings": [],
    }


@pytest.fixture
def subgroup_con():
    con = store.connect(":memory:")
    store.init_schema(con)
    store.load_tournament(con, parse_cache_item(_build_bauble_tournament(), "MTGO"))
    con.execute("UPDATE decks SET archetype = 'Dimir Tempo'")
    yield con
    con.close()


class TestSubgroupCompositions:
    def test_n_with_and_n_without(self, subgroup_con):
        split = subgroup_compositions(
            subgroup_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-05-01", until=None,
        )
        assert split.n_with == 8
        assert split.n_without == 4

    def test_bauble_delta_positive(self, subgroup_con):
        """Mishra's Bauble itself appears only in the with-subgroup → delta > 0."""
        split = subgroup_compositions(
            subgroup_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-05-01", until=None,
        )
        by_name = {d.name: d for d in split.diffs}
        assert "Mishra's Bauble" in by_name
        assert by_name["Mishra's Bauble"].delta > 0

    def test_barrowgoyf_delta_negative(self, subgroup_con):
        """Barrowgoyf is only in the without-subgroup → delta < 0."""
        split = subgroup_compositions(
            subgroup_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-05-01", until=None,
        )
        by_name = {d.name: d for d in split.diffs}
        assert "Barrowgoyf" in by_name
        assert by_name["Barrowgoyf"].delta < 0

    def test_nethergoyf_higher_in_with(self, subgroup_con):
        """Nethergoyf runs 4 in with-decks vs 2 in without → delta > 0."""
        split = subgroup_compositions(
            subgroup_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-05-01", until=None,
        )
        by_name = {d.name: d for d in split.diffs}
        assert by_name["Nethergoyf"].delta > 0

    def test_sorted_by_abs_delta(self, subgroup_con):
        split = subgroup_compositions(
            subgroup_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-05-01", until=None,
        )
        abs_deltas = [abs(d.delta) for d in split.diffs]
        assert abs_deltas == sorted(abs_deltas, reverse=True)

    def test_returns_subgroup_split(self, subgroup_con):
        split = subgroup_compositions(
            subgroup_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-05-01", until=None,
        )
        assert isinstance(split, SubgroupSplit)
        assert split.archetype == "Dimir Tempo"
        assert split.signature_card == "Mishra's Bauble"

    def test_thin_flagging_when_n_below_30(self, subgroup_con):
        """With n=8 and n=4, both subgroups are speculative → thin=True."""
        split = subgroup_compositions(
            subgroup_con, "Dimir Tempo", "Mishra's Bauble",
            since="2026-05-01", until=None,
        )
        assert split.thin is True
        assert split.tier_with == "speculative"
        assert split.tier_without == "speculative"

    def test_empty_archetype_returns_empty_diffs(self, subgroup_con):
        split = subgroup_compositions(
            subgroup_con, "Nonexistent Archetype", "Brainstorm",
            since="2026-05-01", until=None,
        )
        assert split.n_with == 0
        assert split.n_without == 0
        assert split.diffs == []

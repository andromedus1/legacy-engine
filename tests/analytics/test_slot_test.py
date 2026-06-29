"""Tests for the matchup-conditioned sideboard-slot test (analytics/slot_test.py).

Covers:
- Exact with/without buckets on a hand-built corpus.
- No fan-out on a duplicate (tournament, player) deck row (engine-dedup parity).
- Wilson CIs + Fisher significance: a constructed significant vs non-significant split.
- Empty cohort (card in 0 / all decks) → None p/ci/diff, no exception.
- Mirror / draw / bye exclusion parity with compute_match_results.
- cards=None scans all cards the archetype runs on the board.
"""

from __future__ import annotations

from legacy_engine.analytics.slot_test import card_matchup_contrast, pair_adaptive_since
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item


# ---------------------------------------------------------------------------
# Hermetic corpus builder — full control over ownership + outcomes
# ---------------------------------------------------------------------------

def _deck(player: str, *, main: list[str], side: list[str]) -> dict:
    return {
        "Player": player,
        "Result": "1st",
        "Mainboard": [{"Count": 1, "CardName": c} for c in main],
        "Sideboard": [{"Count": 1, "CardName": c} for c in side],
    }


def _build(con, tid_suffix: str, decks: list[dict], rounds: list[dict],
           labels: dict[str, str], *, date: str = "2026-03-01") -> str:
    raw = {
        "Tournament": {
            "Name": f"Slot Test {tid_suffix}",
            "Date": date,
            "Uri": f"https://www.mtgo.com/decklist/slot-test-{tid_suffix}",
            "Formats": "Legacy",
        },
        "Decks": decks,
        "Rounds": rounds,
        "Standings": [],
    }
    tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
    for player, arch in labels.items():
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            [arch, tid, player],
        )
    return tid


def _con():
    return store.connect(":memory:")


# ---------------------------------------------------------------------------
# Buckets + exclusions
# ---------------------------------------------------------------------------

class TestBuckets:
    def test_with_without_split_and_exclusions(self):
        con = _con()
        # Hero "Tempo" vs "Foe". hero_tech / hero_plain own/don't-own "Tech" in side.
        decks = [
            _deck("hero_tech", main=["Bolt"], side=["Tech"]),
            _deck("hero_plain", main=["Bolt"], side=["Filler"]),
            _deck("foe1", main=["Rock"], side=[]),
            _deck("foe2", main=["Rock"], side=[]),
            _deck("hero_mirror", main=["Bolt"], side=["Tech"]),
        ]
        rounds = [
            {"Player1": "hero_tech", "Player2": "foe1", "Result": "2-0"},    # WITH wins
            {"Player1": "foe2", "Player2": "hero_tech", "Result": "2-1"},    # WITH loses
            {"Player1": "hero_plain", "Player2": "foe1", "Result": "0-2"},   # WITHOUT loses
            {"Player1": "hero_tech", "Player2": "hero_mirror", "Result": "2-0"},  # mirror → excluded
            {"Player1": "hero_plain", "Player2": "foe2", "Result": "1-1"},   # draw → excluded
        ]
        labels = {"hero_tech": "Tempo", "hero_plain": "Tempo", "hero_mirror": "Tempo",
                  "foe1": "Foe", "foe2": "Foe"}
        _build(con, "1", decks, rounds, labels)

        report = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=["Tech"])
        assert not report.degraded
        # 3 decisive Tempo-vs-Foe matches (mirror + draw excluded)
        assert report.n_matches == 3
        cell = report.cells[0]
        assert cell.card == "Tech"
        assert (cell.w_with, cell.n_with) == (1, 2)       # hero_tech: 1 win, 1 loss
        assert (cell.w_without, cell.n_without) == (0, 1)  # hero_plain: 1 loss
        assert cell.p_with == 0.5
        assert cell.p_without == 0.0
        assert cell.diff == 0.5
        con.close()

    def test_no_fanout_on_duplicate_player(self):
        con = _con()
        # Two decks share the normalized player name within one tournament → ambiguous → dropped,
        # NOT fanned out into inflated n.
        decks = [
            _deck("dup", main=["Bolt"], side=["Tech"]),
            _deck("Dup", main=["Bolt"], side=["Filler"]),  # normalizes to same "dup"
            _deck("foe1", main=["Rock"], side=[]),
        ]
        rounds = [{"Player1": "dup", "Player2": "foe1", "Result": "2-0"}]
        labels = {"dup": "Tempo", "Dup": "Tempo", "foe1": "Foe"}
        _build(con, "dup", decks, rounds, labels)

        report = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=["Tech"])
        # The only Tempo-vs-Foe round involves an ambiguous hero → dropped.
        assert report.degraded
        assert report.n_matches == 0
        con.close()


# ---------------------------------------------------------------------------
# Stats: significance + CIs + empty cohorts
# ---------------------------------------------------------------------------

class TestStats:
    def _lopsided(self, con):
        """WITH cohort all-wins, WITHOUT cohort all-losses, several copies → significant."""
        decks, rounds, labels = [], [], {}
        for i in range(8):
            w, l = f"win{i}", f"foew{i}"
            decks += [_deck(w, main=["Bolt"], side=["Tech"]), _deck(l, main=["Rock"], side=[])]
            rounds.append({"Player1": w, "Player2": l, "Result": "2-0"})  # WITH wins
            labels[w] = "Tempo"; labels[l] = "Foe"
        for i in range(8):
            p, f = f"plain{i}", f"foep{i}"
            decks += [_deck(p, main=["Bolt"], side=["Filler"]), _deck(f, main=["Rock"], side=[])]
            rounds.append({"Player1": f, "Player2": p, "Result": "2-0"})  # WITHOUT loses
            labels[p] = "Tempo"; labels[f] = "Foe"
        _build(con, "lop", decks, rounds, labels)

    def test_significant_split_flagged(self):
        con = _con()
        self._lopsided(con)
        report = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=["Tech"])
        cell = report.cells[0]
        assert (cell.w_with, cell.n_with) == (8, 8)
        assert (cell.w_without, cell.n_without) == (0, 8)
        assert cell.p_value is not None and cell.p_value < 0.05
        assert cell.significant is True
        assert cell.ci_with is not None and cell.ci_without is not None
        con.close()

    def test_near_5050_not_significant(self):
        con = _con()
        # WITH 1/2, WITHOUT 1/2 → no signal.
        decks = [
            _deck("hw", main=["Bolt"], side=["Tech"]), _deck("hw2", main=["Bolt"], side=["Tech"]),
            _deck("hp", main=["Bolt"], side=["Filler"]), _deck("hp2", main=["Bolt"], side=["Filler"]),
            _deck("f1", main=["Rock"], side=[]), _deck("f2", main=["Rock"], side=[]),
            _deck("f3", main=["Rock"], side=[]), _deck("f4", main=["Rock"], side=[]),
        ]
        rounds = [
            {"Player1": "hw", "Player2": "f1", "Result": "2-0"},   # with win
            {"Player1": "f2", "Player2": "hw2", "Result": "2-0"},  # with loss
            {"Player1": "hp", "Player2": "f3", "Result": "2-0"},   # without win
            {"Player1": "f4", "Player2": "hp2", "Result": "2-0"},  # without loss
        ]
        labels = {"hw": "Tempo", "hw2": "Tempo", "hp": "Tempo", "hp2": "Tempo",
                  "f1": "Foe", "f2": "Foe", "f3": "Foe", "f4": "Foe"}
        _build(con, "even", decks, rounds, labels)
        report = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=["Tech"])
        cell = report.cells[0]
        assert cell.diff == 0.0
        assert cell.p_value is not None and cell.p_value > 0.05
        assert cell.significant is False
        con.close()

    def test_empty_cohort_returns_none(self):
        con = _con()
        # No Tempo deck owns "Ghost" → WITH cohort empty.
        decks = [
            _deck("h1", main=["Bolt"], side=["Filler"]),
            _deck("f1", main=["Rock"], side=[]),
        ]
        rounds = [{"Player1": "h1", "Player2": "f1", "Result": "2-0"}]
        labels = {"h1": "Tempo", "f1": "Foe"}
        _build(con, "empty", decks, rounds, labels)
        report = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=["Ghost"])
        cell = report.cells[0]
        assert cell.n_with == 0
        assert cell.p_with is None and cell.ci_with is None
        assert cell.diff is None and cell.p_value is None and cell.significant is False
        con.close()


class TestWindowing:
    def test_explicit_window_restricts_matches(self):
        con = _con()
        # Two tournaments on different dates, each with one Tempo-vs-Foe match.
        for suffix, date in (("jan", "2026-01-15"), ("mar", "2026-03-15")):
            decks = [
                _deck(f"h_{suffix}", main=["Bolt"], side=["Tech"]),
                _deck(f"f_{suffix}", main=["Rock"], side=[]),
            ]
            rounds = [{"Player1": f"h_{suffix}", "Player2": f"f_{suffix}", "Result": "2-0"}]
            labels = {f"h_{suffix}": "Tempo", f"f_{suffix}": "Foe"}
            _build(con, suffix, decks, rounds, labels, date=date)

        full = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=["Tech"])
        assert full.n_matches == 2

        windowed = card_matchup_contrast(
            con, "Tempo", "Foe", board="side", cards=["Tech"],
            since="2026-02-01", until=None,
        )
        assert windowed.n_matches == 1   # only the March match falls in [2026-02-01, ∞)
        con.close()

    def test_pair_adaptive_since_none_when_unaffected(self):
        con = _con()
        # Archetypes that run no banned cards are never ban-affected → full corpus (None).
        decks = [_deck("h1", main=["Bolt"], side=["Tech"]), _deck("f1", main=["Rock"], side=[])]
        rounds = [{"Player1": "h1", "Player2": "f1", "Result": "2-0"}]
        _build(con, "adp", decks, rounds, {"h1": "Tempo", "f1": "Foe"})
        assert pair_adaptive_since(con, "Tempo", "Foe") is None
        con.close()


class TestThinTier:
    def test_small_cohort_is_speculative_and_flagged(self):
        con = _con()
        decks = [
            _deck("hw", main=["Bolt"], side=["Tech"]),
            _deck("hp", main=["Bolt"], side=["Filler"]),
            _deck("f1", main=["Rock"], side=[]),
            _deck("f2", main=["Rock"], side=[]),
        ]
        rounds = [
            {"Player1": "hw", "Player2": "f1", "Result": "2-0"},
            {"Player1": "hp", "Player2": "f2", "Result": "0-2"},
        ]
        labels = {"hw": "Tempo", "hp": "Tempo", "f1": "Foe", "f2": "Foe"}
        _build(con, "thin", decks, rounds, labels)
        report = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=["Tech"])
        cell = report.cells[0]
        assert cell.tier_with == "speculative"      # n=1 < 30
        assert cell.tier_without == "speculative"
        assert report.any_thin is True
        con.close()


class TestScan:
    def test_cards_none_scans_archetype_side_cards(self):
        con = _con()
        decks = [
            _deck("h1", main=["Bolt"], side=["Tech", "Filler"]),
            _deck("f1", main=["Rock"], side=[]),
        ]
        rounds = [{"Player1": "h1", "Player2": "f1", "Result": "2-0"}]
        labels = {"h1": "Tempo", "f1": "Foe"}
        _build(con, "scan", decks, rounds, labels)
        report = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=None)
        names = {c.card for c in report.cells}
        assert {"Tech", "Filler"} <= names
        con.close()

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

    def test_bye_and_unmatched_excluded(self):
        """A bye (empty p2) and an unmatched-archetype (None) row must not leak into the
        decisive count — exclusion parity with compute_match_results."""
        con = _con()
        decks = [
            _deck("hero_tech", main=["Bolt"], side=["Tech"]),
            _deck("foe1", main=["Rock"], side=[]),
            _deck("ghost", main=["Rock"], side=[]),  # left unlabeled below → archetype stays None
        ]
        rounds = [
            {"Player1": "hero_tech", "Player2": "foe1", "Result": "2-0"},   # decisive, counted
            {"Player1": "hero_tech", "Player2": "", "Result": "2-0"},       # bye — excluded
            {"Player1": "hero_tech", "Player2": "ghost", "Result": "2-0"},  # unmatched — excluded
        ]
        # "ghost" is intentionally NOT in labels → its archetype column stays NULL.
        labels = {"hero_tech": "Tempo", "foe1": "Foe"}
        _build(con, "bye-unmatched", decks, rounds, labels)

        report = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=["Tech"])
        assert not report.degraded
        assert report.n_matches == 1
        cell = report.cells[0]
        assert (cell.w_with, cell.n_with) == (1, 1)
        assert (cell.w_without, cell.n_without) == (0, 0)
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

    def test_sizeable_nonzero_diff_not_significant(self):
        """The 'Null Rod vs Blue Artifacts' cautionary case the module docstring warns about:
        a sizeable, non-zero point-estimate diff (~-8pt, WITH 38% n=71 vs WITHOUT 46% n=67) that
        is NOT significant. A degenerate 0.0-diff split (1/2 vs 1/2) would pass trivially and
        not actually exercise Fisher's exact on a realistic near-miss — this does."""
        con = _con()
        decks, rounds, labels = [], [], {}
        counter = 0

        def add(owns_card: bool, hero_wins: bool):
            nonlocal counter
            counter += 1
            h, f = f"h{counter}", f"f{counter}"
            side = ["Tech"] if owns_card else ["Filler"]
            decks.append(_deck(h, main=["Bolt"], side=side))
            decks.append(_deck(f, main=["Rock"], side=[]))
            rounds.append({"Player1": h, "Player2": f, "Result": "2-0" if hero_wins else "0-2"})
            labels[h] = "Tempo"
            labels[f] = "Foe"

        for _ in range(27):       # WITH cohort: 27/71 wins (38.0%)
            add(True, True)
        for _ in range(71 - 27):
            add(True, False)
        for _ in range(31):       # WITHOUT cohort: 31/67 wins (46.3%)
            add(False, True)
        for _ in range(67 - 31):
            add(False, False)

        _build(con, "realistic", decks, rounds, labels)
        report = card_matchup_contrast(con, "Tempo", "Foe", board="side", cards=["Tech"])
        cell = report.cells[0]
        assert (cell.w_with, cell.n_with) == (27, 71)
        assert (cell.w_without, cell.n_without) == (31, 67)
        assert cell.diff is not None and abs(cell.diff) > 0.05    # material, not the 0.0 degenerate case
        assert cell.p_value is not None and 0.05 < cell.p_value < 0.6   # non-significant, sane band
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

    def test_pair_adaptive_since_later_of_two(self):
        """Both archetypes ban-affected on DIFFERENT dates → adaptive since is the LATER date
        (mirrors build_adaptive_matrix; the ban-regime correctness core of the adaptive window)."""
        con = _con()
        # Hero ran Grief (banned 2024-08-26) in half its pre-ban decks → valid_since 2024-08-26.
        hero_decks = [
            _deck("h1", main=["Bolt", "Grief"], side=[]),
            _deck("h2", main=["Bolt", "Grief"], side=[]),
            _deck("h3", main=["Bolt"], side=[]),
            _deck("h4", main=["Bolt"], side=[]),
        ]
        _build(con, "hero-pre", hero_decks, [],
               {"h1": "Hero", "h2": "Hero", "h3": "Hero", "h4": "Hero"}, date="2024-06-01")

        # Opp ran Entomb (banned 2025-11-10) in half its pre-ban decks → valid_since 2025-11-10.
        opp_decks = [
            _deck("o1", main=["Rock", "Entomb"], side=[]),
            _deck("o2", main=["Rock", "Entomb"], side=[]),
            _deck("o3", main=["Rock"], side=[]),
            _deck("o4", main=["Rock"], side=[]),
        ]
        _build(con, "opp-pre", opp_decks, [],
               {"o1": "Opp", "o2": "Opp", "o3": "Opp", "o4": "Opp"}, date="2025-10-01")

        since = pair_adaptive_since(con, "Hero", "Opp")
        assert since == "2025-11-10"   # later of Hero's 2024-08-26 and Opp's 2025-11-10
        con.close()

    def test_pair_adaptive_since_one_affected_one_not(self):
        """Only one archetype in the pair is ban-affected → adaptive since equals that
        archetype's valid_since (not None, not the unaffected archetype's absence of one)."""
        con = _con()
        opp_decks = [
            _deck("o1", main=["Rock", "Entomb"], side=[]),
            _deck("o2", main=["Rock", "Entomb"], side=[]),
            _deck("o3", main=["Rock"], side=[]),
            _deck("o4", main=["Rock"], side=[]),
        ]
        _build(con, "opp-only-pre", opp_decks, [],
               {"o1": "Opp", "o2": "Opp", "o3": "Opp", "o4": "Opp"}, date="2025-10-01")

        clean_decks = [
            _deck("c1", main=["Bolt"], side=[]),
            _deck("c2", main=["Bolt"], side=[]),
        ]
        _build(con, "clean", clean_decks, [], {"c1": "Clean", "c2": "Clean"}, date="2025-10-01")

        assert pair_adaptive_since(con, "Clean", "Opp") == "2025-11-10"
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

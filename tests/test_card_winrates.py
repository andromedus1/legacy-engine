"""Tests for compute_card_winrates — Unit 1 of epic-deck-generation-per-card-value.

Covers:
- Pinned wins/n on the make_rounds_corpus seeded signal.
- No fan-out double-count invariant (Σ cell n ≤ resolved matches played).
- Byes/draws/mirror/ambiguous/unmatched exclusion parity with compute_match_results.
- since/until date windowing.
- Board-awareness (main vs side counted separately).
- CardWinRates structure + baseline_winrate.
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics.match_results import (
    CardMatchupRecord,
    CardMarginalRecord,
    CardWinRates,
    MatchCoverage,
    compute_card_winrates,
    compute_match_results,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item


def _con():
    return store.connect(":memory:")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_and_label(con, raw, source, labels: dict[str, str]):
    """Load tournament raw dict and apply archetype labels."""
    tid = store.load_tournament(con, parse_cache_item(raw, source))
    for player, arch in labels.items():
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            [arch, tid, player],
        )
    return tid


# ---------------------------------------------------------------------------
# Class TestPinnedSignal — exact wins/n from the seeded corpus fixture
# ---------------------------------------------------------------------------


class TestPinnedSignal:
    """Pinned wins/n for the seeded (Surgical Extraction, side, Combo) cell."""

    def test_seeded_cell_wins_n(self, make_rounds_corpus):
        con, facts = make_rounds_corpus()
        r = compute_card_winrates(con)
        sv = facts["surgical_vs_combo"]
        cell = r.matchup.get((sv["card"], sv["board"], sv["opponent"]))
        assert cell is not None, "seeded cell missing from matchup dict"
        assert cell.wins == sv["wins"]
        assert cell.n == sv["n"]
        assert cell.losses == sv["losses"]
        con.close()

    def test_brainstorm_main_vs_combo(self, make_rounds_corpus):
        con, facts = make_rounds_corpus()
        r = compute_card_winrates(con)
        bv = facts["brainstorm_vs_combo"]
        cell = r.matchup.get((bv["card"], bv["board"], bv["opponent"]))
        assert cell is not None
        assert cell.wins == bv["wins"]
        assert cell.n == bv["n"]
        con.close()

    def test_dark_ritual_main_vs_control_losses(self, make_rounds_corpus):
        con, facts = make_rounds_corpus()
        r = compute_card_winrates(con)
        dv = facts["dark_ritual_vs_control"]
        cell = r.matchup.get((dv["card"], dv["board"], dv["opponent"]))
        assert cell is not None
        assert cell.losses == dv["losses"]
        assert cell.wins == dv["wins"]
        assert cell.n == dv["n"]
        con.close()

    def test_decisive_match_count(self, make_rounds_corpus):
        con, facts = make_rounds_corpus()
        r = compute_card_winrates(con)
        assert r.coverage.decisive_matched == facts["total_decisive"]
        con.close()

    def test_n_repeats_scales_signal(self, make_rounds_corpus):
        """n_repeats=3 triples the seeded cell's n."""
        con, facts = make_rounds_corpus(n_repeats=3)
        r = compute_card_winrates(con)
        sv = facts["surgical_vs_combo"]
        cell = r.matchup[(sv["card"], sv["board"], sv["opponent"])]
        assert cell.n == sv["n"]
        assert cell.wins == sv["wins"]
        con.close()

    def test_n_repeats_tier_boundary_evolving(self, make_rounds_corpus):
        """n_repeats=15 → n=30 → evolving tier for the seeded cell."""
        from legacy_engine.confidence import tier_for_sample
        con, facts = make_rounds_corpus(n_repeats=15)
        r = compute_card_winrates(con)
        sv = facts["surgical_vs_combo"]
        cell = r.matchup[(sv["card"], sv["board"], sv["opponent"])]
        assert cell.n == 30
        assert tier_for_sample(cell.n) == "evolving"
        con.close()

    def test_n_repeats_tier_boundary_established(self, make_rounds_corpus):
        """n_repeats=50 → n=100 → established tier for the seeded cell."""
        from legacy_engine.confidence import tier_for_sample
        con, facts = make_rounds_corpus(n_repeats=50)
        r = compute_card_winrates(con)
        sv = facts["surgical_vs_combo"]
        cell = r.matchup[(sv["card"], sv["board"], sv["opponent"])]
        assert cell.n == 100
        assert tier_for_sample(cell.n) == "established"
        con.close()


# ---------------------------------------------------------------------------
# Class TestNoFanOut — cardinality-safe: Σ cell n ≤ resolved matches played
# ---------------------------------------------------------------------------


class TestNoFanOut:
    """No fan-out double-count: a card contributes exactly 1 to a cell's n per match."""

    def test_sum_of_matchup_n_le_resolved(self, make_rounds_corpus):
        """For each card, Σ over its matchup cells of n ≤ total resolved matches."""
        con, facts = make_rounds_corpus(n_repeats=3)
        r = compute_card_winrates(con)

        total_resolved = r.coverage.decisive_matched

        # Group matchup cells by (card, board)
        from collections import defaultdict
        cell_n_by_card: dict[tuple[str, str], int] = defaultdict(int)
        for (card, board, _opp), cell in r.matchup.items():
            cell_n_by_card[(card, board)] += cell.n

        for (card, board), total_n in cell_n_by_card.items():
            assert total_n <= total_resolved, (
                f"Fan-out detected: ({card!r}, {board!r}) Σcell_n={total_n} "
                f"> total_resolved={total_resolved}"
            )

        con.close()

    def test_card_in_multiple_matchups_no_double_count(self, make_rounds_corpus):
        """Brainstorm is in every Control deck; its cell n must not exceed resolved matches."""
        con, facts = make_rounds_corpus(n_repeats=5)
        r = compute_card_winrates(con)
        total_resolved = r.coverage.decisive_matched

        brainstorm_cells = {
            opp: cell
            for (card, board, opp), cell in r.matchup.items()
            if card == "Brainstorm" and board == "main"
        }
        for opp, cell in brainstorm_cells.items():
            assert cell.n <= total_resolved, (
                f"Fan-out: Brainstorm vs {opp!r} n={cell.n} > resolved={total_resolved}"
            )

        con.close()


# ---------------------------------------------------------------------------
# Class TestCoverageParity — mirrors compute_match_results exclusions exactly
# ---------------------------------------------------------------------------


class TestCoverageParity:
    """compute_card_winrates excludes byes/draws/mirrors/ambiguous/unmatched
    identically to compute_match_results for the same corpus + window."""

    def _load_multi(self, con):
        """Load a corpus with mirror, draw, unmatched, and decisive rounds."""
        raw = {
            "Tournament": {
                "Name": "Parity Test",
                "Date": "2026-06-01",
                "Uri": "https://www.mtgo.com/decklist/parity-test-2026-06-01",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "p1",
                    "Result": "1st",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
                {
                    "Player": "p2",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
                {
                    "Player": "p3",
                    "Result": "3rd",
                    "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
                    "Sideboard": [],
                },
                {
                    "Player": "p4",
                    "Result": "4th",
                    "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [
                # mirror: p1(Delver) vs p2(Delver) — p1 wins
                {"Player1": "p1", "Player2": "p2", "Result": "2-1"},
                # decisive: p3(Lands) vs p4(Combo) — p3 wins
                {"Player1": "p3", "Player2": "p4", "Result": "2-0"},
                # draw: dropped
                {"Player1": "p1", "Player2": "p3", "Result": "1-1"},
                # unmatched: p5 has no deck row
                {"Player1": "p1", "Player2": "p5", "Result": "2-0"},
            ],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' "
            "WHERE tournament_id = ? AND player IN ('p1', 'p2')",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' "
            "WHERE tournament_id = ? AND player = 'p3'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Combo' "
            "WHERE tournament_id = ? AND player = 'p4'",
            [tid],
        )
        return tid

    def test_coverage_counters_match_compute_match_results(self):
        """MatchCoverage from compute_card_winrates matches compute_match_results for same corpus."""
        con = _con()
        self._load_multi(con)

        mr = compute_match_results(con)
        cr = compute_card_winrates(con)

        assert cr.coverage.total_pairings == mr.coverage.total_pairings
        assert cr.coverage.decisive_matched == mr.coverage.decisive_matched
        assert cr.coverage.mirror_matches == mr.coverage.mirror_matches
        assert cr.coverage.dropped_byes_draws == mr.coverage.dropped_byes_draws
        assert cr.coverage.unmatched == mr.coverage.unmatched
        assert cr.coverage.ambiguous_player_names == mr.coverage.ambiguous_player_names

        con.close()

    def test_mirror_excluded_from_card_winrates(self):
        """Mirror matches do not attribute to card win-rate cells."""
        raw = {
            "Tournament": {
                "Name": "Mirror Only",
                "Date": "2026-06-02",
                "Uri": "https://www.mtgo.com/decklist/mirror-only-2026-06-02",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "alice",
                    "Result": "1st",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
                {
                    "Player": "bob",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
            "Standings": [],
        }
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute("UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ?", [tid])

        r = compute_card_winrates(con)
        assert r.coverage.mirror_matches == 1
        assert r.coverage.decisive_matched == 0
        assert r.matchup == {}
        assert r.marginal == {}
        con.close()

    def test_bye_excluded(self):
        """Bye round (player2 empty) → dropped_byes_draws, no card attribution."""
        raw = {
            "Tournament": {
                "Name": "Bye Test",
                "Date": "2026-06-03",
                "Uri": "https://www.mtgo.com/decklist/bye-test-2026-06-03",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "alice",
                    "Result": "1st",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
                {
                    "Player": "bob",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [
                {"Player1": "alice", "Player2": "bob", "Result": "2-1"},
                {"Player1": "alice", "Player2": "", "Result": "2-0"},
            ],
            "Standings": [],
        }
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )

        r = compute_card_winrates(con)
        assert r.coverage.total_pairings == 2
        assert r.coverage.decisive_matched == 1
        assert r.coverage.dropped_byes_draws == 1

        # Only one decisive match: Brainstorm wins vs Lands
        bs_cell = r.matchup.get(("Brainstorm", "main", "Lands"))
        assert bs_cell is not None
        assert bs_cell.wins == 1
        assert bs_cell.n == 1

        con.close()

    def test_ambiguous_excluded(self):
        """Ambiguous player name → ambiguous_player_names, no card attribution."""
        raw = {
            "Tournament": {
                "Name": "Ambiguous",
                "Date": "2026-06-04",
                "Uri": "https://www.mtgo.com/decklist/ambiguous-2026-06-04",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "alice",
                    "Result": "1st",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
                {
                    "Player": "bob",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
            "Standings": [],
        }
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        # Inject duplicate normalized name for alice
        con.execute(
            "INSERT INTO decks VALUES (?, 99, '  Alice ', '1st', 'Delver')", [tid]
        )
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )

        r = compute_card_winrates(con)
        assert r.coverage.ambiguous_player_names == 1
        assert r.coverage.decisive_matched == 0
        assert r.matchup == {}

        con.close()


# ---------------------------------------------------------------------------
# Class TestDateWindowing — since/until filter by tournaments.date
# ---------------------------------------------------------------------------


class TestDateWindowing:
    def _load_two_dated(self, con):
        """Load two tournaments on different dates with known decisive results."""
        raw_early = {
            "Tournament": {
                "Name": "Early",
                "Date": "2026-01-01",
                "Uri": "https://www.mtgo.com/decklist/early-2026-01-01",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "alice",
                    "Result": "1st",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
                {
                    "Player": "bob",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
            "Standings": [],
        }
        raw_late = {
            "Tournament": {
                "Name": "Late",
                "Date": "2026-06-01",
                "Uri": "https://www.mtgo.com/decklist/late-2026-06-01",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "carol",
                    "Result": "1st",
                    "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
                    "Sideboard": [],
                },
                {
                    "Player": "dave",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Ponder"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [{"Player1": "carol", "Player2": "dave", "Result": "2-0"}],
            "Standings": [],
        }
        tid_early = store.load_tournament(con, parse_cache_item(raw_early, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
            [tid_early],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'bob'",
            [tid_early],
        )

        tid_late = store.load_tournament(con, parse_cache_item(raw_late, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = 'carol'",
            [tid_late],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Reanimator' WHERE tournament_id = ? AND player = 'dave'",
            [tid_late],
        )

    def test_since_excludes_earlier(self):
        con = _con()
        self._load_two_dated(con)
        r = compute_card_winrates(con, since="2026-03-01")
        assert r.coverage.decisive_matched == 1
        # Only late tournament matches: Dark Ritual (main) vs Reanimator
        assert ("Dark Ritual", "main", "Reanimator") in r.matchup
        assert ("Brainstorm", "main", "Lands") not in r.matchup
        con.close()

    def test_until_excludes_later(self):
        con = _con()
        self._load_two_dated(con)
        r = compute_card_winrates(con, until="2026-03-01")
        assert r.coverage.decisive_matched == 1
        # Only early tournament: Brainstorm (main) vs Lands
        assert ("Brainstorm", "main", "Lands") in r.matchup
        assert ("Dark Ritual", "main", "Reanimator") not in r.matchup
        con.close()

    def test_both_since_until(self):
        con = _con()
        self._load_two_dated(con)
        # Window covers both → 2 decisive
        r = compute_card_winrates(con, since="2025-01-01", until="2027-01-01")
        assert r.coverage.decisive_matched == 2
        con.close()

    def test_no_window_includes_all(self):
        con = _con()
        self._load_two_dated(con)
        r = compute_card_winrates(con)
        assert r.coverage.decisive_matched == 2
        con.close()


# ---------------------------------------------------------------------------
# Class TestBoardAwareness — main vs side counted separately
# ---------------------------------------------------------------------------


class TestBoardAwareness:
    def test_main_and_side_are_distinct_cells(self):
        """A card in both main and side yields separate matchup cells."""
        raw = {
            "Tournament": {
                "Name": "Board Test",
                "Date": "2026-06-05",
                "Uri": "https://www.mtgo.com/decklist/board-test-2026-06-05",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "alice",
                    "Result": "1st",
                    "Mainboard": [{"Count": 3, "CardName": "Surgical Extraction"}],
                    "Sideboard": [{"Count": 1, "CardName": "Surgical Extraction"}],
                },
                {
                    "Player": "bob",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
            "Standings": [],
        }
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )

        r = compute_card_winrates(con)

        # Both boards should appear as separate keys
        main_cell = r.matchup.get(("Surgical Extraction", "main", "Combo"))
        side_cell = r.matchup.get(("Surgical Extraction", "side", "Combo"))
        assert main_cell is not None, "main board cell missing"
        assert side_cell is not None, "side board cell missing"
        assert main_cell.wins == 1
        assert side_cell.wins == 1

        # They should be separate marginal entries too
        assert r.marginal.get(("Surgical Extraction", "main")) is not None
        assert r.marginal.get(("Surgical Extraction", "side")) is not None

        con.close()

    def test_side_only_card_has_no_main_cell(self):
        """A card only in sideboard produces no main-board cell."""
        raw = {
            "Tournament": {
                "Name": "Side Only",
                "Date": "2026-06-06",
                "Uri": "https://www.mtgo.com/decklist/side-only-2026-06-06",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "alice",
                    "Result": "1st",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [{"Count": 2, "CardName": "Surgical Extraction"}],
                },
                {
                    "Player": "bob",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
            "Standings": [],
        }
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )

        r = compute_card_winrates(con)

        assert ("Surgical Extraction", "main", "Combo") not in r.matchup
        assert ("Surgical Extraction", "side", "Combo") in r.matchup

        con.close()


# ---------------------------------------------------------------------------
# Class TestCardWinRatesStructure — record shapes and baseline_winrate
# ---------------------------------------------------------------------------


class TestCardWinRatesStructure:
    def test_baseline_winrate_near_half(self, make_rounds_corpus):
        """baseline_winrate should be ~0.5 by construction (one win + one loss per match)."""
        con, _ = make_rounds_corpus(n_repeats=5)
        r = compute_card_winrates(con)
        # Not exactly 0.5 due to the formula but should be very close
        assert abs(r.baseline_winrate - 0.5) < 0.01
        con.close()

    def test_empty_corpus_returns_valid_structure(self):
        """Empty DB (schema initialized, no data) → CardWinRates with empty dicts."""
        con = _con()
        store.init_schema(con)  # tables must exist before the query runs
        r = compute_card_winrates(con)
        assert r.matchup == {}
        assert r.marginal == {}
        assert r.baseline_winrate == 0.5
        assert r.coverage.total_pairings == 0
        assert r.coverage.decisive_matched == 0
        con.close()

    def test_provenance_stored(self, make_rounds_corpus):
        con, _ = make_rounds_corpus()
        r = compute_card_winrates(con, provenance="online")
        assert r.provenance == "online"
        con.close()

    def test_provenance_none_stored(self, make_rounds_corpus):
        con, _ = make_rounds_corpus()
        r = compute_card_winrates(con, provenance=None)
        assert r.provenance is None
        con.close()

    def test_marginal_n_equals_sum_of_matchup_n(self, make_rounds_corpus):
        """For each (card, board), marginal.n == sum of matchup cell n's."""
        con, _ = make_rounds_corpus(n_repeats=3)
        r = compute_card_winrates(con)

        from collections import defaultdict
        matchup_n_by_card: dict[tuple[str, str], int] = defaultdict(int)
        for (card, board, _opp), cell in r.matchup.items():
            matchup_n_by_card[(card, board)] += cell.n

        for (card, board), mg in r.marginal.items():
            expected = matchup_n_by_card[(card, board)]
            assert mg.n == expected, (
                f"Marginal mismatch: ({card!r}, {board!r}) marginal.n={mg.n} "
                f"!= Σcell_n={expected}"
            )

        con.close()

    def test_card_matchup_record_n_property(self):
        rec = CardMatchupRecord(card="X", board="main", opponent="Y", wins=3, losses=2)
        assert rec.n == 5

    def test_card_marginal_record_n_property(self):
        rec = CardMarginalRecord(card="X", board="main", wins=7, losses=3)
        assert rec.n == 10

"""Match-outcome extraction: parser, normalizer, record types, and accumulator.

Covers all acceptance criteria across Units 1–5 of
``epic-meta-analytics-match-results``.  House style: module-level raw dicts →
``parse_cache_item`` → ``store.load_tournament``; ``_con()`` helper; ``TestX``
classes; deterministic labels pinned via direct SQL UPDATE.
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics import (
    ArchetypeRecord,
    MatchCoverage,
    MatchOutcome,
    MatchResults,
    MatchupTally,
    compute_match_results,
    normalize_player,
    parse_match_result,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item

# ---------------------------------------------------------------------------
# Shared raw tournament fixtures
# ---------------------------------------------------------------------------

_CHALLENGE_ONLINE = {
    "Tournament": {
        "Name": "Legacy Challenge 32",
        "Date": "2026-05-24",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-32-2026-05-24",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "alice",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "bob",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
    "Standings": [
        {"Rank": 1, "Player": "alice", "Points": 18},
        {"Rank": 2, "Player": "bob", "Points": 15},
    ],
}

_CHALLENGE_PAPER = {
    "Tournament": {
        "Name": "Paper Challenge",
        "Date": "2026-05-25",
        "Uri": "https://melee.gg/Tournament/View/12345",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "carol",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
        {
            "Player": "dave",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Ponder"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [{"Player1": "carol", "Player2": "dave", "Result": "2-0"}],
    "Standings": [
        {"Rank": 1, "Player": "carol", "Points": 9},
        {"Rank": 2, "Player": "dave", "Points": 6},
    ],
}

_LEAGUE = {
    "Tournament": {
        "Name": "Legacy League",
        "Date": "2026-05-24",
        "Uri": "https://www.mtgo.com/decklist/legacy-league-2026-05-24",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "eve",
            "Result": "5-0",
            "Mainboard": [{"Count": 4, "CardName": "Ponder"}],
            "Sideboard": [],
        }
    ],
    "Rounds": [],
    "Standings": [],
}

# A tournament designed to exercise mirror / draw / unmatched scenarios
_MULTI = {
    "Tournament": {
        "Name": "Legacy Challenge 64",
        "Date": "2026-05-26",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-64-2026-05-26",
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


def _con() -> store.DuckDBPyConnection:  # type: ignore[name-defined]
    return store.connect(":memory:")


# ---------------------------------------------------------------------------
# Unit 1 — parse_match_result
# ---------------------------------------------------------------------------


class TestParseMatchResult:
    @pytest.mark.parametrize(
        "result, expected",
        [
            ("2-1", MatchOutcome(2, 1, "p1")),
            ("2-0", MatchOutcome(2, 0, "p1")),
            ("1-2", MatchOutcome(1, 2, "p2")),
            ("0-2", MatchOutcome(0, 2, "p2")),
            ("1-1", MatchOutcome(1, 1, None)),
            ("1-1-1", MatchOutcome(1, 1, None)),
        ],
    )
    def test_decisive_and_draw_cases(self, result, expected):
        assert parse_match_result(result) == expected

    @pytest.mark.parametrize(
        "result",
        ["", None, "BYE", "2", "foo-bar", "  ", "W-L"],
    )
    def test_unparseable_returns_none(self, result):
        assert parse_match_result(result) is None

    def test_draw_has_no_winner(self):
        outcome = parse_match_result("1-1")
        assert outcome is not None
        assert outcome.winner is None

    def test_third_token_ignored(self):
        # "1-1-1" is a draw, not unparseable
        outcome = parse_match_result("1-1-1")
        assert outcome is not None
        assert outcome.winner is None

    def test_never_raises(self):
        # Defensive: arbitrary input must not raise
        for bad in [None, "", "BYE", "abc-def", "2-", "-1", "2-1-foo"]:
            try:
                parse_match_result(bad)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"parse_match_result({bad!r}) raised: {exc}")


# ---------------------------------------------------------------------------
# Unit 2 — normalize_player
# ---------------------------------------------------------------------------


class TestNormalizePlayer:
    def test_strips_and_casefolds(self):
        assert normalize_player("  Alice ") == "alice"

    def test_upper_to_lower(self):
        assert normalize_player("BOB") == "bob"

    def test_none_returns_empty(self):
        assert normalize_player(None) == ""

    def test_empty_returns_empty(self):
        assert normalize_player("") == ""

    def test_mixed_case_and_whitespace(self):
        assert normalize_player("  MiXeD  ") == "mixed"


# ---------------------------------------------------------------------------
# Unit 3 — record types + MatchCoverage
# ---------------------------------------------------------------------------


class TestRecordTypes:
    def test_matchup_tally_n(self):
        t = MatchupTally(archetype_a="Delver", archetype_b="Lands", wins=3, losses=1)
        assert t.n == 4

    def test_matchup_tally_n_zero(self):
        t = MatchupTally(archetype_a="A", archetype_b="B")
        assert t.n == 0

    def test_archetype_record_n(self):
        r = ArchetypeRecord(archetype="Reanimator", wins=5, losses=2)
        assert r.n == 7

    def test_archetype_record_n_zero(self):
        r = ArchetypeRecord(archetype="X")
        assert r.n == 0

    def test_match_coverage_match_rate(self):
        cov = MatchCoverage(total_pairings=10, decisive_matched=7)
        assert cov.match_rate == pytest.approx(0.7)

    def test_match_coverage_match_rate_zero_pairings(self):
        cov = MatchCoverage()
        assert cov.match_rate == 0.0


# ---------------------------------------------------------------------------
# Unit 4 — compute_match_results
# ---------------------------------------------------------------------------


class TestComputeMatchResults:

    # ── helpers ─────────────────────────────────────────────────────────────

    def _load_online_challenge(self, con):
        """Load the basic online challenge with alice(Delver) vs bob(Lands)."""
        tid = store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Delver", tid, "alice"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Lands", tid, "bob"],
        )
        return tid

    # ── decisive match ───────────────────────────────────────────────────────

    def test_decisive_match_tallies(self):
        con = _con()
        self._load_online_challenge(con)
        res = compute_match_results(con)

        assert res.matchups[("Delver", "Lands")].wins == 1
        assert res.matchups[("Delver", "Lands")].losses == 0
        assert res.matchups[("Lands", "Delver")].wins == 0
        assert res.matchups[("Lands", "Delver")].losses == 1
        con.close()

    def test_decisive_match_marginals(self):
        con = _con()
        self._load_online_challenge(con)
        res = compute_match_results(con)

        assert res.archetypes["Delver"].wins == 1
        assert res.archetypes["Delver"].losses == 0
        assert res.archetypes["Lands"].wins == 0
        assert res.archetypes["Lands"].losses == 1
        con.close()

    def test_decisive_match_coverage(self):
        con = _con()
        self._load_online_challenge(con)
        res = compute_match_results(con)

        cov = res.coverage
        assert cov.total_pairings == 1
        assert cov.decisive_matched == 1
        assert cov.unmatched == 0
        assert cov.dropped_byes_draws == 0
        assert cov.mirror_matches == 0
        con.close()

    # ── cell symmetry ────────────────────────────────────────────────────────

    def test_cell_symmetry(self):
        """For all non-mirror cells: (a,b).wins == (b,a).losses."""
        con = _con()
        self._load_online_challenge(con)
        res = compute_match_results(con)

        for (a, b), cell in res.matchups.items():
            mirror = res.matchups.get((b, a))
            if mirror is not None:
                assert cell.wins == mirror.losses, (
                    f"symmetry broken: ({a},{b}).wins={cell.wins} != "
                    f"({b},{a}).losses={mirror.losses}"
                )
        con.close()

    # ── League contributes zero pairings ─────────────────────────────────────

    def test_league_contributes_no_pairings(self):
        con = _con()
        store.load_tournament(con, parse_cache_item(_LEAGUE, "MTGO"))
        res = compute_match_results(con)
        assert res.coverage.total_pairings == 0
        assert res.matchups == {}
        assert res.archetypes == {}
        con.close()

    # ── unmatched ────────────────────────────────────────────────────────────

    def test_unmatched_pairing_no_tally(self):
        """A pairing where one player has no labeled deck → unmatched, no tally."""
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        # Only label alice; bob stays NULL
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Delver", tid, "alice"],
        )
        res = compute_match_results(con)

        assert res.coverage.unmatched == 1
        assert res.coverage.decisive_matched == 0
        assert res.matchups == {}
        con.close()

    # ── draw / bye dropped ───────────────────────────────────────────────────

    def test_draw_dropped(self):
        """A "1-1" result → dropped_byes_draws, no tally."""
        con = _con()
        raw = {
            "Tournament": {
                "Name": "Draw Test",
                "Date": "2026-05-27",
                "Uri": "https://www.mtgo.com/decklist/draw-test-2026-05-27",
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
            "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "1-1"}],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Delver", tid, "alice"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Lands", tid, "bob"],
        )
        res = compute_match_results(con)

        assert res.coverage.dropped_byes_draws == 1
        assert res.coverage.decisive_matched == 0
        assert res.matchups == {}
        con.close()

    # ── mirror match ─────────────────────────────────────────────────────────

    def test_mirror_match(self):
        """Two same-archetype players → mirror_matches == 1, marginal gets +1/+1."""
        con = _con()
        raw = {
            "Tournament": {
                "Name": "Mirror Test",
                "Date": "2026-05-28",
                "Uri": "https://www.mtgo.com/decklist/mirror-test-2026-05-28",
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
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Delver", tid, "alice"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Delver", tid, "bob"],
        )
        res = compute_match_results(con)

        assert res.coverage.mirror_matches == 1
        assert res.coverage.decisive_matched == 0
        # No directed cells for mirror
        assert ("Delver", "Delver") not in res.matchups
        # Marginal: +1 win, +1 loss for Delver
        assert res.archetypes["Delver"].wins == 1
        assert res.archetypes["Delver"].losses == 1
        con.close()

    # ── provenance filter ────────────────────────────────────────────────────

    def test_provenance_online_excludes_paper(self):
        """provenance="online" should exclude paper-tournament rounds."""
        con = _con()
        # Load online tournament with labeled decks
        tid_online = store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Delver", tid_online, "alice"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Lands", tid_online, "bob"],
        )
        # Load paper tournament with labeled decks
        tid_paper = store.load_tournament(
            con, parse_cache_item(_CHALLENGE_PAPER, "mtgmelee")
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Reanimator", tid_paper, "carol"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Combo", tid_paper, "dave"],
        )

        res_online = compute_match_results(con, provenance="online")
        assert res_online.coverage.total_pairings == 1
        assert ("Delver", "Lands") in res_online.matchups
        assert "Reanimator" not in res_online.archetypes

        res_paper = compute_match_results(con, provenance="paper")
        assert res_paper.coverage.total_pairings == 1
        assert ("Reanimator", "Combo") in res_paper.matchups
        assert "Delver" not in res_paper.archetypes

    def test_provenance_none_includes_all(self):
        """provenance=None includes both online and paper."""
        con = _con()
        tid_online = store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Delver", tid_online, "alice"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Lands", tid_online, "bob"],
        )
        tid_paper = store.load_tournament(
            con, parse_cache_item(_CHALLENGE_PAPER, "mtgmelee")
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Reanimator", tid_paper, "carol"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Combo", tid_paper, "dave"],
        )

        res_all = compute_match_results(con, provenance=None)
        assert res_all.coverage.total_pairings == 2
        assert ("Delver", "Lands") in res_all.matchups
        assert ("Reanimator", "Combo") in res_all.matchups

    # ── provenance attribute preserved ───────────────────────────────────────

    def test_provenance_attribute_stored(self):
        con = _con()
        self._load_online_challenge(con)
        res = compute_match_results(con, provenance="online")
        assert res.provenance == "online"
        con.close()

    def test_provenance_none_stored(self):
        con = _con()
        self._load_online_challenge(con)
        res = compute_match_results(con, provenance=None)
        assert res.provenance is None
        con.close()

    # ── normalization parity (SQL lower/trim == normalize_player) ────────────

    def test_normalization_parity(self):
        """A deck stored as '  Alice ' joins correctly with a round using 'alice'."""
        con = _con()
        raw = {
            "Tournament": {
                "Name": "Norm Parity Test",
                "Date": "2026-05-29",
                "Uri": "https://www.mtgo.com/decklist/norm-parity-2026-05-29",
                "Formats": "Legacy",
            },
            "Decks": [
                # Player name has leading/trailing whitespace — simulated at
                # the data layer by inserting the raw dict and then directly
                # patching the player column after load.
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
            "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-0"}],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))

        # Patch the deck player name to add whitespace & change case — this
        # simulates a raw data source with messy handles
        con.execute(
            "UPDATE decks SET player = '  Alice ', archetype = 'Delver' "
            "WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' "
            "WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )

        # The SQL join uses lower(trim(player)) == lower(trim(player1)) so
        # '  Alice ' should join with the round's player1 'alice'.
        res = compute_match_results(con)
        assert res.coverage.total_pairings == 1
        assert res.coverage.decisive_matched == 1
        assert res.coverage.unmatched == 0
        assert res.archetypes["Delver"].wins == 1

        # Also verify normalize_player produces the same key
        assert normalize_player("  Alice ") == "alice"
        con.close()

    # ── multi-scenario integration (mirror + decisive + draw + unmatched) ────

    def test_multi_scenario_coverage_totals(self):
        """Load _MULTI with mirrors, draws, unmatched, and decisive rounds."""
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(_MULTI, "MTGO"))

        # p1/p2 = Delver (mirror), p3 = Lands, p4 = Combo; p5 has no deck row
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

        res = compute_match_results(con)
        cov = res.coverage

        # 4 rounds total
        assert cov.total_pairings == 4
        # p1(Delver) vs p2(Delver) → mirror
        assert cov.mirror_matches == 1
        # p3(Lands) vs p4(Combo) → decisive
        assert cov.decisive_matched == 1
        # p1 vs p3 → draw
        assert cov.dropped_byes_draws == 1
        # p1 vs p5 (no deck row) → unmatched
        assert cov.unmatched == 1

        # Decisive: Lands beat Combo
        assert res.matchups[("Lands", "Combo")].wins == 1
        assert res.matchups[("Combo", "Lands")].losses == 1

        # Mirror: Delver marginal +1/+1
        assert res.archetypes["Delver"].wins == 1
        assert res.archetypes["Delver"].losses == 1

        con.close()

    # ── Unit 5 import smoke test ──────────────────────────────────────────────

    def test_public_imports_from_analytics_package(self):
        """from legacy_engine.analytics import ... must succeed."""
        from legacy_engine.analytics import (  # noqa: F401
            ArchetypeRecord,
            MatchCoverage,
            MatchOutcome,
            MatchResults,
            MatchupTally,
            compute_match_results,
            normalize_player,
            parse_match_result,
        )

    # ── Unit 1 (matchup-matrix): additive mirror_n field ─────────────────────

    def test_mirror_n_populated_for_same_archetype_pairing(self):
        """Two Delver players → mirror_n == {"Delver": 1}; coverage.mirror_matches==1 unchanged."""
        con = _con()
        raw = {
            "Tournament": {
                "Name": "Mirror N Test",
                "Date": "2026-05-29",
                "Uri": "https://www.mtgo.com/decklist/mirror-n-test-2026-05-29",
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
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ?",
            [tid],
        )
        res = compute_match_results(con)

        # Additive field: mirror_n tracks per-archetype count
        assert res.mirror_n == {"Delver": 1}
        # Existing behavior: coverage.mirror_matches still incremented
        assert res.coverage.mirror_matches == 1
        # Existing behavior: no directed cells for mirror
        assert ("Delver", "Delver") not in res.matchups
        con.close()

    def test_mirror_n_empty_for_non_mirror_pairing(self):
        """Non-mirror pairing → mirror_n stays empty; no regression."""
        con = _con()
        self._load_online_challenge(con)
        res = compute_match_results(con)
        assert res.mirror_n == {}
        con.close()

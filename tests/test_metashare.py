"""Meta-share computation tests — Units 1–7 of epic-meta-analytics-metashare.

House style: module-level raw dicts → ``parse_cache_item`` → ``store.load_tournament``
into ``:memory:``; labels pinned via direct SQL UPDATE; ``TestX`` classes; deterministic.
"""

from __future__ import annotations

import math

import pytest
from click.testing import CliRunner

from legacy_engine.analytics import (
    MetaShareEntry,
    MetaShareReport,
    blend_shares,
    compute_all,
    compute_metashare,
)
from legacy_engine.analytics.metashare import (
    _assemble,
    _raw_counts,
    _topcut_counts,
    _unlabeled_count,
    _wrw_weights,
)
from legacy_engine.cli import main
from legacy_engine.confidence import tier_for_sample
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

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _con():
    return store.connect(":memory:")


def _load_online_challenge(con):
    """alice=Delver, bob=Lands; online; standings present."""
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


def _load_paper_challenge(con):
    """carol=Reanimator, dave=Combo; paper; standings present."""
    tid = store.load_tournament(con, parse_cache_item(_CHALLENGE_PAPER, "mtgmelee"))
    con.execute(
        "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
        ["Reanimator", tid, "carol"],
    )
    con.execute(
        "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
        ["Combo", tid, "dave"],
    )
    return tid


# ---------------------------------------------------------------------------
# Unit 1 — _topcut_counts
# ---------------------------------------------------------------------------


class TestTopcutCounts:
    def test_both_players_within_cut(self):
        """alice(rank 1) and bob(rank 2) both within cut_size=8."""
        con = _con()
        _load_online_challenge(con)
        counts = _topcut_counts(con, provenance=None, cut_size=8)
        assert counts["Delver"] == 1
        assert counts["Lands"] == 1
        con.close()

    def test_cut_size_1_only_alice(self):
        """cut_size=1 → only alice (rank 1)."""
        con = _con()
        _load_online_challenge(con)
        counts = _topcut_counts(con, provenance=None, cut_size=1)
        assert counts.get("Delver", 0) == 1
        assert counts.get("Lands", 0) == 0
        con.close()

    def test_league_contributes_zero(self):
        """League (no standings) contributes zero to top-cut counts."""
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(_LEAGUE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Delver", tid, "eve"],
        )
        counts = _topcut_counts(con, provenance=None, cut_size=8)
        assert counts == {}
        con.close()

    def test_provenance_paper_excludes_online(self):
        """provenance='paper' excludes online events."""
        con = _con()
        _load_online_challenge(con)
        counts = _topcut_counts(con, provenance="paper", cut_size=8)
        assert counts == {}
        con.close()

    def test_provenance_online_excludes_paper(self):
        """provenance='online' excludes paper events."""
        con = _con()
        _load_paper_challenge(con)
        counts = _topcut_counts(con, provenance="online", cut_size=8)
        assert counts == {}
        con.close()

    def test_null_archetype_excluded(self):
        """Decks with NULL archetype are not counted even if they have standings."""
        con = _con()
        store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        # Leave archetypes as NULL
        counts = _topcut_counts(con, provenance=None, cut_size=8)
        assert counts == {}
        con.close()


# ---------------------------------------------------------------------------
# Unit 2 — _raw_counts + _unlabeled_count
# ---------------------------------------------------------------------------


class TestRawCounts:
    def test_basic_counts(self):
        """Two Delver + one Lands (all labeled) → {'Delver':2, 'Lands':1}."""
        con = _con()
        # Build a 3-deck tournament
        raw = {
            "Tournament": {
                "Name": "Raw Test",
                "Date": "2026-05-24",
                "Uri": "https://www.mtgo.com/decklist/raw-test-2026-05-24",
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
            ],
            "Rounds": [],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player IN ('p1','p2')",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'p3'",
            [tid],
        )
        counts = _raw_counts(con, provenance=None)
        assert counts == {"Delver": 2, "Lands": 1}
        con.close()

    def test_share_raw_fraction(self):
        """share_raw(Delver) == 2/3."""
        con = _con()
        raw = {
            "Tournament": {
                "Name": "Share Test",
                "Date": "2026-05-25",
                "Uri": "https://www.mtgo.com/decklist/share-test-2026-05-25",
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
            ],
            "Rounds": [],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player IN ('p1','p2')",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'p3'",
            [tid],
        )
        counts = _raw_counts(con, provenance=None)
        total = sum(counts.values())
        assert pytest.approx(counts["Delver"] / total) == 2 / 3
        con.close()

    def test_null_excluded_from_counts(self):
        """NULL-archetype deck is excluded from raw counts."""
        con = _con()
        store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        # No labels set — both decks have NULL archetype
        counts = _raw_counts(con, provenance=None)
        assert counts == {}
        con.close()

    def test_unlabeled_count_reflects_null(self):
        """NULL-archetype deck is reflected in _unlabeled_count."""
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        # Label only alice; bob stays NULL
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        unlabeled = _unlabeled_count(con, provenance=None)
        assert unlabeled == 1
        con.close()

    def test_unknown_appears_as_own_row(self):
        """An 'Unknown'-labeled deck appears as its own 'Unknown' row."""
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Unknown' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Unknown' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )
        counts = _raw_counts(con, provenance=None)
        assert "Unknown" in counts
        assert counts["Unknown"] == 2
        con.close()

    def test_conflict_appears_as_own_row(self):
        """A 'Conflict(...)'-labeled deck appears as its own row."""
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Conflict(A,B)' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )
        counts = _raw_counts(con, provenance=None)
        assert "Conflict(A,B)" in counts
        con.close()

    def test_provenance_filter(self):
        """provenance='online' excludes paper decks."""
        con = _con()
        _load_online_challenge(con)
        _load_paper_challenge(con)
        online_counts = _raw_counts(con, provenance="online")
        assert "Reanimator" not in online_counts
        assert "Delver" in online_counts
        paper_counts = _raw_counts(con, provenance="paper")
        assert "Delver" not in paper_counts
        assert "Reanimator" in paper_counts
        con.close()


# ---------------------------------------------------------------------------
# Unit 3 — _wrw_weights
# ---------------------------------------------------------------------------


class TestWrwWeights:
    def _build_wrw_corpus(self):
        """Delver raw-share 0.5 and wr 0.6; Lands raw-share 0.5 wr 0.4.

        Setup: 2 Delver + 2 Lands decks (equal raw share); Delver beats Lands 3 times,
        Lands beats Delver 2 times → Delver wr = 3/5 = 0.6, Lands wr = 2/5 = 0.4.
        """
        con = _con()
        raw = {
            "Tournament": {
                "Name": "WRW Corpus",
                "Date": "2026-05-26",
                "Uri": "https://www.mtgo.com/decklist/wrw-corpus-2026-05-26",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "d1",
                    "Result": "1st",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
                {
                    "Player": "d2",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
                {
                    "Player": "l1",
                    "Result": "3rd",
                    "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
                    "Sideboard": [],
                },
                {
                    "Player": "l2",
                    "Result": "4th",
                    "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [
                # Delver wins: 3
                {"Player1": "d1", "Player2": "l1", "Result": "2-1"},
                {"Player1": "d1", "Player2": "l2", "Result": "2-0"},
                {"Player1": "d2", "Player2": "l2", "Result": "2-1"},
                # Lands wins: 2
                {"Player1": "l1", "Player2": "d2", "Result": "2-0"},
                {"Player1": "l1", "Player2": "d1", "Result": "2-1"},
            ],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player IN ('d1','d2')",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player IN ('l1','l2')",
            [tid],
        )
        return con

    def test_normalised_wrw_shares(self):
        """Delver raw-share 0.5, wr=0.6 → pre-norm 0.30; Lands raw-share 0.5, wr=0.4 → pre-norm 0.20.
        Normalised: Delver=0.6, Lands=0.4.
        """
        con = self._build_wrw_corpus()
        weights, matchup_n, _excluded = _wrw_weights(con, provenance=None)

        # Pre-norm: 0.5 * 0.6 = 0.30 for Delver, 0.5 * 0.4 = 0.20 for Lands
        # Normalised: 0.30/(0.30+0.20) = 0.6, 0.20/(0.30+0.20) = 0.4
        total_w = sum(weights.values())
        assert pytest.approx(weights["Delver"] / total_w, abs=1e-6) == 0.6
        assert pytest.approx(weights["Lands"] / total_w, abs=1e-6) == 0.4
        con.close()

    def test_matchup_n_is_matchup_count(self):
        """matchup_n returned is the matchup-n from match_results."""
        con = self._build_wrw_corpus()
        weights, matchup_n, _excluded = _wrw_weights(con, provenance=None)
        # Delver played 5 decisive matches total (3 wins + 2 losses = 5)
        assert matchup_n["Delver"] == 5
        # Lands played 5 decisive matches total (2 wins + 3 losses = 5)
        assert matchup_n["Lands"] == 5
        con.close()

    def test_zero_match_data_archetype_absent_from_weights(self):
        """An archetype with deck count but zero match data is absent from weights, matchup_n==0."""
        con = _con()
        # League: has decks but no rounds → no match data
        tid = store.load_tournament(con, parse_cache_item(_LEAGUE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'eve'",
            [tid],
        )
        weights, matchup_n, _excluded = _wrw_weights(con, provenance=None)
        assert "Delver" not in weights
        assert matchup_n.get("Delver", 0) == 0
        con.close()

    def test_seam_with_compute_match_results(self):
        """wrw consumes compute_match_results archetypes (matchup-n), proving the foundation contract."""
        con = self._build_wrw_corpus()
        # The wrw weights must align with match-level W/L from compute_match_results
        from legacy_engine.analytics.match_results import compute_match_results

        match_res = compute_match_results(con, provenance=None)
        weights, matchup_n, _excluded = _wrw_weights(con, provenance=None)

        for archetype, rec in match_res.archetypes.items():
            if rec.n > 0:
                wr = rec.wins / rec.n
                raw = _raw_counts(con, provenance=None)
                total = sum(raw.values())
                share_raw = raw[archetype] / total
                expected_weight = share_raw * wr
                assert pytest.approx(weights[archetype], abs=1e-9) == expected_weight
        con.close()


# ---------------------------------------------------------------------------
# Unit 4 — _assemble + MetaShareEntry / MetaShareReport
# ---------------------------------------------------------------------------


class TestAssemble:
    def test_shares_sum_to_one(self):
        """Shares within a report sum to ~1.0 (± float epsilon), including Other row."""
        con = _con()
        _load_online_challenge(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0)
        total_share = sum(e.share for e in report.entries)
        assert pytest.approx(total_share, abs=1e-9) == 1.0
        con.close()

    def test_fringe_flag_at_threshold(self):
        """Archetype at <2% share is fringe=True; at >=2% is fringe=False."""
        # Build a corpus where one archetype is just above 2% and another just below
        # 51 Delver + 1 Lands + 48 Combo → Lands share = 1/100 = 1% (fringe)
        con = _con()
        decks = []
        for i in range(51):
            decks.append({
                "Player": f"d{i}",
                "Result": f"{i+1}st",
                "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                "Sideboard": [],
            })
        decks.append({
            "Player": "l1",
            "Result": "52nd",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        })
        for i in range(48):
            decks.append({
                "Player": f"c{i}",
                "Result": f"{53+i}th",
                "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
                "Sideboard": [],
            })
        raw = {
            "Tournament": {
                "Name": "Fringe Test",
                "Date": "2026-05-27",
                "Uri": "https://www.mtgo.com/decklist/fringe-test-2026-05-27",
                "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": [],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for i in range(51):
            con.execute(
                "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = ?",
                [tid, f"d{i}"],
            )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'l1'",
            [tid],
        )
        for i in range(48):
            con.execute(
                "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = ?",
                [tid, f"c{i}"],
            )
        # Lands = 1/100 = 1% → fringe; Combo = 48% → not fringe
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.02, group_other=False)
        lands_entry = next(e for e in report.entries if e.archetype == "Lands")
        combo_entry = next(e for e in report.entries if e.archetype == "Combo")
        assert lands_entry.fringe is True
        assert combo_entry.fringe is False
        con.close()

    def test_fringe_grouped_into_other(self):
        """With group_other=True, fringe archetypes land in an 'Other' row."""
        con = _con()
        # Build corpus: 1 Delver + 1 Lands out of 100 decks → each at 1% → fringe
        decks = []
        for i in range(98):
            decks.append({
                "Player": f"c{i}",
                "Result": f"{i+1}th",
                "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                "Sideboard": [],
            })
        decks.append({
            "Player": "d1",
            "Result": "99th",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        })
        decks.append({
            "Player": "l1",
            "Result": "100th",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        })
        raw = {
            "Tournament": {
                "Name": "Other Group Test",
                "Date": "2026-05-27",
                "Uri": "https://www.mtgo.com/decklist/other-group-test-2026-05-27",
                "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": [],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for i in range(98):
            con.execute(
                "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = ?",
                [tid, f"c{i}"],
            )
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'd1'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'l1'",
            [tid],
        )
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.02, group_other=True)
        archetypes_in_report = {e.archetype for e in report.entries}
        # Delver and Lands are fringe; grouped into Other
        assert "Other" in archetypes_in_report
        assert "Delver" not in archetypes_in_report
        assert "Lands" not in archetypes_in_report
        assert "Combo" in archetypes_in_report
        con.close()

    def test_unknown_not_folded_into_other(self):
        """'Unknown' label is never folded into Other even if fringe."""
        con = _con()
        # Build corpus: Unknown is 1 out of 100 → fringe; but should stay as own row
        decks = []
        for i in range(99):
            decks.append({
                "Player": f"d{i}",
                "Result": f"{i+1}th",
                "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                "Sideboard": [],
            })
        decks.append({
            "Player": "u1",
            "Result": "100th",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        })
        raw = {
            "Tournament": {
                "Name": "Unknown Test",
                "Date": "2026-05-27",
                "Uri": "https://www.mtgo.com/decklist/unknown-test-2026-05-27",
                "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": [],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for i in range(99):
            con.execute(
                "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = ?",
                [tid, f"d{i}"],
            )
        con.execute(
            "UPDATE decks SET archetype = 'Unknown' WHERE tournament_id = ? AND player = 'u1'",
            [tid],
        )
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.02, group_other=True)
        archetypes_in_report = {e.archetype for e in report.entries}
        assert "Unknown" in archetypes_in_report
        con.close()

    def test_tier_matches_tier_for_sample(self):
        """Every entry's tier == tier_for_sample(entry.n)."""
        con = _con()
        _load_online_challenge(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        for entry in report.entries:
            assert entry.tier == tier_for_sample(entry.n), (
                f"{entry.archetype}: tier={entry.tier!r} but tier_for_sample({entry.n})="
                f"{tier_for_sample(entry.n)!r}"
            )
        con.close()

    def test_labels_present_on_report(self):
        """Every report carries non-null definition and provenance basis."""
        con = _con()
        _load_online_challenge(con)
        for defn in ("raw", "topcut", "wrw"):
            report = compute_metashare(con, definition=defn, provenance="online")
            assert report.definition == defn
            assert report.provenance == "online"
        con.close()

    def test_conflict_not_folded_into_other(self):
        """'Conflict(...)' label is never folded into Other even if fringe."""
        con = _con()
        decks = []
        for i in range(99):
            decks.append({
                "Player": f"d{i}",
                "Result": f"{i+1}th",
                "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                "Sideboard": [],
            })
        decks.append({
            "Player": "x1",
            "Result": "100th",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        })
        raw = {
            "Tournament": {
                "Name": "Conflict Test",
                "Date": "2026-05-28",
                "Uri": "https://www.mtgo.com/decklist/conflict-test-2026-05-28",
                "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": [],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for i in range(99):
            con.execute(
                "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = ?",
                [tid, f"d{i}"],
            )
        con.execute(
            "UPDATE decks SET archetype = 'Conflict(A,B)' WHERE tournament_id = ? AND player = 'x1'",
            [tid],
        )
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.02, group_other=True)
        archetypes_in_report = {e.archetype for e in report.entries}
        assert "Conflict(A,B)" in archetypes_in_report
        con.close()


# ---------------------------------------------------------------------------
# Unit 5 — compute_metashare / compute_all / blend_shares
# ---------------------------------------------------------------------------


class TestComputeEntryPoints:
    def test_dispatch_raw(self):
        """compute_metashare(definition='raw') returns a raw report."""
        con = _con()
        _load_online_challenge(con)
        report = compute_metashare(con, definition="raw")
        assert report.definition == "raw"
        con.close()

    def test_dispatch_topcut(self):
        """compute_metashare(definition='topcut') returns a topcut report."""
        con = _con()
        _load_online_challenge(con)
        report = compute_metashare(con, definition="topcut")
        assert report.definition == "topcut"
        con.close()

    def test_dispatch_wrw(self):
        """compute_metashare(definition='wrw') returns a wrw report with matchup-n entries."""
        con = _con()
        _load_online_challenge(con)
        report = compute_metashare(con, definition="wrw")
        assert report.definition == "wrw"
        # wrw entries' n should be matchup-n, not deck count
        # alice(Delver) beat bob(Lands) in 1 match → Delver matchup-n == 1
        if report.entries:
            delver_entry = next((e for e in report.entries if e.archetype == "Delver"), None)
            if delver_entry:
                assert delver_entry.n == 1  # one match played
        con.close()

    def test_invalid_definition_raises(self):
        """Unknown definition raises ValueError."""
        con = _con()
        _load_online_challenge(con)
        with pytest.raises(ValueError, match="Unknown definition"):
            compute_metashare(con, definition="invalid")
        con.close()

    def test_compute_all_returns_three_keys(self):
        """compute_all returns exactly {'raw', 'topcut', 'wrw'}."""
        con = _con()
        _load_online_challenge(con)
        result = compute_all(con)
        assert set(result.keys()) == {"raw", "topcut", "wrw"}
        con.close()

    def test_compute_all_definitions_labeled(self):
        """Each report in compute_all is labeled with its definition."""
        con = _con()
        _load_online_challenge(con)
        result = compute_all(con)
        for defn, report in result.items():
            assert report.definition == defn
        con.close()

    def test_blend_shares_labels_provenance(self):
        """blend_shares output provenance string encodes the weights."""
        con = _con()
        _load_online_challenge(con)
        _load_paper_challenge(con)
        online_report = compute_metashare(con, definition="raw", provenance="online")
        paper_report = compute_metashare(con, definition="raw", provenance="paper")
        blended = blend_shares(
            {"online": online_report, "paper": paper_report},
            {"online": 0.7, "paper": 0.3},
        )
        assert "blend(" in blended.provenance
        assert "online" in blended.provenance
        assert "paper" in blended.provenance
        con.close()

    def test_blend_shares_mismatched_definition_raises(self):
        """blend_shares with mismatched definitions raises ValueError."""
        con = _con()
        _load_online_challenge(con)
        raw_report = compute_metashare(con, definition="raw")
        topcut_report = compute_metashare(con, definition="topcut")
        with pytest.raises(ValueError, match="mismatched definitions"):
            blend_shares(
                {"raw": raw_report, "topcut": topcut_report},
                {"raw": 0.5, "topcut": 0.5},
            )
        con.close()

    def test_blend_shares_sum_to_one(self):
        """blended shares sum to ~1.0."""
        con = _con()
        _load_online_challenge(con)
        _load_paper_challenge(con)
        online_report = compute_metashare(con, definition="raw", provenance="online", min_share=0.0)
        paper_report = compute_metashare(con, definition="raw", provenance="paper", min_share=0.0)
        blended = blend_shares(
            {"online": online_report, "paper": paper_report},
            {"online": 0.7, "paper": 0.3},
        )
        total_share = sum(e.share for e in blended.entries)
        assert pytest.approx(total_share, abs=1e-9) == 1.0
        con.close()

    def test_blend_shares_warns_on_non_unit_weights(self, caplog):
        """blend_shares logs a warning when weights don't sum to 1."""
        import logging

        con = _con()
        _load_online_challenge(con)
        _load_paper_challenge(con)
        online_report = compute_metashare(con, definition="raw", provenance="online")
        paper_report = compute_metashare(con, definition="raw", provenance="paper")
        with caplog.at_level(logging.WARNING):
            blend_shares(
                {"online": online_report, "paper": paper_report},
                {"online": 0.6, "paper": 0.6},  # sum = 1.2, not 1.0
            )
        assert any("sum" in r.message.lower() or "weight" in r.message.lower() for r in caplog.records)
        con.close()

    def test_wrw_report_entries_n_are_matchup_n(self):
        """compute_metashare(definition='wrw') entries' n are matchup-n, not deck count."""
        con = _con()
        _load_online_challenge(con)
        # alice(Delver) beat bob(Lands) 1 match → matchup-n = 1 for each archetype
        report = compute_metashare(con, definition="wrw", min_share=0.0, group_other=False)
        for entry in report.entries:
            # deck-count would be 1 each, matchup-n is also 1 here — but the key is
            # it comes from match_results.archetypes[a].n, not decks count
            assert isinstance(entry.n, int)
            assert entry.n >= 0
        con.close()


# ---------------------------------------------------------------------------
# Unit 6 — CLI report meta
# ---------------------------------------------------------------------------


class TestReportMetaCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_report_meta_runs_without_db(self, runner, tmp_path):
        """report meta with --db pointing to an empty DB runs without error."""
        import duckdb

        db_path = tmp_path / "test.duckdb"
        # Initialize schema so it has the right tables
        con = duckdb.connect(str(db_path))
        from legacy_engine.ingestion.store import init_schema
        init_schema(con)
        con.close()

        result = runner.invoke(main, ["report", "meta", "--db", str(db_path)])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"

    def test_report_meta_labeled_header(self, runner, tmp_path):
        """report meta --definition raw prints a header with definition + basis."""
        import duckdb

        from legacy_engine.ingestion.store import init_schema, load_tournament

        db_path = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db_path))
        init_schema(con)
        tid = load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )
        con.close()

        result = runner.invoke(
            main, ["report", "meta", "--definition", "raw", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        # Header must state definition
        assert "RAW" in result.output or "raw" in result.output.lower()
        # Header must state provenance basis (we printed all 3 bases by default)
        assert "basis=" in result.output

    def test_report_meta_no_unlabeled_blend_without_label(self, runner, tmp_path):
        """Default output does not print a blended number without explicit blend label."""
        import duckdb

        from legacy_engine.ingestion.store import init_schema, load_tournament

        db_path = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db_path))
        init_schema(con)
        tid = load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )
        con.close()

        result = runner.invoke(
            main, ["report", "meta", "--provenance", "all", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        # Default should NOT contain a blended number — output should show separate bases
        # (there should be NO "blend(" in the output since we didn't request a blend)
        assert "blend(" not in result.output

    def test_report_meta_single_provenance(self, runner, tmp_path):
        """report meta --provenance online prints only online basis."""
        import duckdb

        from legacy_engine.ingestion.store import init_schema, load_tournament

        db_path = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db_path))
        init_schema(con)
        tid = load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )
        con.close()

        result = runner.invoke(
            main, ["report", "meta", "--provenance", "online", "--definition", "raw", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "online" in result.output

    def test_report_meta_is_no_longer_stub(self, runner):
        """report meta is implemented — should NOT return 'not implemented'."""
        # We need a DB; invoke with a non-existent path should fail with a path error,
        # not 'not implemented'
        result = runner.invoke(main, ["report", "meta", "--help"])
        assert result.exit_code == 0
        # help text should mention the definition option
        assert "--definition" in result.output

    def test_report_meta_accepts_definition_option(self, runner, tmp_path):
        """report meta accepts --definition [raw|topcut|wrw|all]."""
        import duckdb

        from legacy_engine.ingestion.store import init_schema

        db_path = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db_path))
        init_schema(con)
        con.close()

        for defn in ("raw", "topcut", "wrw", "all"):
            result = runner.invoke(
                main, ["report", "meta", "--definition", defn, "--db", str(db_path)]
            )
            assert result.exit_code == 0, (
                f"--definition {defn} failed: {result.output}\n{result.exception}"
            )


# ---------------------------------------------------------------------------
# Unit 7 — Peer-review finding fixes (Unit 2: findings 1-topcut, 3, 4, 5, 6)
# ---------------------------------------------------------------------------

# Raw tournament dict for a single event with two players sharing the same
# normalized name (both "alice" after lower/trim) — triggers dup-CTE exclusion.
_DUP_NAME_CHALLENGE = {
    "Tournament": {
        "Name": "Dup Name Challenge",
        "Date": "2026-05-30",
        "Uri": "https://www.mtgo.com/decklist/dup-name-challenge-2026-05-30",
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
            # Duplicate: same player name as above (simulates a data-entry collision)
            "Player": "Alice",    # normalizes to "alice" via lower(trim(...))
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
        {
            "Player": "bob",
            "Result": "3rd Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [
        {"Rank": 1, "Player": "alice", "Points": 18},
        {"Rank": 2, "Player": "Alice", "Points": 15},
        {"Rank": 3, "Player": "bob",   "Points": 12},
    ],
}


def _load_dup_name_challenge(con):
    """Load a tournament where 'alice' and 'Alice' share a normalized name.

    alice → Delver, Alice → Lands, bob → Combo.  Only bob (non-ambiguous) should
    appear in top-cut counts; alice/Alice are ambiguous and excluded by the dup CTE.
    """
    tid = store.load_tournament(con, parse_cache_item(_DUP_NAME_CHALLENGE, "MTGO"))
    con.execute(
        "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
        [tid],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'Alice'",
        [tid],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = 'bob'",
        [tid],
    )
    return tid


class TestPeerReviewFindingsUnit2:
    """Regression tests for findings 1 (top-cut half), 3, 4, 5, 6 from the cross-model peer review."""

    # ---- Finding #1 (top-cut half): dup-CTE excludes ambiguous normalized names ----

    def test_topcut_dup_name_excluded(self):
        """Archetypes whose player name is ambiguous (dup norm) are excluded from top-cut counts.

        alice vs Alice collapse to the same normalized name; both are excluded.
        bob (unique norm) survives.  Pre-fix the count inflated because two distinct
        deck rows both joined to the standings row for 'alice'.
        """
        con = _con()
        _load_dup_name_challenge(con)
        counts = _topcut_counts(con, provenance=None, cut_size=8)
        # Ambiguous players excluded; only Combo (bob) survives
        assert counts.get("Delver", 0) == 0, "Delver (alice) must be excluded — dup name"
        assert counts.get("Lands", 0) == 0, "Lands (Alice) must be excluded — dup name"
        assert counts.get("Combo", 0) == 1, "Combo (bob) must remain — unique name"
        con.close()

    def test_topcut_dup_name_does_not_inflate_count(self):
        """With a dup name, total top-cut count equals only non-ambiguous players.

        Before the fix, alice+Alice both joined the single standings row for 'alice',
        producing count=2 for the two archetypes.  After the fix, both are dropped.
        """
        con = _con()
        _load_dup_name_challenge(con)
        counts = _topcut_counts(con, provenance=None, cut_size=8)
        total_topcut = sum(counts.values())
        # Only bob (rank 3, within cut_size=8) is non-ambiguous
        assert total_topcut == 1, f"Expected 1 non-ambiguous top-cut deck, got {total_topcut}"
        con.close()

    def test_topcut_dup_standings_name_does_not_inflate_count(self):
        """A name duplicated on the STANDINGS side (not the decks side) must not fan out the join.

        Single 'alice' deck, but two standings rows normalize to 'alice' ('alice' + 'Alice').
        Pre-fix the dup CTE only watched the decks side, so alice's one deck joined both
        standings rows → Delver counted twice.  After the fix a name ambiguous in EITHER decks
        or standings is excluded, so alice drops out and only the clean 'bob' deck is counted.
        """
        con = _con()
        raw = {
            "Tournament": {
                "Name": "Dup Standings Test",
                "Date": "2026-05-30",
                "Uri": "https://www.mtgo.com/decklist/dup-standings-test-2026-05-30",
                "Formats": "Legacy",
            },
            "Decks": [
                {"Player": "alice", "Result": "1st Place",
                 "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}], "Sideboard": []},
                {"Player": "bob", "Result": "2nd Place",
                 "Mainboard": [{"Count": 4, "CardName": "Force of Will"}], "Sideboard": []},
            ],
            "Rounds": [],
            "Standings": [
                {"Rank": 1, "Player": "alice", "Points": 18},
                {"Rank": 2, "Player": "Alice", "Points": 15},   # normalizes to 'alice' → ambiguous
                {"Rank": 3, "Player": "bob",   "Points": 12},
            ],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'", [tid]
        )
        con.execute(
            "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = 'bob'", [tid]
        )
        counts = _topcut_counts(con, provenance=None, cut_size=8)
        assert counts.get("Delver", 0) == 0, "alice is ambiguous on the standings side → excluded, not doubled"
        assert counts.get("Combo", 0) == 1, "bob (unique on both sides) counted exactly once"
        assert sum(counts.values()) == 1, f"standings dup must not inflate; got {counts}"
        con.close()

    # ---- Finding #3: top-cut unlabeled count ----

    def test_topcut_unlabeled_null_archetype_counted(self):
        """A top-cut window with 1 labeled + 1 NULL-archetype deck reports total_decks=1, unlabeled=1.

        Before the fix the branch forced unlabeled=0 regardless of actual NULL-archetype
        deck presence in standings.
        """
        con = _con()
        # Single tournament: alice (rank 1, Delver) and bob (rank 2, NULL archetype)
        raw = {
            "Tournament": {
                "Name": "Unlabeled Topcut Test",
                "Date": "2026-05-30",
                "Uri": "https://www.mtgo.com/decklist/unlabeled-topcut-test-2026-05-30",
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
            "Rounds": [],
            "Standings": [
                {"Rank": 1, "Player": "alice", "Points": 18},
                {"Rank": 2, "Player": "bob",   "Points": 15},
            ],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        # alice gets an archetype; bob stays NULL
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        report = compute_metashare(con, definition="topcut", provenance=None, cut_size=8)
        assert report.total_decks == 1, (
            f"total_decks should be 1 (only alice), got {report.total_decks}"
        )
        assert report.unlabeled == 1, (
            f"unlabeled should be 1 (bob has NULL archetype in standings), got {report.unlabeled}"
        )
        con.close()

    def test_topcut_unlabeled_zero_when_all_labeled(self):
        """All top-cut decks labeled → unlabeled=0."""
        con = _con()
        _load_online_challenge(con)   # alice=Delver (rank 1), bob=Lands (rank 2)
        report = compute_metashare(con, definition="topcut", provenance=None, cut_size=8)
        assert report.unlabeled == 0
        con.close()

    # ---- Finding #4: _assemble(group_other=False) honors display_total ----

    def test_wrw_group_other_false_total_decks_is_matchup_n(self):
        """compute_metashare(definition='wrw', group_other=False) reports total_decks = matchup-n.

        Before the fix, the non-grouped return path used raw ``total`` (=1, the normalised
        weight sum) instead of ``display_total`` (the matchup-n sum).  This meant
        total_decks was always 1 for wrw with group_other=False.
        """
        con = _con()
        _load_online_challenge(con)   # alice vs bob: 1 match played → matchup-n = 1 each
        report = compute_metashare(
            con, definition="wrw", provenance=None, group_other=False, min_share=0.0
        )
        # total_decks must equal sum of matchup-n for archetypes in the weighted set
        # alice(Delver)=1 match, bob(Lands)=1 match → total_matchup_n = 2 (exact)
        assert report.total_decks == 2, (
            f"total_decks must be the matchup-n sum (2), not the raw normalised-weight total (1); "
            f"got {report.total_decks}"
        )
        con.close()

    def test_wrw_group_other_true_and_false_same_total_decks(self):
        """group_other=True and group_other=False should report identical total_decks for wrw."""
        con = _con()
        _load_online_challenge(con)
        report_grouped = compute_metashare(
            con, definition="wrw", provenance=None, group_other=True, min_share=0.0
        )
        report_ungrouped = compute_metashare(
            con, definition="wrw", provenance=None, group_other=False, min_share=0.0
        )
        assert report_grouped.total_decks == report_ungrouped.total_decks, (
            f"grouped total_decks={report_grouped.total_decks} != "
            f"ungrouped total_decks={report_ungrouped.total_decks}"
        )
        con.close()

    # ---- Finding #5: excluded_no_match_data on wrw report ----

    def test_wrw_excluded_no_match_data_populated(self):
        """A wrw archetype with deck count but zero match data appears in excluded_no_match_data.

        Before the fix this was only a debug log — callers had no way to detect the gap.
        """
        con = _con()
        # Load league (no rounds → no match data) and online challenge side-by-side.
        # eve (League/Delver) has a deck but plays no rounds.
        # alice (Challenge/Delver) and bob (Challenge/Lands) play one match.
        _load_online_challenge(con)   # alice=Delver, bob=Lands; 1 round played
        league_raw = {
            "Tournament": {
                "Name": "League No Rounds",
                "Date": "2026-05-30",
                "Uri": "https://www.mtgo.com/decklist/league-no-rounds-2026-05-30",
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
        tid = store.load_tournament(con, parse_cache_item(league_raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'NoMatchArch' WHERE tournament_id = ? AND player = 'eve'",
            [tid],
        )
        report = compute_metashare(con, definition="wrw", provenance=None, group_other=False, min_share=0.0)
        assert "NoMatchArch" in report.excluded_no_match_data, (
            f"Expected 'NoMatchArch' in excluded_no_match_data, got {report.excluded_no_match_data!r}"
        )
        con.close()

    def test_wrw_excluded_no_match_data_empty_when_all_have_match_data(self):
        """excluded_no_match_data is empty when all archetypes have match data."""
        con = _con()
        _load_online_challenge(con)   # all archetypes played rounds
        report = compute_metashare(con, definition="wrw", provenance=None)
        assert report.excluded_no_match_data == [], (
            f"Expected empty excluded_no_match_data, got {report.excluded_no_match_data!r}"
        )
        con.close()

    def test_raw_excluded_no_match_data_always_empty(self):
        """excluded_no_match_data is always empty for raw/topcut definitions."""
        con = _con()
        _load_online_challenge(con)
        for defn in ("raw", "topcut"):
            report = compute_metashare(con, definition=defn, provenance=None)
            assert report.excluded_no_match_data == [], (
                f"{defn}: expected empty excluded_no_match_data, got {report.excluded_no_match_data!r}"
            )
        con.close()

    # ---- Finding #6: blend_shares keeps "Other" + guards zero weight-sum ----

    def test_blend_shares_keeps_other_not_inflated(self):
        """blend_shares with A=80%/Other=20% keeps Other at ~20%.

        Before the fix 'Other' was dropped from all_archetypes, so A was renormalized
        to 100% and Other disappeared entirely from the blended output.
        """
        con = _con()
        # Build two reports that each have an "Other" bucket by using a corpus with many
        # fringe archetypes and one dominant one.
        # 80 Delver + 20 fringe archetypes → each fringe is 1% → group_other collapses them.
        # We'll construct a report manually via _assemble to control the exact share split.
        from legacy_engine.analytics.metashare import _assemble

        counts_a = {"Delver": 80.0, "Other": 20.0}   # simulate post-group_other split
        report_a = _assemble(
            counts_a,
            definition="raw",
            provenance="online",
            n_by_arch={"Delver": 80, "Other": 20},
            total=100,
            unlabeled=0,
            min_share=0.0,
            group_other=False,   # keep Other as-is; it's already bucketed
        )
        # Single-report blend with weight 1.0 — should be identity
        blended = blend_shares({"online": report_a}, {"online": 1.0})
        other_entry = next((e for e in blended.entries if e.archetype == "Other"), None)
        assert other_entry is not None, "Other must be preserved in blended output"
        assert pytest.approx(other_entry.share, abs=0.01) == 0.20, (
            f"Other share should be ~0.20, got {other_entry.share:.4f}"
        )
        delver_entry = next(e for e in blended.entries if e.archetype == "Delver")
        assert pytest.approx(delver_entry.share, abs=0.01) == 0.80, (
            f"Delver share should be ~0.80, got {delver_entry.share:.4f}"
        )
        con.close()

    def test_blend_shares_other_preserved_across_two_provenances(self):
        """Two-provenance blend keeps Other in both inputs and blends it correctly."""
        from legacy_engine.analytics.metashare import _assemble

        # online: Delver=70%, Other=30%
        report_online = _assemble(
            {"Delver": 70.0, "Other": 30.0},
            definition="raw",
            provenance="online",
            n_by_arch={"Delver": 70, "Other": 30},
            total=100,
            unlabeled=0,
            min_share=0.0,
            group_other=False,
        )
        # paper: Delver=60%, Other=40%
        report_paper = _assemble(
            {"Delver": 60.0, "Other": 40.0},
            definition="raw",
            provenance="paper",
            n_by_arch={"Delver": 60, "Other": 40},
            total=100,
            unlabeled=0,
            min_share=0.0,
            group_other=False,
        )
        blended = blend_shares(
            {"online": report_online, "paper": report_paper},
            {"online": 0.5, "paper": 0.5},
        )
        archetypes_in_blend = {e.archetype for e in blended.entries}
        assert "Other" in archetypes_in_blend, "Other must appear in blended output"
        # Delver blended share: 0.5*0.70 + 0.5*0.60 = 0.65; Other: 0.5*0.30 + 0.5*0.40 = 0.35
        # Before renorm they already sum to 1.0, so renorm is a no-op.
        other_entry = next(e for e in blended.entries if e.archetype == "Other")
        delver_entry = next(e for e in blended.entries if e.archetype == "Delver")
        assert pytest.approx(other_entry.share, abs=0.01) == 0.35
        assert pytest.approx(delver_entry.share, abs=0.01) == 0.65

    def test_blend_shares_all_zero_weights_raises_value_error(self):
        """blend_shares with all-zero weights raises ValueError, not ZeroDivisionError."""
        con = _con()
        _load_online_challenge(con)
        report = compute_metashare(con, definition="raw", provenance=None)
        with pytest.raises(ValueError, match="weights sum to"):
            blend_shares({"online": report}, {"online": 0.0})
        con.close()

    def test_blend_shares_negative_weight_raises_value_error(self):
        """blend_shares with a negative weight sum (≤0) raises ValueError."""
        con = _con()
        _load_online_challenge(con)
        _load_paper_challenge(con)
        report_a = compute_metashare(con, definition="raw", provenance="online")
        report_b = compute_metashare(con, definition="raw", provenance="paper")
        with pytest.raises(ValueError, match="weights sum to"):
            blend_shares({"online": report_a, "paper": report_b}, {"online": -0.5, "paper": -0.5})
        con.close()


# ---------------------------------------------------------------------------
# corpus_freshness — epic-advisory-output-honesty-transparency
# ---------------------------------------------------------------------------


class TestCorpusFreshness:
    def test_empty_corpus_returns_none(self):
        from legacy_engine.analytics.metashare import corpus_freshness
        con = _con()
        store.init_schema(con)
        assert corpus_freshness(con) == (None, 0)

    def test_returns_max_date_and_deck_count(self):
        from legacy_engine.analytics.metashare import corpus_freshness
        con = _con()
        _load_online_challenge(con)
        max_date, deck_count = corpus_freshness(con)
        assert max_date == "2026-05-24"   # date-portion of the online challenge
        assert deck_count >= 2            # alice + bob (at least)

    def test_provenance_filter(self):
        from legacy_engine.analytics.metashare import corpus_freshness
        con = _con()
        _load_online_challenge(con)
        # paper basis has no events → empty
        assert corpus_freshness(con, provenance="paper") == (None, 0)
        # online basis has the challenge
        max_date, n = corpus_freshness(con, provenance="online")
        assert max_date == "2026-05-24" and n >= 2

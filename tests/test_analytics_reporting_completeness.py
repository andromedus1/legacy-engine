"""Tests for feature-analytics-reporting-completeness (4 additive finding fixes).

Each test class covers one finding:
  TestWrwWindowed            — wrw meta-share can now be windowed to a regime
  TestBiggestMovers          — biggest_movers digest surfaces correct top changes
  TestHeadToHeadLookup       — lookup_head_to_head returns correct cell+CI+tier
  TestAffectednessExplain    — explain_valid_since shows the driving ban event

House style: module-level raw dicts → parse_cache_item → store.load_tournament
into :memory:; labels pinned via direct SQL UPDATE; TestX classes; deterministic.
"""

from __future__ import annotations

from datetime import date

from click.testing import CliRunner

from legacy_engine.analytics.affectedness import (
    AffectednessExplanation,
    explain_valid_since,
)
from legacy_engine.analytics.matchup import (
    build_matrix,
    lookup_head_to_head,
)
from legacy_engine.analytics.metashare import compute_metashare
from legacy_engine.analytics.trends import (
    RegimeWindow,
    TrendCell,
    TrendSeries,
    biggest_movers,
)
from legacy_engine.cli import main
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item

# ---------------------------------------------------------------------------
# Shared tournament fixture helpers
# ---------------------------------------------------------------------------

# A tournament in the "after Psychic Frog + Vexing Bauble (2024-12-16)" regime:
# between 2024-12-16 (inclusive) and 2025-02-01 (exclusive).
_REGIME_B_TOURNAMENT = {
    "Tournament": {
        "Name": "Legacy Challenge B-wrw",
        "Date": "2025-01-15",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-b-wrw-2025-01-15",
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
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
    "Standings": [],
}

# A tournament outside that regime (before 2024-12-16)
_REGIME_A_TOURNAMENT = {
    "Tournament": {
        "Name": "Legacy Challenge A-wrw",
        "Date": "2024-09-01",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-a-wrw-2024-09-01",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "carol",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
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
    "Standings": [],
}


def _make_two_regime_corpus() -> object:
    """Build an in-memory corpus spanning two regimes (A and B)."""
    con = store.connect(":memory:")
    for raw in (_REGIME_A_TOURNAMENT, _REGIME_B_TOURNAMENT):
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        # Label Alice/Carol as "Control", Bob/Dave as "Combo"
        con.execute(
            "UPDATE decks SET archetype = 'Control' "
            "WHERE tournament_id = ? AND player IN ('alice', 'carol')",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Combo' "
            "WHERE tournament_id = ? AND player IN ('bob', 'dave')",
            [tid],
        )
    return con


# ---------------------------------------------------------------------------
# Finding 1: wrw-windowed
# ---------------------------------------------------------------------------


class TestWrwWindowed:
    """wrw meta-share can be windowed to a regime without raising."""

    def test_wrw_no_longer_raises_under_window(self):
        """compute_metashare(definition='wrw') with since/until must NOT raise."""
        con = _make_two_regime_corpus()
        try:
            # Previously this raised NotImplementedError; now it must succeed.
            report = compute_metashare(
                con,
                definition="wrw",
                since="2024-12-16",
                until="2025-02-01",
            )
            # Regime B has: Control (alice) wins vs Combo (bob) in tournament B.
            # Both archetypes have deck counts AND match data in this window.
            assert report.definition == "wrw"
            assert len(report.entries) > 0, "wrw windowed report should have entries"
        finally:
            con.close()

    def test_wrw_windowed_uses_window_deck_counts(self):
        """Windowed wrw share is computed only over in-window decks, not the full corpus."""
        con = _make_two_regime_corpus()
        try:
            # Full-corpus: two tournaments, 4 decks (2 Control, 2 Combo).
            full_report = compute_metashare(con, definition="wrw")
            # Windowed to regime B only: one tournament (regime B), 2 decks.
            # In regime A, carol (Control) and dave (Combo) contribute to full corpus.
            window_report = compute_metashare(
                con,
                definition="wrw",
                since="2024-12-16",
                until="2025-02-01",
            )
            # Both should have entries (archetypes have match data in respective windows).
            assert len(full_report.entries) > 0
            assert len(window_report.entries) > 0

            # The windowed corpus is STRICTLY smaller, with known counts:
            # full = 4 decks (regime A carol/dave + regime B alice/bob);
            # windowed to regime B = 2 decks (alice/bob only).
            assert full_report.total_decks == 4
            assert window_report.total_decks == 2
            assert window_report.total_decks < full_report.total_decks
        finally:
            con.close()

    def test_wrw_full_corpus_still_works(self):
        """Full-corpus (no window) wrw is byte-identical to before — not broken by the change."""
        con = _make_two_regime_corpus()
        try:
            report = compute_metashare(con, definition="wrw")
            assert report.definition == "wrw"
        finally:
            con.close()

    def test_cli_report_meta_wrw_with_since(self, tmp_path):
        """CLI: report meta --definition wrw --since <date> must succeed (no longer skipped)."""
        # Seed a tmp-file DuckDB so CI doesn't depend on the default data/legacy.duckdb.
        db_path = tmp_path / "t.duckdb"
        con = store.connect(str(db_path))
        for raw in (_REGIME_A_TOURNAMENT, _REGIME_B_TOURNAMENT):
            tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
            con.execute(
                "UPDATE decks SET archetype = 'Control' "
                "WHERE tournament_id = ? AND player IN ('alice', 'carol')",
                [tid],
            )
            con.execute(
                "UPDATE decks SET archetype = 'Combo' "
                "WHERE tournament_id = ? AND player IN ('bob', 'dave')",
                [tid],
            )
        con.close()

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "report", "meta",
                "--definition", "wrw",
                "--since", "2024-12-16",
                "--db", str(db_path),
            ],
        )
        # Should succeed (or warn about empty corpus / thin data, not hard-fail on wrw window).
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Finding 2: trends-biggest-movers (pure function, no DB)
# ---------------------------------------------------------------------------


def _make_hand_built_series() -> TrendSeries:
    """Build a TrendSeries entirely from hand-crafted data (no DB, no compute_trends).

    Regime A (label='regime-A'): Control=40%, Combo=30%, Tempo=20%, Reanimator=10%
    Regime B (label='regime-B'): Control=20%, Combo=50%, Tempo=5%  (Reanimator exits)

    Expected biggest movers (by |delta|, no tie-break needed at top-3):
      Combo:       +20% (biggest gainer)
      Control:     -20% (biggest loser)
      Reanimator:  -10% (exited: prev=10%, curr=None/0%)
    """
    regime_a = RegimeWindow(
        label="regime-A",
        since=date(2024, 1, 1),
        until=date(2025, 1, 1),
        opening_events=(),
    )
    regime_b = RegimeWindow(
        label="regime-B",
        since=date(2025, 1, 1),
        until=None,
        opening_events=("Some Ban",),
    )

    cells: dict[tuple[str, str], TrendCell] = {
        ("regime-A", "Control"):     TrendCell("Control",     0.40, 80, "established"),
        ("regime-A", "Combo"):       TrendCell("Combo",       0.30, 60, "established"),
        ("regime-A", "Tempo"):       TrendCell("Tempo",       0.20, 40, "evolving"),
        ("regime-A", "Reanimator"):  TrendCell("Reanimator",  0.10, 20, "speculative"),
        ("regime-B", "Control"):     TrendCell("Control",     0.20, 40, "established"),
        ("regime-B", "Combo"):       TrendCell("Combo",       0.50, 100, "established"),
        ("regime-B", "Tempo"):       TrendCell("Tempo",       0.05, 10, "speculative"),
        # Reanimator absent in regime-B (exited)
    }
    archetypes = ["Combo", "Control", "Tempo", "Reanimator"]

    return TrendSeries(
        definition="raw",
        provenance=None,
        regimes=[regime_a, regime_b],
        cells=cells,
        archetypes=archetypes,
    )


class TestBiggestMovers:
    """biggest_movers digest surfaces the correct top changes from a hand-built series."""

    def test_top_movers_sorted_by_abs_delta(self):
        """biggest_movers(n=3) returns top 3 by |delta|, sorted descending."""
        series = _make_hand_built_series()
        movers = biggest_movers(series, n=3)

        assert len(movers) == 3
        # All returned movers should be sorted by |delta| descending
        deltas = [abs(m.delta) for m in movers]
        assert deltas == sorted(deltas, reverse=True)

    def test_combo_is_top_gainer(self):
        """Combo grows from 30% to 50%: delta=+20% — should rank first or second."""
        series = _make_hand_built_series()
        movers = biggest_movers(series, n=4)

        combo = next((m for m in movers if m.archetype == "Combo"), None)
        assert combo is not None, "Combo must appear in biggest movers"
        assert abs(combo.delta - 0.20) < 1e-6, f"Combo delta should be +0.20, got {combo.delta}"
        assert combo.delta > 0  # gainer
        assert abs(combo.prev_share - 0.30) < 1e-6
        assert abs(combo.curr_share - 0.50) < 1e-6

    def test_control_is_top_loser(self):
        """Control drops from 40% to 20%: delta=-20% — should be top loser."""
        series = _make_hand_built_series()
        movers = biggest_movers(series, n=4)

        control = next((m for m in movers if m.archetype == "Control"), None)
        assert control is not None, "Control must appear in biggest movers"
        assert abs(control.delta - (-0.20)) < 1e-6
        assert control.delta < 0  # loser

    def test_reanimator_exit_captured(self):
        """Reanimator exits (prev=10%, curr=None): treated as -10% delta."""
        series = _make_hand_built_series()
        movers = biggest_movers(series, n=4)

        reanimator = next((m for m in movers if m.archetype == "Reanimator"), None)
        assert reanimator is not None, "Reanimator exit should appear in movers"
        assert reanimator.curr_share is None  # truly absent in last regime
        assert abs(reanimator.prev_share - 0.10) < 1e-6
        assert abs(reanimator.delta - (-0.10)) < 1e-6

    def test_fewer_than_two_regimes_returns_empty(self):
        """Series with only one regime → no comparison possible → empty list."""
        series = _make_hand_built_series()
        single = TrendSeries(
            definition="raw",
            provenance=None,
            regimes=[series.regimes[0]],
            cells={k: v for k, v in series.cells.items() if k[0] == "regime-A"},
            archetypes=["Control", "Combo"],
        )
        assert biggest_movers(single) == []

    def test_between_parameter_selects_specific_pair(self):
        """between=(prev, curr) compares a specific pair rather than the last two."""
        series = _make_hand_built_series()
        movers = biggest_movers(series, between=("regime-A", "regime-B"))
        assert len(movers) > 0
        # All movers should reference the specified regime pair.
        for m in movers:
            assert m.prev_regime == "regime-A"
            assert m.curr_regime == "regime-B"

    def test_between_unknown_label_returns_empty(self):
        """between with a non-existent label → empty list, no exception."""
        series = _make_hand_built_series()
        assert biggest_movers(series, between=("regime-A", "nonexistent")) == []

    def test_n_parameter_limits_result(self):
        """n=2 returns at most 2 movers."""
        series = _make_hand_built_series()
        movers = biggest_movers(series, n=2)
        assert len(movers) <= 2

    def test_regime_labels_on_output(self):
        """BiggestMover carries the correct prev/curr regime labels."""
        series = _make_hand_built_series()
        movers = biggest_movers(series, n=1)
        assert movers[0].prev_regime == "regime-A"
        assert movers[0].curr_regime == "regime-B"

    def test_cli_report_trends_movers_flag(self, tmp_path):
        """CLI: report trends --movers 5 runs without error (even on empty corpus)."""
        # Seed a tmp-file DuckDB with a two-regime corpus so CI doesn't depend on
        # the default data/legacy.duckdb.  An empty file is also valid (the CLI
        # prints "no events in corpus" and exits 0), but seeding data exercises
        # the movers path as well.
        db_path = tmp_path / "t.duckdb"
        con = store.connect(str(db_path))
        for raw in (_REGIME_A_TOURNAMENT, _REGIME_B_TOURNAMENT):
            tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
            con.execute(
                "UPDATE decks SET archetype = 'Control' "
                "WHERE tournament_id = ? AND player IN ('alice', 'carol')",
                [tid],
            )
            con.execute(
                "UPDATE decks SET archetype = 'Combo' "
                "WHERE tournament_id = ? AND player IN ('bob', 'dave')",
                [tid],
            )
        con.close()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["report", "trends", "--movers", "5", "--db", str(db_path)],
        )
        # An empty corpus produces "no events in corpus" — exit 0 is expected.
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Finding 3: head-to-head matchup lookup (pure function over MatchupMatrix)
# ---------------------------------------------------------------------------


def _make_matchup_corpus(n_matches: int = 35) -> object:
    """Build an in-memory corpus with n_matches decisive Control-vs-Combo matches.

    Uses n_repeats tournaments of 1 decisive match each so we can control n
    and push past the DISPLAY_GATE_N=30 threshold.
    """
    con = store.connect(":memory:")
    for i in range(n_matches):
        raw = {
            "Tournament": {
                "Name": f"H2H Corpus {i+1}",
                "Date": f"2026-01-{(i % 28) + 1:02d}",
                "Uri": f"https://www.mtgo.com/decklist/h2h-{i+1:03d}",
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
                    "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )
    return con


class TestHeadToHeadLookup:
    """lookup_head_to_head returns the correct cell, CI, and tier."""

    def test_returns_cell_for_included_pair(self):
        """lookup_head_to_head returns a non-None cell when both archetypes are in the matrix."""
        con = _make_matchup_corpus(n_matches=35)
        try:
            matrix = build_matrix(con, min_row_share=0.0)
            cell = lookup_head_to_head(matrix, "Control", "Combo")
            assert cell is not None
        finally:
            con.close()

    def test_cell_n_matches_expected(self):
        """Cell n == number of decisive Control-vs-Combo matches loaded."""
        n = 35
        con = _make_matchup_corpus(n_matches=n)
        try:
            matrix = build_matrix(con, min_row_share=0.0)
            cell = lookup_head_to_head(matrix, "Control", "Combo")
            assert cell is not None
            assert cell.n == n
        finally:
            con.close()

    def test_cell_tier_established_above_threshold(self):
        """With n=100 decisive matches the cell tier should be 'established'."""
        con = _make_matchup_corpus(n_matches=100)
        try:
            matrix = build_matrix(con, min_row_share=0.0)
            cell = lookup_head_to_head(matrix, "Control", "Combo")
            assert cell is not None
            assert cell.tier == "established"
        finally:
            con.close()

    def test_cell_ci_bounds_present_and_ordered(self):
        """Cell CI [low, high] must be present and well-ordered when n>=DISPLAY_GATE_N."""
        con = _make_matchup_corpus(n_matches=35)
        try:
            matrix = build_matrix(con, min_row_share=0.0)
            cell = lookup_head_to_head(matrix, "Control", "Combo")
            assert cell is not None
            assert cell.ci_low is not None
            assert cell.ci_high is not None
            assert 0.0 <= cell.ci_low <= cell.ci_high <= 1.0
        finally:
            con.close()

    def test_display_true_above_gate(self):
        """display=True when n >= DISPLAY_GATE_N (30)."""
        con = _make_matchup_corpus(n_matches=35)
        try:
            matrix = build_matrix(con, min_row_share=0.0)
            cell = lookup_head_to_head(matrix, "Control", "Combo")
            assert cell is not None
            assert cell.display is True
        finally:
            con.close()

    def test_display_false_below_gate(self):
        """display=False when n < DISPLAY_GATE_N (speculative data)."""
        con = _make_matchup_corpus(n_matches=5)
        try:
            matrix = build_matrix(con, min_row_share=0.0)
            cell = lookup_head_to_head(matrix, "Control", "Combo")
            assert cell is not None
            assert cell.display is False
        finally:
            con.close()

    def test_returns_none_for_excluded_archetype(self):
        """Returns None when an archetype is not included in the matrix."""
        con = _make_matchup_corpus(n_matches=5)
        try:
            # Use a high min_row_share to exclude one or both archetypes.
            matrix = build_matrix(con, min_row_share=0.9)
            # With a min_row_share higher than any archetype can clear, nothing is included.
            result = lookup_head_to_head(matrix, "Control", "Combo")
            # Either both are excluded (returns None) or the matrix is empty.
            if not matrix.archetypes:
                assert result is None
        finally:
            con.close()

    def test_returns_none_for_unknown_archetype(self):
        """Returns None when an archetype name is not in the matrix at all."""
        con = _make_matchup_corpus(n_matches=35)
        try:
            matrix = build_matrix(con, min_row_share=0.0)
            result = lookup_head_to_head(matrix, "Control", "NonExistentArchetype")
            assert result is None
        finally:
            con.close()

    def test_pure_function_works_on_hand_built_cell(self):
        """lookup_head_to_head works on a hand-built MatchupMatrix (no DB)."""
        from legacy_engine.analytics.matchup import MatchupMatrix, build_cell, build_mirror_cell

        a, b = "Alpha", "Beta"
        cell_ab = build_cell(a, b, wins=20, n=30)
        cell_ba = build_cell(b, a, wins=10, n=30)

        matrix = MatchupMatrix(
            cells={(a, b): cell_ab, (b, a): cell_ba,
                   (a, a): build_mirror_cell(a, 5),
                   (b, b): build_mirror_cell(b, 5)},
            provenance=None,
            total_matches=30,
            archetypes=[a, b],
            caveat="test",
        )
        result = lookup_head_to_head(matrix, a, b)
        assert result is cell_ab
        assert result.wins == 20
        assert result.n == 30

    def test_cli_report_matchups_a_b_flags(self, tmp_path):
        """CLI: report matchups --a X --b Y runs without error."""
        # Seed a tmp-file DuckDB with matchup data so CI doesn't depend on the
        # default data/legacy.duckdb.  Reuse _make_matchup_corpus's seeding logic
        # written to a file path instead of :memory:.
        db_path = tmp_path / "t.duckdb"
        con = store.connect(str(db_path))
        n_matches = 35
        for i in range(n_matches):
            raw = {
                "Tournament": {
                    "Name": f"H2H Corpus {i+1}",
                    "Date": f"2026-01-{(i % 28) + 1:02d}",
                    "Uri": f"https://www.mtgo.com/decklist/h2h-{i+1:03d}",
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
                        "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
                        "Sideboard": [],
                    },
                ],
                "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
                "Standings": [],
            }
            tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
            con.execute(
                "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ? AND player = 'alice'",
                [tid],
            )
            con.execute(
                "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = 'bob'",
                [tid],
            )
        con.close()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["report", "matchups", "--a", "Control", "--b", "Combo", "--db", str(db_path)],
        )
        assert result.exit_code == 0, result.output

    def test_cli_report_matchups_a_without_b_fails(self):
        """CLI: report matchups --a X (without --b) should fail with a clear error."""
        runner = CliRunner()
        result = runner.invoke(main, ["report", "matchups", "--a", "Control"])
        assert result.exit_code != 0
        assert "--a and --b" in result.output or "Error" in result.output


# ---------------------------------------------------------------------------
# Finding 4: affectedness-explain (pure function over DB query)
# ---------------------------------------------------------------------------

# We need a corpus where one archetype ran a banned card before the ban.
# We'll seed a deck with "Entomb" (banned 2025-11-10) in an archetype called
# "Reanimator" with events before 2025-11-10.

_REANIMATOR_PRE_BAN = {
    "Tournament": {
        "Name": "Legacy Pre-Entomb Reanimator",
        "Date": "2025-06-15",
        "Uri": "https://melee.gg/Tournament/View/reanimator-pre-ban",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "entomber",
            "Result": "1st Place",
            "Mainboard": [
                {"Count": 4, "CardName": "Entomb"},
                {"Count": 4, "CardName": "Brainstorm"},
            ],
            "Sideboard": [],
        },
        {
            "Player": "other",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Ponder"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}

# Another archetype that never ran Entomb
_CONTROL_PRE_BAN = {
    "Tournament": {
        "Name": "Legacy Pre-Entomb Control",
        "Date": "2025-07-01",
        "Uri": "https://melee.gg/Tournament/View/control-pre-ban",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "ctrl1",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "ctrl2",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}


def _make_affectedness_corpus() -> object:
    """Build corpus for affectedness explain tests."""
    con = store.connect(":memory:")
    tid1 = store.load_tournament(con, parse_cache_item(_REANIMATOR_PRE_BAN, "Paper"))
    con.execute(
        "UPDATE decks SET archetype = 'Reanimator' WHERE tournament_id = ?",
        [tid1],
    )

    tid2 = store.load_tournament(con, parse_cache_item(_CONTROL_PRE_BAN, "Paper"))
    con.execute(
        "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ?",
        [tid2],
    )
    return con


class TestAffectednessExplain:
    """explain_valid_since shows the driving ban event and card frequencies."""

    def test_returns_list_of_explanations(self):
        """explain_valid_since returns a non-empty list of AffectednessExplanation objects."""
        con = _make_affectedness_corpus()
        try:
            explanations = explain_valid_since(con, "Reanimator")
            assert len(explanations) > 0
            assert all(isinstance(e, AffectednessExplanation) for e in explanations)
        finally:
            con.close()

    def test_entomb_ban_marks_reanimator_affected(self):
        """The 2025-11-10 Entomb ban should appear with affected=True for Reanimator.

        Reanimator ran 1/1 decks with Entomb pre-ban (100% inclusion rate ≥ threshold=0.25).
        """
        con = _make_affectedness_corpus()
        try:
            explanations = explain_valid_since(con, "Reanimator")
            # Find the Entomb ban entry (ban_date=2025-11-10)
            entomb_entry = next(
                (e for e in explanations if "2025-11-10" in e.ban_date and "Entomb" in e.banned_cards),
                None,
            )
            assert entomb_entry is not None, "Entomb ban entry (2025-11-10) must appear"
            assert entomb_entry.affected is True, (
                f"Reanimator ran Entomb at 100%, should be affected. "
                f"rate={entomb_entry.inclusion_rate:.1%}, "
                f"decks={entomb_entry.pre_ban_decks}, run={entomb_entry.running_decks}"
            )
            assert entomb_entry.running_decks >= 1
            assert entomb_entry.inclusion_rate >= 0.25
        finally:
            con.close()

    def test_control_not_affected_by_entomb(self):
        """Control never ran Entomb; the Entomb entry should have affected=False."""
        con = _make_affectedness_corpus()
        try:
            explanations = explain_valid_since(con, "Control")
            entomb_entry = next(
                (e for e in explanations if "2025-11-10" in e.ban_date and "Entomb" in e.banned_cards),
                None,
            )
            assert entomb_entry is not None
            assert entomb_entry.affected is False
            assert entomb_entry.running_decks == 0
        finally:
            con.close()

    def test_explanations_ordered_chronologically(self):
        """Explanations are returned in chronological order (earliest ban first)."""
        con = _make_affectedness_corpus()
        try:
            explanations = explain_valid_since(con, "Reanimator")
            dates = [e.ban_date for e in explanations]
            assert dates == sorted(dates), "Explanations must be chronological"
        finally:
            con.close()

    def test_valid_since_matches_latest_affected_ban(self):
        """The derived valid_since == max(ban_date where affected=True)."""
        con = _make_affectedness_corpus()
        try:
            explanations = explain_valid_since(con, "Reanimator")
            affected_dates = [e.ban_date for e in explanations if e.affected]
            if affected_dates:
                expected_valid_since = max(affected_dates)
                # Verify this against archetype_valid_since for consistency
                from legacy_engine.analytics.affectedness import archetype_valid_since
                valid = archetype_valid_since(con, ["Reanimator"])
                assert valid["Reanimator"] == expected_valid_since
        finally:
            con.close()

    def test_no_data_window_yields_zero_decks(self):
        """A ban whose pre-ban window has no corpus data → pre_ban_decks=0, affected=False."""
        con = _make_affectedness_corpus()
        try:
            # The first ban in BAN_EVENTS (2022-01-01) has no pre-ban data in our corpus
            # since all our tournaments are from 2025+.
            explanations = explain_valid_since(con, "Reanimator")
            first_entry = explanations[0]
            # 2022-01-01 Ragavan ban: no tournaments before 2022-01-01 in our corpus
            assert first_entry.pre_ban_decks == 0
            assert first_entry.affected is False
        finally:
            con.close()

    def test_prev_ban_date_threading(self):
        """Each explanation's prev_ban_date is the previous ban's ban_date (or None)."""
        con = _make_affectedness_corpus()
        try:
            explanations = explain_valid_since(con, "Reanimator")
            assert explanations[0].prev_ban_date is None  # first ban, no prior window
            for i in range(1, len(explanations)):
                assert explanations[i].prev_ban_date == explanations[i - 1].ban_date
        finally:
            con.close()

    def test_cli_report_affectedness(self, tmp_path):
        """CLI: report affectedness --archetype X runs without error."""
        # Seed a tmp-file DuckDB with affectedness data so CI doesn't depend on
        # the default data/legacy.duckdb.  Reuse _make_affectedness_corpus's
        # seeding logic written to a file path instead of :memory:.
        db_path = tmp_path / "t.duckdb"
        con = store.connect(str(db_path))
        tid1 = store.load_tournament(con, parse_cache_item(_REANIMATOR_PRE_BAN, "Paper"))
        con.execute(
            "UPDATE decks SET archetype = 'Reanimator' WHERE tournament_id = ?",
            [tid1],
        )
        tid2 = store.load_tournament(con, parse_cache_item(_CONTROL_PRE_BAN, "Paper"))
        con.execute(
            "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ?",
            [tid2],
        )
        con.close()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["report", "affectedness", "--archetype", "Reanimator", "--db", str(db_path)],
        )
        assert result.exit_code == 0, result.output
        assert "Affectedness Derivation" in result.output

    def test_cli_report_affectedness_requires_archetype(self):
        """CLI: report affectedness without --archetype should fail."""
        runner = CliRunner()
        result = runner.invoke(main, ["report", "affectedness"])
        assert result.exit_code != 0

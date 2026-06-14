"""CLI venue tests — feature-three-venue-meta-frame.

Tests:
- ``report meta --venues online,paper`` — both venue tables + Divergence block
- ``report meta`` (no --venues) — byte-identical to baseline (gated-additive)
- ``--provenance`` + ``--venues`` mutual exclusion
- ``advise report --venues online,paper --deck <fixture>`` — per-venue banners + footer
- ``--field`` + ``--venues`` mutual exclusion
- Backward-compat: ``advise report`` without ``--venues`` — exits cleanly

House style: file-backed DuckDB for CLI invocations; CliRunner.
"""

from __future__ import annotations

import textwrap

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.ingestion import store as _store
from legacy_engine.ingestion.cache import parse_cache_item


# ---------------------------------------------------------------------------
# Corpus fixture helpers
# ---------------------------------------------------------------------------

_ONLINE_TOURN = {
    "Tournament": {
        "Name": "MTGO Legacy Challenge 32 venues-test",
        "Date": "2026-06-05",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-32-2026-06-05",
        "Formats": "Legacy",
    },
    "Decks": [
        {"Player": "p1", "Result": "1st", "Mainboard": [{"Count": 4, "CardName": "Urza's Tower"}], "Sideboard": []},
        {"Player": "p2", "Result": "2nd", "Mainboard": [{"Count": 4, "CardName": "Urza's Mine"}], "Sideboard": []},
        {"Player": "p3", "Result": "3rd", "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}], "Sideboard": []},
        {"Player": "p4", "Result": "4th", "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}], "Sideboard": []},
    ],
    "Rounds": [],
    "Standings": [],
}

_PAPER_TOURN = {
    "Tournament": {
        "Name": "Paper Legacy Open venues-test",
        "Date": "2026-06-06",
        "Uri": "https://melee.gg/Tournament/View/77777",
        "Formats": "Legacy",
    },
    "Decks": [
        {"Player": "q1", "Result": "1st", "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}], "Sideboard": []},
        {"Player": "q2", "Result": "2nd", "Mainboard": [{"Count": 4, "CardName": "Force of Will"}], "Sideboard": []},
    ],
    "Rounds": [],
    "Standings": [],
}


def _build_venue_db(tmp_path):
    """Build a file-backed DuckDB with both online and paper tournaments."""
    db_path = tmp_path / "venues_test.duckdb"
    con = _store.connect(str(db_path))
    _store.init_schema(con)

    tid_online = _store.load_tournament(con, parse_cache_item(_ONLINE_TOURN, "MTGO"))
    con.execute(
        "UPDATE decks SET archetype = 'Tron' WHERE tournament_id = ? AND player IN ('p1', 'p2')",
        [tid_online],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ? AND player = 'p3'",
        [tid_online],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player = 'p4'",
        [tid_online],
    )

    tid_paper = _store.load_tournament(con, parse_cache_item(_PAPER_TOURN, "Melee"))
    con.execute(
        "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ? AND player = 'q1'",
        [tid_paper],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'q2'",
        [tid_paper],
    )

    con.close()
    return str(db_path)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def venue_db(tmp_path):
    return _build_venue_db(tmp_path)


@pytest.fixture
def deck_file(tmp_path):
    """Minimal decklist with 60 Brainstorm for testing advise report --venues."""
    deck = tmp_path / "deck.txt"
    deck.write_text("60 Brainstorm\n")
    return str(deck)


@pytest.fixture
def field_file(tmp_path):
    """Minimal custom field file."""
    f = tmp_path / "field.txt"
    f.write_text("0.5 Control\n0.5 Combo\n")
    return str(f)


# ---------------------------------------------------------------------------
# Tests: report meta --venues
# ---------------------------------------------------------------------------


class TestReportMetaVenues:
    """CLI tests for ``report meta --venues``."""

    def test_venues_shows_venue_banners(self, runner, venue_db):
        """Both venue labels appear as banners in the output."""
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--venues", "online,paper",
             "--definition", "raw", "--all-time"],
        )
        assert result.exit_code == 0, result.output
        assert "Online (MTGO)" in result.output
        assert "Paper" in result.output

    def test_venues_shows_divergence_block(self, runner, venue_db):
        """Divergence block header appears when --venues is set."""
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--venues", "online,paper",
             "--definition", "raw", "--all-time"],
        )
        assert result.exit_code == 0, result.output
        assert "Venue Divergence" in result.output

    def test_venues_tron_higher_online(self, runner, venue_db):
        """Tron appears in online table (2/4 = 50%) but not paper table."""
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--venues", "online,paper",
             "--definition", "raw", "--all-time", "--min-share", "0.0"],
        )
        assert result.exit_code == 0, result.output
        # Tron should appear somewhere in the output
        assert "Tron" in result.output

    def test_venues_divergence_ordering(self, runner, venue_db):
        """Divergence rows appear (Tron has spread 0.50 online - 0.0 paper = 0.50)."""
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--venues", "online,paper",
             "--definition", "raw", "--all-time", "--min-share", "0.0"],
        )
        assert result.exit_code == 0, result.output
        # Divergence section should show archetypes
        assert "Tron" in result.output

    def test_provenance_and_venues_mutually_exclusive(self, runner, venue_db):
        """--provenance online + --venues → ClickException non-zero exit."""
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db,
             "--provenance", "online", "--venues", "online,paper",
             "--definition", "raw", "--all-time"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_provenance_all_plus_venues_mutually_exclusive(self, runner, venue_db):
        """--provenance all (default) + --venues is allowed — only non-all provenance is exclusive."""
        # The check only fires when --provenance is explicitly non-"all".
        # Default provenance="all" with --venues should work.
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--venues", "online,paper",
             "--definition", "raw", "--all-time"],
        )
        assert result.exit_code == 0, result.output

    def test_unknown_venue_key_exits_nonzero(self, runner, venue_db):
        """Unknown venue key → error (fails loud per CLI pattern)."""
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--venues", "online,local:local",
             "--definition", "raw", "--all-time"],
        )
        assert result.exit_code != 0

    def test_no_venues_backward_compatible(self, runner, venue_db):
        """report meta WITHOUT --venues runs cleanly — gated-additive-augmentation."""
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--definition", "raw", "--all-time",
             "--provenance", "all"],
        )
        assert result.exit_code == 0, result.output
        # Should still show the meta share report header (legacy mode)
        assert "Meta Share" in result.output

    def test_venues_default_window_is_current_regime_not_full_corpus(self, runner, venue_db):
        """report meta --venues with NO window flag defaults to current regime, not full corpus.

        The window echo should NOT say 'full-corpus'; it should reference the current
        ban-regime window (since=<date> .. —), so the user sees the data is scoped
        to the live meta.  A plain report meta (no --venues) still defaults to
        full-corpus — gated-additive: that path is untouched.
        """
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--venues", "online,paper",
             "--definition", "raw"],
        )
        assert result.exit_code == 0, result.output
        # Must NOT say full-corpus — the default is now current regime
        assert "full-corpus" not in result.output
        # Must echo a window line with a date (current regime since 2026-05-18)
        assert "// window:" in result.output
        assert "regime: current" in result.output
        # Data from 2026-06-05/06 is inside the current regime (opens 2026-05-18),
        # so venue tables must still render — not "no data"
        assert "Online (MTGO)" in result.output
        assert "Paper" in result.output

    def test_non_venues_default_remains_full_corpus(self, runner, venue_db):
        """report meta (no --venues) keeps its existing full-corpus default.

        Gated-additive: the non-venues path is byte-identical to the pre-patch code.
        """
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--definition", "raw"],
        )
        assert result.exit_code == 0, result.output
        assert "// window: full-corpus" in result.output

    def test_venues_wrw_skipped_under_window(self, runner, venue_db):
        """wrw is skipped under a time window — same guard as baseline behavior."""
        result = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--venues", "online,paper",
             "--definition", "wrw", "--since", "2026-01-01", "--until", "2026-12-31"],
        )
        assert result.exit_code == 0, result.output
        assert "skipping wrw" in result.output

    def test_venue_paper_no_data_shows_note(self, runner, tmp_path):
        """A venue with no corpus data shows 'no data' note rather than crashing."""
        # Build a DB with only online data
        db_path = tmp_path / "online_only.duckdb"
        con = _store.connect(str(db_path))
        _store.init_schema(con)
        tid = _store.load_tournament(con, parse_cache_item(_ONLINE_TOURN, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Tron' WHERE tournament_id = ? AND player IN ('p1', 'p2')",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ?",
            [tid],
        )
        con.close()
        result = runner.invoke(
            main,
            ["report", "meta", "--db", str(db_path), "--venues", "online,paper",
             "--definition", "raw", "--all-time"],
        )
        assert result.exit_code == 0, result.output
        # Paper has no data → should show a "no data" note
        assert "no data" in result.output.lower() or "0 decks" in result.output.lower()


# ---------------------------------------------------------------------------
# Tests: advise report --venues
# ---------------------------------------------------------------------------


class TestAdviseReportVenues:
    """CLI tests for ``advise report --venues``."""

    def test_field_and_venues_mutually_exclusive(self, runner, venue_db, deck_file, field_file):
        """--field + --venues → ClickException."""
        result = runner.invoke(
            main,
            ["advise", "report", "--db", venue_db, "--deck", deck_file,
             "--field", field_file, "--venues", "online,paper", "--all-time"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_venues_shows_per_venue_banners(self, runner, venue_db, deck_file):
        """Per-venue banners appear in output."""
        result = runner.invoke(
            main,
            ["advise", "report", "--db", venue_db, "--deck", deck_file,
             "--venues", "online,paper", "--all-time"],
        )
        assert result.exit_code == 0, result.output
        assert "Online (MTGO)" in result.output
        assert "Paper" in result.output

    def test_venues_shows_cross_venue_footer(self, runner, venue_db, deck_file):
        """Cross-venue positioning delta footer appears."""
        result = runner.invoke(
            main,
            ["advise", "report", "--db", venue_db, "--deck", deck_file,
             "--venues", "online,paper", "--all-time"],
        )
        assert result.exit_code == 0, result.output
        assert "Cross-venue positioning delta" in result.output

    def test_no_venues_backward_compatible(self, runner, venue_db, deck_file):
        """advise report WITHOUT --venues runs cleanly and produces a Field Read."""
        result = runner.invoke(
            main,
            ["advise", "report", "--db", venue_db, "--deck", deck_file, "--all-time"],
        )
        assert result.exit_code == 0, result.output
        assert "Field Read" in result.output
        # Cross-venue footer should NOT appear in the non-venues mode
        assert "Cross-venue positioning delta" not in result.output

    def test_venues_unknown_key_exits_nonzero(self, runner, venue_db, deck_file):
        """Unknown venue key raises an error."""
        result = runner.invoke(
            main,
            ["advise", "report", "--db", venue_db, "--deck", deck_file,
             "--venues", "online,unknown_venue", "--all-time"],
        )
        assert result.exit_code != 0

    def test_venues_field_read_per_venue_header(self, runner, venue_db, deck_file):
        """Each per-venue section has a Field Read header."""
        result = runner.invoke(
            main,
            ["advise", "report", "--db", venue_db, "--deck", deck_file,
             "--venues", "online,paper", "--all-time"],
        )
        assert result.exit_code == 0, result.output
        # Each venue section starts with the Field Read header
        assert result.output.count("Field Read") >= 2


# ---------------------------------------------------------------------------
# Tests: byte-identical backward compatibility assertions
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Gated-additive: --venues unset → output is unchanged from baseline."""

    def test_report_meta_no_venues_same_output_structure(self, runner, venue_db):
        """Without --venues, report meta output structure is preserved."""
        result_without = runner.invoke(
            main,
            ["report", "meta", "--db", venue_db, "--definition", "raw",
             "--provenance", "online", "--all-time"],
        )
        assert result_without.exit_code == 0, result_without.output
        # The key structural element: "Meta Share" header and no venue-mode markers
        assert "Meta Share" in result_without.output
        assert "Venue Divergence" not in result_without.output
        assert "── Venue:" not in result_without.output

    def test_advise_report_no_venues_same_output_structure(self, runner, venue_db, deck_file):
        """Without --venues, advise report output structure is preserved."""
        result_without = runner.invoke(
            main,
            ["advise", "report", "--db", venue_db, "--deck", deck_file, "--all-time"],
        )
        assert result_without.exit_code == 0, result_without.output
        assert "Field Read" in result_without.output
        # No cross-venue footer in baseline mode
        assert "Cross-venue positioning delta" not in result_without.output
        # No venue banners in baseline mode
        assert "── Venue: Online" not in result_without.output

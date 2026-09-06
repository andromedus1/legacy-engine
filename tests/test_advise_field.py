"""Tests for ``advise field`` — standalone field-read with no deck required.

Spec: feature-standalone-field-read.
Verifies:
  - global field (no args) prints composition + vulnerability/hate-equity profile
  - ``--provenance paper`` filters field to paper-only archetypes + echoes provenance
  - ``--field <file>`` uses custom field, field_source=custom
  - No deck argument is accepted or required
  - Output matches the field portion of ``advise report`` for the same field
  - Gated-additive: ``advise report`` still works with a deck; its output is unchanged

House style: minimal labeled corpus via parse_cache_item + SQL UPDATE;
CliRunner with ``--db`` pointing at a file-backed DB copy.
"""
from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.advisory.field import build_global_field
from legacy_engine.advisory.whattoplay import field_vulnerability_tags, hate_equity
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Shared test data  (mirrors test_advise_provenance_flag pattern)
# ---------------------------------------------------------------------------

_ONLINE_TOURNAMENT = {
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
            "Sideboard": [{"Count": 2, "CardName": "Force of Will"}],
        },
        {
            "Player": "bob",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
    "Standings": [
        {"Rank": 1, "Player": "alice", "Points": 9},
        {"Rank": 2, "Player": "bob", "Points": 6},
    ],
}

_PAPER_TOURNAMENT = {
    "Tournament": {
        "Name": "SCG Columbus Legacy",
        "Date": "2026-05-25",
        "Uri": "https://melee.gg/Tournament/View/99999",
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
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [{"Player1": "carol", "Player2": "dave", "Result": "2-1"}],
    "Standings": [
        {"Rank": 1, "Player": "carol", "Points": 9},
        {"Rank": 2, "Player": "dave", "Points": 6},
    ],
}

_BRAINSTORM_CARD = Card(
    name="Brainstorm",
    type_line="Instant",
    oracle_text="Draw three cards, then put two cards on top.",
    cmc=1.0,
    colors=["U"],
    produced_mana=[],
    is_land=False,
)
_FORCE_CARD = Card(
    name="Force of Will",
    type_line="Instant",
    oracle_text="Counter target spell.",
    cmc=5.0,
    colors=["U"],
    produced_mana=[],
    is_land=False,
)
_ISLAND = Card(
    name="Island",
    type_line="Basic Land — Island",
    oracle_text="",
    cmc=0.0,
    colors=[],
    produced_mana=["U"],
    is_land=True,
)
_DARK_RITUAL_CARD = Card(
    name="Dark Ritual",
    type_line="Instant",
    oracle_text="Add {B}{B}{B}.",
    cmc=1.0,
    colors=["B"],
    produced_mana=["B"],
    is_land=False,
)

_TEST_CARDS = [_BRAINSTORM_CARD, _FORCE_CARD, _ISLAND, _DARK_RITUAL_CARD]

_BRAINSTORM_DECKLIST = "4 Brainstorm\n4 Force of Will\n12 Island\nSideboard\n2 Force of Will"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


def _build_mixed_db(tmp_path) -> str:
    """DB with both online (Control) and paper (Combo) archetypes."""
    db_path = str(tmp_path / "mixed.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    store.load_cards(con, _TEST_CARDS)

    tid_online = store.load_tournament(con, parse_cache_item(_ONLINE_TOURNAMENT, "MTGO"))
    con.execute("UPDATE decks SET archetype = 'Control' WHERE tournament_id = ?", [tid_online])

    tid_paper = store.load_tournament(con, parse_cache_item(_PAPER_TOURNAMENT, "mtgmelee"))
    con.execute("UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ?", [tid_paper])

    con.close()
    return db_path


def _build_online_only_db(tmp_path) -> str:
    """DB with only online (Control) decks."""
    db_path = str(tmp_path / "online.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    store.load_cards(con, _TEST_CARDS)

    tid = store.load_tournament(con, parse_cache_item(_ONLINE_TOURNAMENT, "MTGO"))
    con.execute("UPDATE decks SET archetype = 'Control' WHERE tournament_id = ?", [tid])

    con.close()
    return db_path


def _write_field(tmp_path, content: str) -> str:
    p = tmp_path / "field.txt"
    p.write_text(content)
    return str(p)


def _write_deck(tmp_path, content: str) -> str:
    p = tmp_path / "deck.txt"
    p.write_text(content)
    return str(p)


# ---------------------------------------------------------------------------
# Unit 1: Help string — advise field exists and shows correct options
# ---------------------------------------------------------------------------


class TestAdviseFieldHelp:
    def test_help_exits_zero(self, runner):
        result = runner.invoke(main, ["advise", "field", "--help"])
        assert result.exit_code == 0, result.output

    def test_help_shows_provenance(self, runner):
        result = runner.invoke(main, ["advise", "field", "--help"])
        assert "--provenance" in result.output

    def test_help_shows_field_option(self, runner):
        result = runner.invoke(main, ["advise", "field", "--help"])
        assert "--field" in result.output

    def test_positioning_help_documents_currency_count_completeness(self, runner):
        result = runner.invoke(main, ["advise", "positioning", "--help"])
        assert result.exit_code == 0
        assert "current_regime_n requires complete counts" in result.output
        assert "inactive means zero current presence" in " ".join(result.output.split())

    def test_help_shows_window_opts(self, runner):
        result = runner.invoke(main, ["advise", "field", "--help"])
        assert "--since" in result.output
        assert "--until" in result.output
        assert "--regime" in result.output
        assert "--all-time" in result.output

    def test_no_deck_option_in_help(self, runner):
        """advise field must NOT expose a --deck option."""
        result = runner.invoke(main, ["advise", "field", "--help"])
        assert "--deck" not in result.output


# ---------------------------------------------------------------------------
# Unit 2: Global field — no flags
# ---------------------------------------------------------------------------


class TestAdviseFieldGlobal:
    def test_global_field_exits_zero(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(main, ["advise", "field", "--db", db_path])
        assert result.exit_code == 0, result.output

    def test_global_field_shows_composition_header(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(main, ["advise", "field", "--db", db_path])
        assert result.exit_code == 0
        assert "Field composition" in result.output

    def test_global_field_shows_both_archetypes(self, runner, tmp_path):
        """Global field shows both Control (online) and Combo (paper)."""
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(main, ["advise", "field", "--db", db_path])
        assert result.exit_code == 0
        assert "Control" in result.output
        assert "Combo" in result.output

    def test_global_field_shows_field_read_header(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(main, ["advise", "field", "--db", db_path])
        assert result.exit_code == 0
        assert "Field Read" in result.output

    def test_global_field_shows_vulnerability_section(self, runner, tmp_path):
        """Output must include the vulnerability/hate-equity section."""
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(main, ["advise", "field", "--db", db_path])
        assert result.exit_code == 0
        # Either shows the profile or the "no tagged archetypes" message
        assert (
            "Field vulnerability profile" in result.output
            or "hate-equity" in result.output
        )

    def test_global_field_shows_field_source_global(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(main, ["advise", "field", "--db", db_path])
        assert result.exit_code == 0
        assert "global" in result.output

    def test_global_field_no_provenance_echo(self, runner, tmp_path):
        """Without --provenance, no provenance echo line (gated-additive)."""
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(main, ["advise", "field", "--db", db_path])
        assert result.exit_code == 0
        assert "// provenance:" not in result.output


# ---------------------------------------------------------------------------
# Unit 3: --provenance paper
# ---------------------------------------------------------------------------


class TestAdviseFieldProvenance:
    def test_paper_provenance_accepted(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(
            main, ["advise", "field", "--provenance", "paper", "--db", db_path]
        )
        assert result.exit_code == 0, result.output

    def test_paper_provenance_echoed(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(
            main, ["advise", "field", "--provenance", "paper", "--db", db_path]
        )
        assert "// provenance: paper" in result.output

    def test_paper_provenance_filters_to_paper_only(self, runner, tmp_path):
        """Paper field shows only Combo (paper archetype), not Control (online)."""
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(
            main, ["advise", "field", "--provenance", "paper", "--db", db_path]
        )
        assert result.exit_code == 0
        assert "Combo" in result.output
        assert "Control" not in result.output

    def test_online_provenance_filters_to_online_only(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(
            main, ["advise", "field", "--provenance", "online", "--db", db_path]
        )
        assert result.exit_code == 0
        assert "Control" in result.output
        assert "Combo" not in result.output

    def test_invalid_provenance_rejected(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        result = runner.invoke(
            main, ["advise", "field", "--provenance", "both", "--db", db_path]
        )
        assert result.exit_code != 0

    def test_paper_provenance_produces_different_output_than_global(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)

        result_global = runner.invoke(main, ["advise", "field", "--db", db_path])
        result_paper = runner.invoke(
            main, ["advise", "field", "--provenance", "paper", "--db", db_path]
        )
        assert result_global.exit_code == 0
        assert result_paper.exit_code == 0
        # Paper-only field has a different composition than the combined field
        assert result_global.output != result_paper.output


# ---------------------------------------------------------------------------
# Unit 4: --field <custom file>
# ---------------------------------------------------------------------------


class TestAdviseFieldCustomFile:
    def test_custom_field_exits_zero(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        field_path = _write_field(tmp_path, "0.6 Control\n0.4 Combo")
        result = runner.invoke(
            main, ["advise", "field", "--field", field_path, "--db", db_path]
        )
        assert result.exit_code == 0, result.output

    def test_custom_field_shows_field_source_custom(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        field_path = _write_field(tmp_path, "0.6 Control\n0.4 Combo")
        result = runner.invoke(
            main, ["advise", "field", "--field", field_path, "--db", db_path]
        )
        assert result.exit_code == 0
        assert "custom" in result.output

    def test_low_regime_currency_emits_measurement_and_warning(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        field_path = _write_field(
            tmp_path,
            "# current_regime_n: 2\n0.6 Control 6\n0.4 Combo 4",
        )
        result = runner.invoke(
            main, ["advise", "field", "--field", field_path, "--db", db_path]
        )
        assert result.exit_code == 0, result.output
        assert "// field regime currency: 20% current" in result.output
        assert "// [warn] field is 20% current-regime" in result.output

    def test_majority_current_currency_has_no_staleness_warning(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        field_path = _write_field(
            tmp_path,
            "# current_regime_n: 8\n0.6 Control 6\n0.4 Combo 4",
        )
        result = runner.invoke(
            main, ["advise", "field", "--field", field_path, "--db", db_path]
        )
        assert result.exit_code == 0, result.output
        assert "// field regime currency: 80% current" in result.output
        assert "// [warn] field is" not in result.output

    def test_undated_custom_field_warns_currency_unavailable(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        field_path = _write_field(tmp_path, "0.6 Control\n0.4 Combo")
        result = runner.invoke(
            main, ["advise", "field", "--field", field_path, "--db", db_path]
        )
        assert result.exit_code == 0, result.output
        assert (
            "// [warn] regime currency unavailable: unavailable for undated aggregate"
            in result.output
        )

    def test_custom_field_shows_custom_archetypes(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        field_path = _write_field(tmp_path, "0.7 Tempo\n0.3 Elves")
        result = runner.invoke(
            main, ["advise", "field", "--field", field_path, "--db", db_path]
        )
        assert result.exit_code == 0
        assert "Tempo" in result.output
        assert "Elves" in result.output

    def test_custom_field_with_provenance_succeeds(self, runner, tmp_path):
        """--field + --provenance: custom field is used, provenance is accepted."""
        db_path = _build_mixed_db(tmp_path)
        field_path = _write_field(tmp_path, "0.6 Control\n0.4 Combo")
        result = runner.invoke(
            main,
            [
                "advise", "field",
                "--field", field_path,
                "--provenance", "paper",
                "--db", db_path,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "custom" in result.output
        assert "// provenance: paper" in result.output

    def test_custom_field_shows_vulnerability_section(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        field_path = _write_field(tmp_path, "0.6 Control\n0.4 Combo")
        result = runner.invoke(
            main, ["advise", "field", "--field", field_path, "--db", db_path]
        )
        assert result.exit_code == 0
        assert "Field vulnerability profile" in result.output or "hate-equity" in result.output


# ---------------------------------------------------------------------------
# Unit 5: Field matches the field portion of advise report for the same field
# ---------------------------------------------------------------------------


class TestAdviseFieldMatchesReportFieldSection:
    """advise field output should contain the same archetype shares as the field
    section in advise report for the same corpus window.

    We compare at the library level (build_global_field) rather than diffing
    the full CLI output, since advise report adds many deck-specific sections.
    """

    def test_same_archetypes_as_global_field(self, tmp_path):
        """advise field (global) lists the same archetypes as build_global_field."""
        db_path = _build_mixed_db(tmp_path)
        con = store.connect(db_path)
        try:
            field = build_global_field(con, provenance=None)
        finally:
            con.close()

        runner = CliRunner()
        result = runner.invoke(main, ["advise", "field", "--db", db_path])
        assert result.exit_code == 0, result.output

        for archetype in field.shares:
            assert archetype in result.output, (
                f"Expected archetype {archetype!r} in advise field output"
            )

    def test_paper_field_matches_build_global_field_paper(self, tmp_path):
        """advise field --provenance paper lists same archetypes as build_global_field(paper)."""
        db_path = _build_mixed_db(tmp_path)
        con = store.connect(db_path)
        try:
            field = build_global_field(con, provenance="paper")
        finally:
            con.close()

        runner = CliRunner()
        result = runner.invoke(
            main, ["advise", "field", "--provenance", "paper", "--db", db_path]
        )
        assert result.exit_code == 0, result.output

        for archetype in field.shares:
            assert archetype in result.output

    def test_hate_equity_matches_library(self, tmp_path):
        """The vulnerability profile echoed by advise field matches what the library computes."""
        db_path = _build_mixed_db(tmp_path)
        con = store.connect(db_path)
        try:
            field = build_global_field(con, provenance=None)
            archetype_tags = field_vulnerability_tags(con, field)
            lib_profile = hate_equity(field, archetype_tags)
        finally:
            con.close()

        runner = CliRunner()
        result = runner.invoke(main, ["advise", "field", "--db", db_path])
        assert result.exit_code == 0, result.output

        # Every tag in the library profile should appear in the CLI output
        for tag in lib_profile:
            assert tag in result.output, (
                f"Expected vulnerability tag {tag!r} in advise field output"
            )


# ---------------------------------------------------------------------------
# Unit 6: Gated-additive — advise report still works; no regressions
# ---------------------------------------------------------------------------


class TestAdviseReportUnchanged:
    """Confirm advise report still requires a deck and produces its normal output."""

    def test_advise_report_still_works_with_deck(self, runner, tmp_path):
        db_path = _build_mixed_db(tmp_path)
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        result = runner.invoke(main, [
            "advise", "report",
            "--deck", deck_path,
            "--archetype", "Control",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "Field Read" in result.output

    def test_advise_field_not_affected_by_existing_advise_leaves(self, runner):
        """Smoke-test: all existing advise sub-commands still appear in help."""
        result = runner.invoke(main, ["advise", "--help"])
        assert result.exit_code == 0
        for leaf in ("field", "positioning", "sideboard", "whattoplay", "report"):
            assert leaf in result.output, f"Expected {leaf!r} in advise --help"

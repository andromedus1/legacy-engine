"""CLI skeleton — groups are discoverable; leaf stubs fail loudly with 'not implemented'."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_top_level_help_lists_groups(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    for group in ("seed", "refresh", "label", "report", "advise", "generate", "export"):
        assert group in result.output


@pytest.mark.parametrize(
    "group,subcommands",
    [
        ("seed", ("cards", "cache", "rules", "banlist")),
        ("report", ("meta", "matchups", "tiers")),
        ("advise", ("positioning", "sideboard", "whattoplay", "report")),
        ("generate", ("consensus", "tune")),
        ("export", ("deck",)),
    ],
)
def test_group_help_lists_subcommands(runner, group, subcommands):
    result = runner.invoke(main, [group, "--help"])
    assert result.exit_code == 0
    for sub in subcommands:
        assert sub in result.output


def test_generate_consensus_requires_archetype(runner):
    """generate consensus exits non-zero when --archetype is missing."""
    result = runner.invoke(main, ["generate", "consensus"])
    assert result.exit_code != 0


def test_export_deck_requires_deck(runner):
    """export deck exits non-zero when --deck is missing."""
    result = runner.invoke(main, ["export", "deck"])
    assert result.exit_code != 0


@pytest.mark.parametrize(
    "args,label",
    [
        # seed cards/cache/rules/banlist, label, report matchups, report meta, and report tiers are implemented.
        # advise positioning/sideboard/whattoplay/report are also implemented (no longer stubs).
        (["refresh"], "refresh"),
    ],
)
def test_leaf_stubs_not_implemented(runner, args, label):
    result = runner.invoke(main, args)
    assert result.exit_code != 0
    assert f"not implemented: {label}" in result.output


def test_advise_subcommands_require_deck(runner):
    """Implemented advise commands require --deck; missing → non-zero exit + usage error."""
    for sub in ("positioning", "sideboard", "whattoplay", "report"):
        result = runner.invoke(main, ["advise", sub])
        assert result.exit_code != 0, f"advise {sub} should fail without --deck"


# ---------------------------------------------------------------------------
# report cards — Unit 5 of epic-deck-generation-per-card-value
# ---------------------------------------------------------------------------


class TestReportCards:
    """CLI tests for `report cards`."""

    @pytest.fixture
    def db_with_corpus(self, tmp_path, make_rounds_corpus):
        """Write a rounds corpus to a real DuckDB file for CLI invocation."""
        db_path = tmp_path / "test.duckdb"
        # Build in-memory, then copy tables to the file-backed DB.
        con_mem, _ = make_rounds_corpus(n_repeats=5)

        from legacy_engine.ingestion import store as _store
        con_file = _store.connect(str(db_path))
        _store.init_schema(con_file)

        # Copy all rows from the in-memory DB to the file DB.
        for table in ("tournaments", "decks", "deck_cards", "rounds"):
            rows = con_mem.execute(f"SELECT * FROM {table}").fetchall()
            if rows:
                placeholders = ", ".join(["?"] * len(rows[0]))
                con_file.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)

        con_mem.close()
        con_file.close()
        return str(db_path)

    def test_report_cards_help(self, runner):
        result = runner.invoke(main, ["report", "cards", "--help"])
        assert result.exit_code == 0
        assert "--archetype" in result.output
        assert "--vs" in result.output
        assert "--board" in result.output
        assert "--min-tier" in result.output

    def test_report_cards_listed_in_report_group(self, runner):
        result = runner.invoke(main, ["report", "--help"])
        assert result.exit_code == 0
        assert "cards" in result.output

    def test_report_cards_happy_path_marginal(self, runner, db_with_corpus):
        """report cards on a real corpus prints a table with card names."""
        result = runner.invoke(main, ["report", "cards", "--db", db_with_corpus, "--board", "main"])
        assert result.exit_code == 0, result.output
        assert "Brainstorm" in result.output or "Dark Ritual" in result.output

    def test_report_cards_vs_opponent(self, runner, db_with_corpus):
        """report cards --vs Combo shows Brainstorm (main) vs Combo."""
        result = runner.invoke(main, ["report", "cards", "--db", db_with_corpus, "--vs", "Combo", "--board", "main"])
        assert result.exit_code == 0, result.output
        assert "Brainstorm" in result.output

    def test_report_cards_min_tier_established_suppresses_speculative(self, runner, db_with_corpus):
        """--min-tier established with n_repeats=5 (n=10) suppresses all rows + shows note."""
        result = runner.invoke(
            main,
            ["report", "cards", "--db", db_with_corpus, "--board", "main", "--min-tier", "established"],
        )
        assert result.exit_code == 0, result.output
        # n=10 for all cells (n_repeats=5) → speculative → suppressed
        assert "suppressed" in result.output.lower() or "below" in result.output.lower()

    def test_report_cards_min_tier_speculative_shows_all(self, runner, db_with_corpus):
        """--min-tier speculative (default) shows all rows including speculative."""
        result = runner.invoke(
            main,
            ["report", "cards", "--db", db_with_corpus, "--board", "main", "--min-tier", "speculative"],
        )
        assert result.exit_code == 0, result.output
        # No suppression note when everything is shown
        assert "Brainstorm" in result.output

    def test_report_cards_presence_correlational_note(self, runner, db_with_corpus):
        """Report header always prints the NOT causal disclaimer."""
        result = runner.invoke(main, ["report", "cards", "--db", db_with_corpus])
        assert result.exit_code == 0, result.output
        assert "NOT causal" in result.output or "correlational" in result.output

    def test_report_cards_empty_db_no_crash(self, runner, tmp_path):
        """Empty DB with no matches prints cleanly without crashing."""
        from legacy_engine.ingestion import store as _store
        db_path = str(tmp_path / "empty.duckdb")
        con = _store.connect(db_path)
        _store.init_schema(con)
        con.close()
        result = runner.invoke(main, ["report", "cards", "--db", db_path])
        assert result.exit_code == 0, result.output

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
    for group in ("seed", "refresh", "label", "report", "advise", "generate", "export", "viz"):
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
        result = runner.invoke(main, ["report", "cards", "--db", db_with_corpus, "--board", "main", "--since", "2025-01-01"])
        assert result.exit_code == 0, result.output
        assert "Brainstorm" in result.output or "Dark Ritual" in result.output

    def test_report_cards_vs_opponent(self, runner, db_with_corpus):
        """report cards --vs Combo shows Brainstorm (main) vs Combo."""
        result = runner.invoke(main, ["report", "cards", "--db", db_with_corpus, "--vs", "Combo", "--board", "main", "--since", "2025-01-01"])
        assert result.exit_code == 0, result.output
        assert "Brainstorm" in result.output

    def test_report_cards_min_tier_established_suppresses_speculative(self, runner, db_with_corpus):
        """--min-tier established with n_repeats=5 (n=10) suppresses all rows + shows note."""
        result = runner.invoke(
            main,
            ["report", "cards", "--db", db_with_corpus, "--board", "main", "--min-tier", "established", "--since", "2025-01-01"],
        )
        assert result.exit_code == 0, result.output
        # n=10 for all cells (n_repeats=5) → speculative → suppressed
        assert "suppressed" in result.output.lower() or "below" in result.output.lower()

    def test_report_cards_min_tier_speculative_shows_all(self, runner, db_with_corpus):
        """--min-tier speculative (default) shows all rows including speculative."""
        result = runner.invoke(
            main,
            ["report", "cards", "--db", db_with_corpus, "--board", "main", "--min-tier", "speculative", "--since", "2025-01-01"],
        )
        assert result.exit_code == 0, result.output
        # No suppression note when everything is shown
        assert "Brainstorm" in result.output

    def test_report_cards_presence_correlational_note(self, runner, db_with_corpus):
        """Report header always prints the NOT causal disclaimer."""
        result = runner.invoke(main, ["report", "cards", "--db", db_with_corpus, "--since", "2025-01-01"])
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


# ---------------------------------------------------------------------------
# viz CLI group tests
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path_rounds(tmp_path, make_rounds_corpus):
    """File-backed DuckDB with n_repeats=15 (evolving tier, n=30) for viz CLI tests.

    n_repeats=15 yields valid dates (2026-01-01..15) and n=30 matchup counts (evolving tier).
    We avoid n_repeats>28 because the fixture date formula generates invalid dates like 2026-01-32.
    """
    db_path = tmp_path / "viz_test.duckdb"
    con_mem, _ = make_rounds_corpus(n_repeats=15)

    from legacy_engine.ingestion import store as _store
    con_file = _store.connect(str(db_path))
    _store.init_schema(con_file)

    for table in ("tournaments", "decks", "deck_cards", "rounds"):
        rows = con_mem.execute(f"SELECT * FROM {table}").fetchall()
        if rows:
            placeholders = ", ".join(["?"] * len(rows[0]))
            con_file.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)

    con_mem.close()
    con_file.close()
    return str(db_path)


class TestVizGroup:
    """CLI tests for the `viz` command group."""

    def test_viz_help_lists_subcommands(self, runner):
        result = runner.invoke(main, ["viz", "--help"])
        assert result.exit_code == 0
        for sub in ("deck", "meta", "matchups", "trends", "tiers"):
            assert sub in result.output

    def test_viz_deck_requires_archetype(self, runner):
        result = runner.invoke(main, ["viz", "deck"])
        assert result.exit_code != 0

    def test_viz_deck_requires_out(self, runner):
        result = runner.invoke(main, ["viz", "deck", "Control"])
        assert result.exit_code != 0

    def test_viz_deck_html_writes_file(self, runner, tmp_path, db_path_rounds):
        out_path = str(tmp_path / "deck.html")
        result = runner.invoke(main, [
            "viz", "deck", "Control",
            "--out", out_path,
            "--db", db_path_rounds,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        import os
        assert os.path.exists(out_path)
        html = open(out_path).read()
        assert "<!DOCTYPE html>" in html
        assert "vegaEmbed(" in html
        assert len(html) > 1000

    def test_viz_deck_html_non_trivial_size(self, runner, tmp_path, db_path_rounds):
        """Dashboard HTML should be substantially sized — at least 5 KB."""
        out_path = str(tmp_path / "deck.html")
        runner.invoke(main, [
            "viz", "deck", "Control",
            "--out", out_path,
            "--db", db_path_rounds,
            "--seed", "42",
        ])
        import os
        size = os.path.getsize(out_path)
        assert size > 5_000, f"HTML file too small: {size} bytes"

    def test_viz_deck_dir_writes_pngs(self, runner, tmp_path, db_path_rounds):
        """--out <dir> writes one PNG per chart tile."""
        import os
        out_dir = str(tmp_path / "tiles")
        result = runner.invoke(main, [
            "viz", "deck", "Control",
            "--out", out_dir,
            "--db", db_path_rounds,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        pngs = [f for f in os.listdir(out_dir) if f.endswith(".png")]
        # 4 chart tiles (matchup, positioning, meta, trends)
        assert len(pngs) == 4, f"expected 4 PNGs, got {pngs}"
        for png_file in pngs:
            full = os.path.join(out_dir, png_file)
            with open(full, "rb") as f:
                header = f.read(4)
            assert header == b"\x89PNG", f"{png_file} is not a valid PNG"

    def test_viz_meta_writes_html(self, runner, tmp_path, db_path_rounds):
        out_path = str(tmp_path / "meta.html")
        result = runner.invoke(main, [
            "viz", "meta",
            "--out", out_path,
            "--db", db_path_rounds,
        ])
        assert result.exit_code == 0, result.output
        import os
        assert os.path.exists(out_path)
        content = open(out_path).read()
        assert "<!DOCTYPE html>" in content or "vega" in content.lower()

    def test_viz_meta_writes_png(self, runner, tmp_path, db_path_rounds):
        out_path = str(tmp_path / "meta.png")
        result = runner.invoke(main, [
            "viz", "meta",
            "--out", out_path,
            "--db", db_path_rounds,
        ])
        assert result.exit_code == 0, result.output
        import os
        with open(out_path, "rb") as f:
            header = f.read(4)
        assert header == b"\x89PNG"

    def test_viz_trends_writes_html(self, runner, tmp_path, db_path_rounds):
        out_path = str(tmp_path / "trends.html")
        result = runner.invoke(main, [
            "viz", "trends",
            "--out", out_path,
            "--db", db_path_rounds,
        ])
        assert result.exit_code == 0, result.output
        import os
        assert os.path.exists(out_path)

    def test_viz_tiers_writes_png(self, runner, tmp_path, db_path_rounds):
        out_path = str(tmp_path / "tiers.png")
        result = runner.invoke(main, [
            "viz", "tiers",
            "--out", out_path,
            "--db", db_path_rounds,
        ])
        assert result.exit_code == 0, result.output
        import os
        with open(out_path, "rb") as f:
            header = f.read(4)
        assert header == b"\x89PNG"

    def test_viz_matchups_writes_html(self, runner, tmp_path, db_path_rounds):
        out_path = str(tmp_path / "matchups.html")
        result = runner.invoke(main, [
            "viz", "matchups",
            "--out", out_path,
            "--db", db_path_rounds,
        ])
        assert result.exit_code == 0, result.output
        import os
        assert os.path.exists(out_path)

    def test_viz_deck_out_ext_routing_html_vs_dir(self, runner, tmp_path, db_path_rounds):
        """Extension-based routing: .html → HTML file; no extension → dir mode."""
        import os

        # .html → dashboard HTML
        html_out = str(tmp_path / "dash.html")
        r = runner.invoke(main, [
            "viz", "deck", "Control",
            "--out", html_out,
            "--db", db_path_rounds,
            "--seed", "0",
        ])
        assert r.exit_code == 0, r.output
        assert os.path.isfile(html_out)
        assert "<!DOCTYPE html>" in open(html_out).read()

        # no-extension dir → tiles
        tile_dir = str(tmp_path / "tiledir")
        r2 = runner.invoke(main, [
            "viz", "deck", "Control",
            "--out", tile_dir,
            "--db", db_path_rounds,
            "--seed", "0",
        ])
        assert r2.exit_code == 0, r2.output
        pngs = [f for f in os.listdir(tile_dir) if f.endswith(".png")]
        assert len(pngs) >= 1

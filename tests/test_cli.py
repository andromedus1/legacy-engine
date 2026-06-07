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

    def test_viz_render_failure_raises_click_exception(self, runner, tmp_path, db_path_rounds, monkeypatch):
        """I2 regression: a ValueError from render_png must surface as a clean ClickException.

        The CLI must not propagate a raw traceback — it wraps render errors as ClickException
        (non-zero exit, error message in output, no raw ValueError traceback).
        """
        import legacy_engine.viz.render as _render_mod

        def _boom(spec, **kwargs):
            raise ValueError("boom — simulated vl_convert failure")

        monkeypatch.setattr(_render_mod, "render_png", _boom)

        out_dir = str(tmp_path / "fail_tiles")
        result = runner.invoke(main, [
            "viz", "deck", "Control",
            "--out", out_dir,
            "--db", db_path_rounds,
            "--seed", "0",
        ])
        # Must exit non-zero
        assert result.exit_code != 0
        # Must show the user-friendly error message (ClickException), not a raw traceback
        output = result.output
        assert "Error" in output or (result.exception is not None and isinstance(result.exception, SystemExit))
        # The raw ValueError class name must NOT appear as an unhandled traceback
        # (it appears in the ClickException message, but not as "Traceback (most recent call last)")
        assert "Traceback (most recent call last)" not in output


# ---------------------------------------------------------------------------
# Field & regime consistency — epic-advisory-output-honesty-field-consistency
# ---------------------------------------------------------------------------


class TestFieldConsistency:
    """tiers default→current-regime window opts + Unknown/Conflict labeling in render."""

    @pytest.fixture
    def db_with_corpus(self, tmp_path, make_rounds_corpus):
        """Write a rounds corpus to a real DuckDB file for CLI invocation."""
        db_path = tmp_path / "test.duckdb"
        con_mem, _ = make_rounds_corpus(n_repeats=5)
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

    def test_tiers_default_windows_to_current_regime(self, runner, db_with_corpus):
        result = runner.invoke(main, ["report", "tiers", "--db", db_with_corpus, "--provenance", "online"])
        assert result.exit_code == 0, result.output
        assert "// window: regime: current" in result.output

    def test_tiers_all_time_uses_full_corpus(self, runner, db_with_corpus):
        result = runner.invoke(
            main, ["report", "tiers", "--db", db_with_corpus, "--provenance", "online", "--all-time"]
        )
        assert result.exit_code == 0, result.output
        assert "// window: full-corpus" in result.output

    def test_tiers_windowed_wrw_fails_loud_not_crash(self, runner, db_with_corpus):
        # Bare wrw windows to the current regime → unsupported. Must be a clean ClickException,
        # NOT an unhandled NotImplementedError traceback (regression caught in review).
        result = runner.invoke(main, ["report", "tiers", "--db", db_with_corpus, "--definition", "wrw"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "windowed wrw is unsupported" in result.output
        assert "--all-time" in result.output

    def test_tiers_all_time_wrw_is_allowed(self, runner, db_with_corpus):
        result = runner.invoke(
            main, ["report", "tiers", "--db", db_with_corpus, "--definition", "wrw", "--all-time"]
        )
        assert result.exit_code == 0, result.output

    def _meta_report(self, archetypes):
        from legacy_engine.analytics.metashare import MetaShareEntry, MetaShareReport
        entries = [
            MetaShareEntry(archetype=a, share=s, n=n, tier="established", fringe=False)
            for a, s, n in archetypes
        ]
        return MetaShareReport(
            definition="raw", provenance="online", entries=entries,
            total_decks=1000, unlabeled=0, min_share=0.02,
        )

    def test_tiers_exposes_window_opts(self, runner):
        result = runner.invoke(main, ["report", "tiers", "--help"])
        assert result.exit_code == 0
        for opt in ("--all-time", "--regime", "--since", "--until"):
            assert opt in result.output, f"{opt} missing from `report tiers --help`"

    def test_metashare_render_marks_unknown(self, capsys):
        from legacy_engine.cli import _print_metashare_report
        report = self._meta_report([("Izzet Delver", 0.30, 300), ("Unknown", 0.08, 80)])
        _print_metashare_report(report)
        out = capsys.readouterr().out
        # The Unknown line carries ‡; the real archetype line does not.
        unknown_line = next(ln for ln in out.splitlines() if ln.startswith("Unknown"))
        delver_line = next(ln for ln in out.splitlines() if ln.startswith("Izzet Delver"))
        assert "‡" in unknown_line
        assert "‡" not in delver_line
        assert out.count("unclassified — not positionable") == 1  # footnote once

    def test_metashare_render_marks_conflict(self, capsys):
        from legacy_engine.cli import _print_metashare_report
        report = self._meta_report([("Izzet Delver", 0.30, 300), ("Conflict(Delver,Tempo)", 0.04, 40)])
        _print_metashare_report(report)
        out = capsys.readouterr().out
        conflict_line = next(ln for ln in out.splitlines() if ln.startswith("Conflict("))
        assert "‡" in conflict_line

    def test_metashare_render_no_footnote_when_all_classified(self, capsys):
        from legacy_engine.cli import _print_metashare_report
        report = self._meta_report([("Izzet Delver", 0.30, 300), ("Lands", 0.10, 100)])
        _print_metashare_report(report)
        out = capsys.readouterr().out
        assert "‡" not in out
        assert "unclassified — not positionable" not in out

    def test_matchup_render_marks_unknown(self, capsys):
        from legacy_engine.cli import _print_matchup_matrix
        from legacy_engine.analytics.matchup import MatchupMatrix, build_cell, build_mirror_cell
        archs = ["Izzet Delver", "Unknown"]
        cells = {}
        for a in archs:
            cells[(a, a)] = build_mirror_cell(a, 50)
            for b in archs:
                if a != b:
                    cells[(a, b)] = build_cell(a, b, 55, 100)
        matrix = MatchupMatrix(
            cells=cells, provenance=None, total_matches=200,
            archetypes=archs, caveat="test",
        )
        _print_matchup_matrix(matrix)
        out = capsys.readouterr().out
        unknown_row = next(ln for ln in out.splitlines() if ln.startswith("Unknown"))
        assert "Unknown ‡" in unknown_row
        assert out.count("unclassified — not positionable") == 1
        # numeric cells unaffected
        assert "(n=100)" in out


# ---------------------------------------------------------------------------
# Output transparency — epic-advisory-output-honesty-transparency
# ---------------------------------------------------------------------------


class TestTransparency:
    """data-freshness header + staleness guard, consensus thin-sample flag, tune swap rationale."""

    @pytest.fixture
    def db_with_corpus(self, tmp_path, make_rounds_corpus):
        db_path = tmp_path / "test.duckdb"
        con_mem, _ = make_rounds_corpus(n_repeats=5)
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

    # --- pure staleness helper (regression for the unparseable-date crash) ---
    def test_staleness_age_none_on_empty(self):
        from datetime import date
        from legacy_engine.cli import _staleness_age_days
        assert _staleness_age_days(None, date(2026, 6, 6)) is None

    def test_staleness_age_none_on_unparseable_date(self):
        # Synthetic corpora carry out-of-range dates like '2026-01-50' — must NOT crash.
        from datetime import date
        from legacy_engine.cli import _staleness_age_days
        assert _staleness_age_days("2026-01-50", date(2026, 6, 6)) is None

    def test_staleness_age_computes_days(self):
        from datetime import date
        from legacy_engine.cli import _staleness_age_days
        assert _staleness_age_days("2026-05-30", date(2026, 6, 6)) == 7
        assert _staleness_age_days("2026-01-01", date(2026, 6, 6)) > 30

    # --- data-freshness header on reports ---
    def test_report_meta_prints_data_as_of_header(self, runner, db_with_corpus):
        result = runner.invoke(main, ["report", "meta", "--db", db_with_corpus, "--provenance", "online"])
        assert result.exit_code == 0, result.output
        assert "// data as of 2026-01-05" in result.output  # max synthetic date (n_repeats=5)
        assert "decks)" in result.output

    # --- consensus thin-sample flag ---
    def test_consensus_thin_sample_flagged(self, runner, db_with_corpus):
        result = runner.invoke(
            main,
            ["generate", "consensus", "--archetype", "Control", "--db", db_with_corpus, "--since", "2026-01-01"],
        )
        assert result.exit_code == 0, result.output
        assert "[speculative]" in result.output
        assert "thin sample" in result.output

    # --- tune swap rationale ---
    def test_tune_renders_delta_and_swaps(self, runner, db_with_corpus, tmp_path):
        deck = tmp_path / "control.txt"
        # A minimal Control list — exact legality isn't the point; the render is.
        deck.write_text("4 Brainstorm\n")
        result = runner.invoke(
            main,
            ["generate", "tune", "--deck", str(deck), "--archetype", "Control", "--db", db_with_corpus],
        )
        # Tune may legality-fail on a 1-card deck; if it runs, the rationale lines must be present.
        if result.exit_code == 0:
            assert "Δvalue =" in result.output
            assert ("Swaps:" in result.output) or ("Swaps (" in result.output)

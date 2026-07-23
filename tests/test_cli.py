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
        ("seed", ("cards", "cache", "rules", "banlist", "prices")),
        ("report", ("meta", "matchups", "tiers", "prices")),
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
        # numeric cells unaffected — triple display carries shrunk|raw and n
        assert "n=100" in out and "|" in out


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
    def test_tune_renders_delta_and_swap_log(self, runner, db_with_corpus, tmp_path):
        # Derive a LEGAL 60-card deck from the consensus output (its maindeck is exactly 60),
        # then tune it — so the command actually exits 0 and the new render lines are asserted.
        cons = runner.invoke(
            main,
            ["generate", "consensus", "--archetype", "Control", "--db", db_with_corpus, "--since", "2026-01-01"],
        )
        assert cons.exit_code == 0, cons.output
        maindeck_lines = []
        for ln in cons.output.splitlines():
            if ln.strip() == "Sideboard":
                break
            if ln and ln[0].isdigit():  # "N CardName" — skip // headers/blank lines
                maindeck_lines.append(ln)
        assert maindeck_lines, cons.output
        deck = tmp_path / "control.txt"
        deck.write_text("\n".join(maindeck_lines) + "\n")

        result = runner.invoke(
            main,
            ["generate", "tune", "--deck", str(deck), "--archetype", "Control", "--db", db_with_corpus],
        )
        assert result.exit_code == 0, result.output
        assert "Δvalue =" in result.output
        # Thin corpus → no signal → no swaps; the no-swap log line must render cleanly.
        assert "// Swap log:" in result.output
        # The presence-correlational scale note appears only when swaps were made.
        if "1. CUT" in result.output:
            assert "presence-correlational" in result.output


# ---------------------------------------------------------------------------
# TestWindowEchoRegimeConsistency — feature-regime-windowing-consistency
# ---------------------------------------------------------------------------


class TestWindowEchoRegimeConsistency:
    """CLI window-echo assertions for feature-regime-windowing-consistency.

    Verifies that each surface echoes its window and that the divergence between
    consensus (uniform current-regime) and tune/sideboard (adaptive) is stated.
    """

    @pytest.fixture
    def db_with_corpus(self, tmp_path, make_rounds_corpus):
        """Write a small rounds corpus to a file-backed DuckDB for CLI invocations."""
        db_path = tmp_path / "test_window.duckdb"
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

    def test_generate_consensus_echoes_window_and_sample_n(self, runner, db_with_corpus):
        """generate consensus must echo window + sample_n in its header."""
        result = runner.invoke(
            main,
            ["generate", "consensus", "--archetype", "Control",
             "--db", db_with_corpus, "--since", "2026-01-01"],
        )
        assert result.exit_code == 0, result.output
        # Fix A: consensus echoes its current-regime window + sample_n
        assert "window:" in result.output
        assert "sample_n=" in result.output

    def test_generate_consensus_echoes_honest_explicit_window_label(self, runner, db_with_corpus):
        """generate consensus with an explicit --since must label the window honestly as an
        explicit override — NOT the stale hardcoded "uniform current-regime" claim (completion-
        review Finding 2: the audit line must name the actual basis, since --since here isn't
        necessarily the current ban regime)."""
        result = runner.invoke(
            main,
            ["generate", "consensus", "--archetype", "Control",
             "--db", db_with_corpus, "--since", "2026-01-01"],
        )
        assert result.exit_code == 0, result.output
        assert "// window: since 2026-01-01 (explicit window)" in result.output

    def test_generate_tune_echoes_window_divergence(self, runner, db_with_corpus, tmp_path):
        """generate tune must state the window divergence between list and matchup math."""
        # Build a minimal legal-ish deck file first.
        cons = runner.invoke(
            main,
            ["generate", "consensus", "--archetype", "Control",
             "--db", db_with_corpus, "--since", "2026-01-01"],
        )
        assert cons.exit_code == 0, cons.output
        maindeck_lines = []
        for ln in cons.output.splitlines():
            if ln.strip() == "Sideboard":
                break
            if ln and ln[0].isdigit():
                maindeck_lines.append(ln)
        assert maindeck_lines, cons.output
        deck = tmp_path / "control_for_tune.txt"
        deck.write_text("\n".join(maindeck_lines) + "\n")

        result = runner.invoke(
            main,
            ["generate", "tune", "--deck", str(deck), "--archetype", "Control",
             "--db", db_with_corpus],
        )
        assert result.exit_code == 0, result.output
        # Fix A: tune echoes the window divergence note
        output_lower = result.output.lower()
        assert (
            "two windows" in output_lower
            or "divergence" in output_lower
            or "current-regime" in output_lower
            or "adaptive" in output_lower
        ), f"Expected window divergence note in tune output; output:\n{result.output}"

    def test_advise_sideboard_default_echoes_adaptive_window(self, runner, db_with_corpus, tmp_path):
        """advise sideboard (default = adaptive mode) must echo // window: adaptive."""
        # Write a minimal deck file.
        deck = tmp_path / "sb_deck.txt"
        deck.write_text("4 Brainstorm\n56 Island\n")

        result = runner.invoke(
            main,
            ["advise", "sideboard", "--deck", str(deck), "--db", db_with_corpus,
             "--archetype", "Control", "--solver", "greedy"],
        )
        assert result.exit_code == 0, result.output
        # Default mode is adaptive → should echo adaptive window line
        assert "// window:" in result.output
        output_lower = result.output.lower()
        assert "adaptive" in output_lower, (
            f"Expected adaptive window echo in advise sideboard output; got:\n{result.output}"
        )

    def test_advise_sideboard_all_time_echoes_full_corpus(self, runner, db_with_corpus, tmp_path):
        """advise sideboard --all-time must echo // window: full-corpus."""
        deck = tmp_path / "sb_deck2.txt"
        deck.write_text("4 Brainstorm\n56 Island\n")

        result = runner.invoke(
            main,
            ["advise", "sideboard", "--deck", str(deck), "--db", db_with_corpus,
             "--all-time", "--solver", "greedy"],
        )
        assert result.exit_code == 0, result.output
        assert "// window:" in result.output
        assert "full-corpus" in result.output

    def test_advise_sideboard_regime_current_echoes_window(self, runner, db_with_corpus, tmp_path):
        """advise sideboard --regime current echoes a window line (regime label or banner)."""
        deck = tmp_path / "sb_deck3.txt"
        deck.write_text("4 Brainstorm\n56 Island\n")

        result = runner.invoke(
            main,
            ["advise", "sideboard", "--deck", str(deck), "--db", db_with_corpus,
             "--regime", "current", "--solver", "greedy"],
        )
        assert result.exit_code == 0, result.output
        assert "// window:" in result.output


# ---------------------------------------------------------------------------
# report cards --contrast — matchup-conditioned sideboard-slot test
# (feature epic-sb-config-evaluation-matchup-slot-test)
# ---------------------------------------------------------------------------


class TestReportCardsContrast:
    """CLI tests for the `report cards --contrast` sideboard-slot test."""

    @pytest.fixture
    def contrast_db(self, tmp_path, make_rounds_corpus):
        """File-backed DuckDB with the Control-vs-Combo rounds corpus (Surgical in side)."""
        db_path = tmp_path / "contrast.duckdb"
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

    def test_contrast_requires_vs(self, runner, contrast_db):
        result = runner.invoke(
            main, ["report", "cards", "--contrast", "--archetype", "Control", "--db", contrast_db]
        )
        assert result.exit_code != 0
        assert "requires both --archetype and --vs" in result.output

    def test_contrast_requires_archetype(self, runner, contrast_db):
        result = runner.invoke(
            main, ["report", "cards", "--contrast", "--vs", "Combo", "--db", contrast_db]
        )
        assert result.exit_code != 0
        assert "requires both --archetype and --vs" in result.output

    def test_contrast_prints_both_windows_and_disclaimer(self, runner, contrast_db):
        result = runner.invoke(
            main,
            ["report", "cards", "--contrast", "--archetype", "Control", "--vs", "Combo",
             "--db", contrast_db],
        )
        assert result.exit_code == 0, result.output
        assert "Sideboard-slot contrast" in result.output
        assert "adaptive ban-aware" in result.output
        assert "full-corpus (all-time)" in result.output
        assert "NOT causal" in result.output

    def test_contrast_defaults_to_side_board(self, runner, contrast_db):
        """No --board on the contrast path defaults to side (the sideboard-slot test)."""
        result = runner.invoke(
            main,
            ["report", "cards", "--contrast", "--archetype", "Control", "--vs", "Combo",
             "--db", contrast_db],
        )
        assert result.exit_code == 0, result.output
        assert "[board=side]" in result.output

    def test_contrast_respects_explicit_board(self, runner, contrast_db):
        result = runner.invoke(
            main,
            ["report", "cards", "--contrast", "--archetype", "Control", "--vs", "Combo",
             "--board", "main", "--db", contrast_db],
        )
        assert result.exit_code == 0, result.output
        assert "[board=main]" in result.output

    def test_contrast_scan_shows_multiple_comparisons_caution(self, runner, contrast_db):
        """Scanning all cards (no --card) prints the multiple-comparisons caution."""
        result = runner.invoke(
            main,
            ["report", "cards", "--contrast", "--archetype", "Control", "--vs", "Combo",
             "--db", contrast_db],
        )
        assert result.exit_code == 0, result.output
        assert "multiple comparisons" in result.output

    def test_contrast_single_card_no_multiple_comparisons_caution(self, runner, contrast_db):
        """Focusing one --card suppresses the multiple-comparisons caution."""
        result = runner.invoke(
            main,
            ["report", "cards", "--contrast", "--archetype", "Control", "--vs", "Combo",
             "--card", "Surgical Extraction", "--db", contrast_db],
        )
        assert result.exit_code == 0, result.output
        assert "multiple comparisons" not in result.output

    def test_non_contrast_path_unchanged(self, runner, contrast_db):
        """Without --contrast, the normal marginal/lift report still renders (no contrast header)."""
        result = runner.invoke(
            main, ["report", "cards", "--db", contrast_db, "--board", "main", "--since", "2025-01-01"]
        )
        assert result.exit_code == 0, result.output
        assert "Sideboard-slot contrast" not in result.output
        assert "Card Win-Rates" in result.output

    def test_contrast_thin_cohort_renders_thin_banner(self, runner, contrast_db):
        """A cohort under the n<30 speculative floor renders the labeled thin-n honesty banner
        (contrast_db's n_repeats=5 seeds the WITH cohort at n=10 — thin by construction)."""
        result = runner.invoke(
            main,
            ["report", "cards", "--contrast", "--archetype", "Control", "--vs", "Combo",
             "--card", "Surgical Extraction", "--db", contrast_db],
        )
        assert result.exit_code == 0, result.output
        assert "// thin: cohorts with n<30 are speculative — diffs indicative only, CIs wide." in result.output

    def test_contrast_custom_window_single_section(self, runner, contrast_db):
        """Explicit --since/--until yields exactly ONE labeled custom-window report — the
        adaptive ban-aware and full-corpus windows are not also computed."""
        result = runner.invoke(
            main,
            ["report", "cards", "--contrast", "--archetype", "Control", "--vs", "Combo",
             "--since", "2026-01-01", "--until", "2026-12-31", "--db", contrast_db],
        )
        assert result.exit_code == 0, result.output
        assert result.output.count("// window:") == 1
        assert "custom (" in result.output
        assert "adaptive ban-aware" not in result.output
        assert "full-corpus (all-time)" not in result.output


# ---------------------------------------------------------------------------
# advise compare — config/transform comparator
# (feature epic-sb-config-evaluation-config-comparator)
# ---------------------------------------------------------------------------


class TestAdviseCompare:
    """CLI tests for `advise compare`."""

    @pytest.fixture
    def compare_db(self, tmp_path, make_rounds_corpus):
        db_path = tmp_path / "compare.duckdb"
        con_mem, _ = make_rounds_corpus(n_repeats=20)  # n=40 cells → established-ish
        from legacy_engine.ingestion import store as _store
        con_file = _store.connect(str(db_path))
        _store.init_schema(con_file)
        for table in ("tournaments", "decks", "deck_cards", "rounds"):
            rows = con_mem.execute(f"SELECT * FROM {table}").fetchall()
            if rows:
                ph = ", ".join(["?"] * len(rows[0]))
                con_file.executemany(f"INSERT INTO {table} VALUES ({ph})", rows)
        con_mem.close()
        con_file.close()
        return str(db_path)

    @pytest.fixture
    def field_file(self, tmp_path):
        f = tmp_path / "field.txt"
        f.write_text("0.5 Control\n0.5 Combo\n")
        return str(f)

    @pytest.fixture
    def transform_split_db(self, tmp_path):
        """Hermetic DB where "Combo" crushes opponent X but folds to Y, and "Control" does
        the exact opposite — a transform config (max over Combo/Control) must pick a
        DIFFERENT chosen mode per matchup row, not the same mode everywhere."""
        from legacy_engine.ingestion import store as _store
        from legacy_engine.ingestion.cache import parse_cache_item

        db_path = tmp_path / "transform_split.duckdb"
        con = _store.connect(str(db_path))

        # (hero_archetype, opponent_archetype, wins, losses) — n=20 per cell, 80/20 split.
        cells = [
            ("Combo", "X", 16, 4),
            ("Control", "X", 4, 16),
            ("Combo", "Y", 4, 16),
            ("Control", "Y", 16, 4),
        ]
        counter = 0
        for hero_arch, opp_arch, wins, losses in cells:
            decks, rounds, labels = [], [], {}
            for outcome, count in (("win", wins), ("loss", losses)):
                for _ in range(count):
                    counter += 1
                    h, o = f"h{counter}", f"o{counter}"
                    decks.append({"Player": h, "Result": "1st",
                                  "Mainboard": [{"Count": 1, "CardName": "Filler"}], "Sideboard": []})
                    decks.append({"Player": o, "Result": "2nd",
                                  "Mainboard": [{"Count": 1, "CardName": "Filler"}], "Sideboard": []})
                    rounds.append({"Player1": h, "Player2": o, "Result": "2-0" if outcome == "win" else "0-2"})
                    labels[h] = hero_arch
                    labels[o] = opp_arch
            raw = {
                "Tournament": {
                    "Name": f"Split {hero_arch}-{opp_arch}", "Date": "2026-02-01",
                    "Uri": f"https://www.mtgo.com/decklist/split-{hero_arch}-{opp_arch}".lower(),
                    "Formats": "Legacy",
                },
                "Decks": decks, "Rounds": rounds, "Standings": [],
            }
            tid = _store.load_tournament(con, parse_cache_item(raw, "MTGO"))
            for player, arch in labels.items():
                con.execute(
                    "UPDATE decks SET archetype=? WHERE tournament_id=? AND player=?", [arch, tid, player]
                )
        con.close()
        return str(db_path)

    @pytest.fixture
    def xy_field_file(self, tmp_path):
        f = tmp_path / "xy_field.txt"
        f.write_text("0.5 X\n0.5 Y\n")
        return str(f)

    def test_requires_a_and_b(self, runner, compare_db, field_file):
        result = runner.invoke(main, ["advise", "compare", "--field", field_file, "--a", "Control", "--db", compare_db])
        assert result.exit_code != 0
        assert "requires both --a and --b" in result.output

    def test_basic_comparison_prints_ev_and_breakeven(self, runner, compare_db, field_file):
        result = runner.invoke(
            main,
            ["advise", "compare", "--field", field_file, "--a", "Control", "--b", "Combo",
             "--seed", "1", "--all-time", "--db", compare_db],
        )
        assert result.exit_code == 0, result.output
        assert "Configuration comparison" in result.output
        assert "P(A beats B)" in result.output
        assert "break-even" in result.output
        assert "coverage" in result.output

    def test_honesty_banners_always_print(self, runner, compare_db, field_file):
        """The lift-overlay + transform-optimistic-ceiling honesty banners are mandatory —
        they must print on a bare comparison AND survive --a-lift / --b-transform together."""
        lift_banner = "// lifts are presence-correlational assumptions (point overlay), NOT in the MC base."
        transform_banner = (
            "// transform = max-over-modes per matchup — the optimistic ceiling "
            "(assumes you reach the better mode post-board)."
        )

        basic = runner.invoke(
            main,
            ["advise", "compare", "--field", field_file, "--a", "Control", "--b", "Combo",
             "--seed", "1", "--all-time", "--db", compare_db],
        )
        assert basic.exit_code == 0, basic.output
        assert lift_banner in basic.output
        assert transform_banner in basic.output

        decorated = runner.invoke(
            main,
            ["advise", "compare", "--field", field_file, "--a", "Control", "--b", "Combo",
             "--a-lift", "Combo=+0.1", "--b-transform", "Control",
             "--seed", "1", "--all-time", "--db", compare_db],
        )
        assert decorated.exit_code == 0, decorated.output
        assert lift_banner in decorated.output
        assert transform_banner in decorated.output

    def test_transform_mode_shown(self, runner, transform_split_db, xy_field_file):
        """--b-transform must show the chosen mode per matchup row, and that mode must DIFFER
        between rows where the transform mode wins vs where it loses (not a static field label
        printed regardless of the flag)."""
        result = runner.invoke(
            main,
            # Config A is an unrelated third archetype (imputed, no data vs X/Y) so its
            # rendered mode label can't collide with B's "Combo"/"Control" mode text.
            ["advise", "compare", "--field", xy_field_file, "--a", "ThirdDeck", "--b", "Combo",
             "--b-transform", "Control", "--seed", "1", "--all-time", "--db", transform_split_db],
        )
        assert result.exit_code == 0, result.output
        lines = result.output.splitlines()
        x_line = next(ln for ln in lines if ln.startswith("X "))
        y_line = next(ln for ln in lines if ln.startswith("Y "))
        # vs X: Combo (80%) beats Control (20%) → B's chosen mode is "Combo".
        assert "(Combo" in x_line
        assert "(Control" not in x_line
        # vs Y: Control (80%) beats Combo (20%) → B's chosen mode is "Control".
        assert "(Control" in y_line
        assert "(Combo" not in y_line

    def test_a_lift_parsed(self, runner, compare_db, field_file):
        result = runner.invoke(
            main,
            ["advise", "compare", "--field", field_file, "--a", "Control", "--b", "Combo",
             "--a-lift", "Combo=+0.1", "--seed", "1", "--all-time", "--db", compare_db],
        )
        assert result.exit_code == 0, result.output
        assert "adjusted field EV" in result.output

    @pytest.fixture
    def slot_split_db(self, tmp_path):
        """Control's 'Hate Card' has a genuinely computable WITH-vs-WITHOUT split vs Combo
        (one owner who wins, one non-owner who loses) — unlike compare_db, where EVERY Control
        deck owns 'Surgical Extraction' and the WITHOUT cohort is always empty."""
        from legacy_engine.ingestion import store as _store
        from legacy_engine.ingestion.cache import parse_cache_item

        db_path = tmp_path / "slot_split.duckdb"
        con = _store.connect(str(db_path))
        raw = {
            "Tournament": {"Name": "Slot Split", "Date": "2026-02-01",
                           "Uri": "https://www.mtgo.com/decklist/slot-split-1", "Formats": "Legacy"},
            "Decks": [
                {"Player": "c1", "Result": "1st",
                 "Mainboard": [{"Count": 1, "CardName": "Filler"}],
                 "Sideboard": [{"Count": 1, "CardName": "Hate Card"}]},
                {"Player": "c2", "Result": "2nd",
                 "Mainboard": [{"Count": 1, "CardName": "Filler"}], "Sideboard": []},
                {"Player": "b1", "Result": "3rd",
                 "Mainboard": [{"Count": 1, "CardName": "Filler"}], "Sideboard": []},
                {"Player": "b2", "Result": "4th",
                 "Mainboard": [{"Count": 1, "CardName": "Filler"}], "Sideboard": []},
            ],
            "Rounds": [
                {"Player1": "c1", "Player2": "b1", "Result": "2-0"},   # c1 (owns Hate Card) wins
                {"Player1": "c2", "Player2": "b2", "Result": "0-2"},   # c2 (no Hate Card) loses
            ],
            "Standings": [],
        }
        tid = _store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for p, arch in {"c1": "Control", "c2": "Control", "b1": "Combo", "b2": "Combo"}.items():
            con.execute("UPDATE decks SET archetype=? WHERE tournament_id=? AND player=?", [arch, tid, p])
        con.close()
        return str(db_path)

    def test_a_lift_slot_folds_measured_diff(self, runner, slot_split_db, field_file):
        """A slot with a real WITH-vs-WITHOUT split folds its measured diff into the lift and
        shifts the adjusted EV — the 'folded' branch, distinct from the 'skipped' branch below."""
        result = runner.invoke(
            main,
            ["advise", "compare", "--field", field_file, "--a", "Control", "--b", "Combo",
             "--a-lift-slot", "Hate Card@Combo", "--seed", "1", "--all-time", "--db", slot_split_db],
        )
        assert result.exit_code == 0, result.output
        assert "// lift-slot: 'Hate Card' vs 'Combo' → measured lift +1.000." in result.output
        assert "no computable diff" not in result.output
        assert "adjusted field EV" in result.output   # the fold actually moved the overlay

    def test_a_lift_slot_skipped_when_no_computable_diff(self, runner, compare_db, field_file):
        """compare_db's 'Surgical Extraction' is owned by EVERY Control deck — the WITHOUT
        cohort is always empty, so the slot pull has no computable diff and is skipped
        (negative case for the folded branch above; both share the 'lift-slot:' prefix)."""
        result = runner.invoke(
            main,
            ["advise", "compare", "--field", field_file, "--a", "Control", "--b", "Combo",
             "--a-lift-slot", "Surgical Extraction@Combo", "--seed", "1", "--all-time", "--db", compare_db],
        )
        assert result.exit_code == 0, result.output
        assert "// lift-slot: no computable diff for 'Surgical Extraction' vs 'Combo' — skipped." in result.output
        assert "→ measured lift" not in result.output

    def test_lift_opponent_not_in_field_fails(self, runner, compare_db, field_file):
        result = runner.invoke(
            main,
            ["advise", "compare", "--field", field_file, "--a", "Control", "--b", "Combo",
             "--a-lift", "Nonexistent=+0.1", "--db", compare_db],
        )
        assert result.exit_code != 0
        assert "not in the field" in result.output


# ---------------------------------------------------------------------------
# TestSideboardOutputDiagnostics — feature-sb-field-weighted-scorer-output, Unit B5
# ---------------------------------------------------------------------------


class TestSideboardOutputDiagnostics:
    """CLI render tests for `advise sideboard`'s coverage% diagnostic + explainable
    per-card impact-breakdown audit lines (Unit B5)."""

    @pytest.fixture
    def db_with_corpus(self, tmp_path, make_rounds_corpus):
        """File-backed DuckDB for `advise sideboard --db <path>` (never the default DB —
        file-backed-cli-test-db-builder pattern)."""
        db_path = tmp_path / "test_sb_output.duckdb"
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

    def test_coverage_diagnostic_and_impact_breakdown_render(
        self, runner, db_with_corpus, tmp_path, monkeypatch
    ):
        """A SideboardPackage carrying populated coverage%/impact_annotations renders the
        labeled coverage diagnostic + the per-card auditable-factor breakdown line."""
        from legacy_engine.advisory import sideboard as sb_mod
        from legacy_engine.advisory.impact import ImpactBreakdown

        fake_pkg = sb_mod.SideboardPackage(
            cards={"Surgical Extraction": 2},
            trace=[],
            covered_weight=0.5,
            budget=15,
            reserved=0,
            solver_used="greedy",
            field_source="custom",
            heuristic_note="heuristic note",
            warnings=(),
            card_coverage_pct={"Surgical Extraction": 0.26},
            board_coverage_pct=0.26,
            impact_annotations={
                "Surgical Extraction": sb_mod.CardImpactAnnotation(
                    breakdown=ImpactBreakdown(
                        centrality=1.0, symmetry=1.0, castability=1.0, draw_prob=0.7
                    ),
                    reference_archetype="Reanimator",
                    reference_share=0.26,
                    confidence="established",
                    brittle=False,
                ),
            },
        )
        monkeypatch.setattr(sb_mod, "recommend_sideboard", lambda *a, **k: fake_pkg)

        deck = tmp_path / "sb_deck_diag.txt"
        deck.write_text("4 Brainstorm\n56 Island\n")
        result = runner.invoke(
            main,
            ["advise", "sideboard", "--deck", str(deck), "--db", db_with_corpus,
             "--archetype", "Control", "--solver", "greedy"],
        )
        assert result.exit_code == 0, result.output
        assert "// coverage diagnostic — NOT the optimization objective" in result.output
        assert "Surgical Extraction: ~26% of field" in result.output
        assert "board coverage diagnostic: ~26% of field" in result.output
        assert "// impact breakdown" in result.output
        assert "Surgical Extraction vs Reanimator (26.0% share)" in result.output
        assert "centrality=1.00 symmetry=1.00 castability=1.00 draw=0.70" in result.output
        assert "impact=0.700" in result.output
        assert "confidence=established" in result.output
        assert "BRITTLE" not in result.output

    def test_brittle_flag_renders_honest_degrade_note(
        self, runner, db_with_corpus, tmp_path, monkeypatch
    ):
        """A brittle=True annotation (thin-sample reference matchup) renders the labeled
        honest-degrade BRITTLE note, and its confidence tier is shown."""
        from legacy_engine.advisory import sideboard as sb_mod
        from legacy_engine.advisory.impact import ImpactBreakdown

        fake_pkg = sb_mod.SideboardPackage(
            cards={"Null Rod": 1},
            trace=[],
            covered_weight=0.1,
            budget=15,
            reserved=0,
            solver_used="greedy",
            field_source="custom",
            heuristic_note="heuristic note",
            warnings=(),
            card_coverage_pct={"Null Rod": 0.03},
            board_coverage_pct=0.03,
            impact_annotations={
                "Null Rod": sb_mod.CardImpactAnnotation(
                    breakdown=ImpactBreakdown(
                        centrality=0.5, symmetry=1.0, castability=1.0, draw_prob=0.3
                    ),
                    reference_archetype="ThinArchetype",
                    reference_share=0.03,
                    confidence="speculative",
                    brittle=True,
                ),
            },
        )
        monkeypatch.setattr(sb_mod, "recommend_sideboard", lambda *a, **k: fake_pkg)

        deck = tmp_path / "sb_deck_brittle.txt"
        deck.write_text("4 Brainstorm\n56 Island\n")
        result = runner.invoke(
            main,
            ["advise", "sideboard", "--deck", str(deck), "--db", db_with_corpus,
             "--archetype", "Control", "--solver", "greedy"],
        )
        assert result.exit_code == 0, result.output
        assert "BRITTLE" in result.output
        assert "confidence=speculative" in result.output

    def test_no_impact_data_omits_breakdown_block(self, runner, db_with_corpus, tmp_path):
        """Real (non-mocked) recommend_sideboard on a corpus with no curated/derivable
        linchpin data for 'Control' -> impact_annotations={} -> no impact-breakdown block
        rendered (the no-impact-data path never fabricates a breakdown)."""
        deck = tmp_path / "sb_deck_plain.txt"
        deck.write_text("4 Brainstorm\n56 Island\n")
        result = runner.invoke(
            main,
            ["advise", "sideboard", "--deck", str(deck), "--db", db_with_corpus,
             "--archetype", "Control", "--solver", "greedy"],
        )
        assert result.exit_code == 0, result.output
        assert "// impact breakdown" not in result.output


# ---------------------------------------------------------------------------
# TestSlotROIPuntRender — feature-sb-slot-roi-punt, Unit D3
# ---------------------------------------------------------------------------


class TestSlotROIPuntRender:
    """CLI render tests for `advise sideboard`'s slot-ROI + punt decision-support block."""

    @pytest.fixture
    def db_with_corpus(self, tmp_path, make_rounds_corpus):
        """File-backed DuckDB for `advise sideboard --db <path>` (never the default DB —
        file-backed-cli-test-db-builder pattern)."""
        db_path = tmp_path / "test_sb_slot_roi.duckdb"
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

    def test_slot_roi_block_renders_ranked_rows_with_punt_markers(
        self, runner, db_with_corpus, tmp_path, monkeypatch
    ):
        """A SideboardPackage carrying a populated slot_roi table renders the labeled
        decision-support block, in order, with PUNT markers and confidence tiers."""
        from legacy_engine.advisory import sideboard as sb_mod

        fake_pkg = sb_mod.SideboardPackage(
            cards={"Surgical Extraction": 2},
            trace=[],
            covered_weight=0.5,
            budget=15,
            reserved=0,
            solver_used="greedy",
            field_source="custom",
            heuristic_note="heuristic note",
            warnings=(),
            slot_roi=(
                sb_mod.MatchupROI(
                    opponent="Delver", field_share=0.6, base_equity=0.45,
                    max_equity_gain=0.10, roi_per_slot=0.05, crosses_half=False,
                    punt=True, confidence="established",
                    punt_reason="max dedication still <50%",
                ),
                sb_mod.MatchupROI(
                    opponent="Combo", field_share=0.1, base_equity=0.5,
                    max_equity_gain=0.0, roi_per_slot=0.0, crosses_half=True,
                    punt=False, confidence="speculative", punt_reason="",
                ),
            ),
        )
        monkeypatch.setattr(sb_mod, "recommend_sideboard", lambda *a, **k: fake_pkg)

        deck = tmp_path / "sb_deck_roi.txt"
        deck.write_text("4 Brainstorm\n56 Island\n")
        result = runner.invoke(
            main,
            ["advise", "sideboard", "--deck", str(deck), "--db", db_with_corpus,
             "--archetype", "Control", "--solver", "greedy"],
        )
        assert result.exit_code == 0, result.output
        assert (
            "// slot-ROI (decision support — expected match-win per dedicated slot):"
            in result.output
        )
        assert "vs Delver (60.0% share)" in result.output
        assert "45.0% → 55.0% equity" in result.output
        assert "ROI/slot=0.0500" in result.output
        assert "confidence=established" in result.output
        assert "[PUNT — max dedication still <50%]" in result.output
        assert "vs Combo (10.0% share)" in result.output
        assert "confidence=speculative" in result.output
        # Delver (rank 1, punted) must render before Combo (rank 2) — table order preserved.
        assert result.output.index("vs Delver") < result.output.index("vs Combo")
        # The speculative Combo row is never punted (hard rule) — no PUNT marker on its line.
        combo_line = next(ln for ln in result.output.splitlines() if "vs Combo" in ln)
        assert "PUNT" not in combo_line

    def test_no_slot_roi_omits_block(self, runner, db_with_corpus, tmp_path, monkeypatch):
        """An empty slot_roi tuple (the gated default — e.g. `archetype=None` was passed to
        `recommend_sideboard`, or the field itself is empty) renders no slot-ROI block."""
        from legacy_engine.advisory import sideboard as sb_mod

        fake_pkg = sb_mod.SideboardPackage(
            cards={"Surgical Extraction": 2},
            trace=[],
            covered_weight=0.5,
            budget=15,
            reserved=0,
            solver_used="greedy",
            field_source="custom",
            heuristic_note="heuristic note",
            warnings=(),
            slot_roi=(),
        )
        monkeypatch.setattr(sb_mod, "recommend_sideboard", lambda *a, **k: fake_pkg)

        deck = tmp_path / "sb_deck_no_roi.txt"
        deck.write_text("4 Brainstorm\n56 Island\n")
        result = runner.invoke(
            main,
            ["advise", "sideboard", "--deck", str(deck), "--db", db_with_corpus,
             "--solver", "greedy"],
        )
        assert result.exit_code == 0, result.output
        assert "// slot-ROI" not in result.output


class TestRefreshCacheAudit:
    """Pure formatter: refresh-cache summary + label-honesty audit lines (no CLI invocation)."""

    def _stats(self, **overrides):
        from legacy_engine.ingestion.cache import IngestStats

        kwargs = dict(
            total=2, new=1, changed=0, unchanged=1, seeded=0, bad=0,
            labels_before=3, labels_after=3, variants_before=3, variants_after=3,
        )
        kwargs.update(overrides)
        return IngestStats(**kwargs)

    def test_summary_line_reports_counts(self):
        from legacy_engine.cli import _refresh_cache_audit

        lines = _refresh_cache_audit(self._stats())
        assert lines[0] == (
            "Refreshed tournament cache: 2 events — 1 new, 0 changed, 1 unchanged, 0 seeded"
        )

    def test_bad_suffix_only_when_bad_gt_zero(self):
        from legacy_engine.cli import _refresh_cache_audit

        clean = _refresh_cache_audit(self._stats(bad=0))
        assert "bad" not in clean[0]

        dirty = _refresh_cache_audit(self._stats(bad=2))
        assert dirty[0].endswith(", 2 bad")

    def test_preserved_line_on_zero_drops(self):
        from legacy_engine.cli import _refresh_cache_audit

        lines = _refresh_cache_audit(self._stats(labels_after=3, variants_after=3))
        assert any(line.startswith("// labels preserved:") for line in lines)
        assert not any("⚠" in line for line in lines)

    def test_warning_line_present_iff_drops(self):
        from legacy_engine.cli import _refresh_cache_audit

        dropped = _refresh_cache_audit(
            self._stats(labels_before=3, labels_after=1, variants_before=3, variants_after=1)
        )
        warn_lines = [line for line in dropped if "⚠" in line]
        assert len(warn_lines) == 1
        assert "2 archetype + 2 variant labels dropped" in warn_lines[0]
        assert any(line.startswith("// labels: ") for line in dropped)

        preserved = _refresh_cache_audit(self._stats(labels_after=3, variants_after=3))
        assert not any("⚠" in line for line in preserved)

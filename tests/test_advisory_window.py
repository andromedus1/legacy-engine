"""Tests for epic-regime-aware-advisory-cli-surface — resolve_advisory_window + the CLI flags.

`make_rounds_corpus(n)` yields 4 rounds per repeat dated 2026-01-(r+1), so n repeats = 4n rounds
within [2026-01-01, 2026-01-(n+1)). The latest ban regime ("current") opens 2026-05-18, so the
corpus has ZERO rounds in the current regime — a natural thin-degrade case.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.advisory.window import WindowResolution, resolve_advisory_window
from legacy_engine.cli import main
from legacy_engine.ingestion import store


class TestResolveAdvisoryWindow:
    def test_all_time_no_degrade(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=1)
        res = resolve_advisory_window(con, all_time=True)
        assert res == WindowResolution(None, None, None, "full-corpus")
        con.close()

    def test_default_is_full_corpus(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=1)
        res = resolve_advisory_window(con)  # no flags
        assert res.since is None and res.until is None and res.banner is None
        con.close()

    def test_all_time_beats_regime(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=1)
        res = resolve_advisory_window(con, regime="current", all_time=True)
        assert res.since is None and res.until is None and res.banner is None
        con.close()

    def test_current_regime_degrades_when_thin(self, make_rounds_corpus):
        # Corpus is all Jan-2026 → ZERO rounds in the current (2026-05-18+) regime → degrade.
        con, _ = make_rounds_corpus(n_repeats=5)
        res = resolve_advisory_window(con, regime="current")
        assert res.since is None and res.until is None      # degraded to full corpus
        assert res.banner is not None and "THIN" in res.banner
        assert "regime: current" in res.requested_label
        con.close()

    def test_window_with_enough_rounds_kept(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=50)            # 200 rounds in Jan 2026
        res = resolve_advisory_window(
            con, since="2026-01-01", until="2026-03-01", thin_floor=10,
        )
        assert res.since == "2026-01-01" and res.until == "2026-03-01"
        assert res.banner is None
        con.close()

    def test_explicit_window_below_floor_degrades(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=2)             # 8 rounds total
        res = resolve_advisory_window(con, since="2026-01-01", until="2026-01-03", thin_floor=500)
        assert res.since is None and res.until is None and res.banner is not None
        con.close()

    def test_thin_floor_zero_disables_degrade(self, make_rounds_corpus):
        # Deck-based surfaces (report meta) pass thin_floor=0 → window honored, never degraded.
        con, _ = make_rounds_corpus(n_repeats=2)
        res = resolve_advisory_window(con, regime="current", thin_floor=0)
        assert res.since == "2026-05-18" and res.until is None and res.banner is None
        con.close()


class TestWindowCLI:
    @pytest.fixture
    def db_path(self, tmp_path, make_rounds_corpus):
        path = tmp_path / "win.duckdb"
        con_mem, _ = make_rounds_corpus(n_repeats=50)
        con_file = store.connect(str(path))
        store.init_schema(con_file)
        for table in ("tournaments", "decks", "deck_cards", "rounds"):
            rows = con_mem.execute(f"SELECT * FROM {table}").fetchall()
            if rows:
                ph = ", ".join(["?"] * len(rows[0]))
                con_file.executemany(f"INSERT INTO {table} VALUES ({ph})", rows)
        con_mem.close()
        con_file.close()
        return str(path)

    def test_matchups_help_lists_window_flags(self):
        result = CliRunner().invoke(main, ["report", "matchups", "--help"])
        assert result.exit_code == 0
        for opt in ("--since", "--until", "--regime", "--all-time"):
            assert opt in result.output

    def test_no_flags_is_adaptive(self, db_path):
        # v2: matchups default is now adaptive (per-cell ban-aware), not full-corpus.
        result = CliRunner().invoke(main, ["report", "matchups", "--db", db_path, "--provenance", "online"])
        assert result.exit_code == 0, result.output
        assert "window: adaptive" in result.output

    def test_all_time_says_full_corpus(self, db_path):
        result = CliRunner().invoke(
            main, ["report", "matchups", "--db", db_path, "--provenance", "online", "--all-time"]
        )
        assert result.exit_code == 0, result.output
        assert "window: full-corpus" in result.output

    def test_regime_current_degrades_with_banner(self, db_path):
        # current regime has no rounds in this Jan-2026 corpus → degrade banner.
        result = CliRunner().invoke(
            main, ["report", "matchups", "--db", db_path, "--provenance", "online", "--regime", "current"]
        )
        assert result.exit_code == 0, result.output
        assert "THIN" in result.output and "window: full-corpus" in result.output

    def test_meta_since_windows(self, db_path):
        result = CliRunner().invoke(
            main, ["report", "meta", "--db", db_path, "--definition", "raw",
                   "--provenance", "online", "--since", "2026-01-01", "--until", "2026-03-01"]
        )
        assert result.exit_code == 0, result.output
        assert "window:" in result.output

    def test_meta_does_not_degrade_on_thin_rounds(self, db_path):
        # Meta is deck-based (thin_floor=0): an explicit window is honored, NOT degraded to
        # full-corpus, even though it's below the matchup rounds floor.
        result = CliRunner().invoke(
            main, ["report", "meta", "--db", db_path, "--definition", "raw",
                   "--provenance", "online", "--since", "2026-01-01", "--until", "2026-03-01"]
        )
        assert result.exit_code == 0, result.output
        assert "window: 2026-01-01" in result.output
        assert "THIN" not in result.output          # no rounds-degrade for meta

    def test_meta_skips_wrw_under_window(self, db_path):
        # Meta doesn't degrade (thin_floor=0), so the window stands → wrw is skipped.
        result = CliRunner().invoke(
            main, ["report", "meta", "--db", db_path, "--definition", "wrw",
                   "--provenance", "online", "--since", "2026-01-01", "--until", "2026-03-01"]
        )
        assert result.exit_code == 0, result.output
        assert "skipping wrw under a window" in result.output


class TestMetashareDocRot:
    def test_stale_claim_removed(self):
        import inspect
        from legacy_engine.analytics import metashare
        src = inspect.getsource(metashare.compute_metashare)
        assert "match_results is not windowed" not in src

    def test_windowed_wrw_still_raises(self, make_rounds_corpus):
        from legacy_engine.analytics.metashare import compute_metashare
        con, _ = make_rounds_corpus(n_repeats=1)
        with pytest.raises(NotImplementedError):
            compute_metashare(con, definition="wrw", since="2026-01-01")
        con.close()

"""Tests for epic-regime-aware-advisory-cli-surface — resolve_advisory_window + the CLI flags.

`make_rounds_corpus(n)` yields 4 rounds per repeat dated 2026-01-(r+1), so n repeats = 4n rounds
within [2026-01-01, 2026-01-(n+1)). The latest ban regime ("current") opens on the ledger's last
confirmed ban date (see `in_current_regime`/`BAN_EVENTS`), well after Jan 2026, so the corpus has
ZERO rounds in the current regime — a natural thin-degrade case.
"""

from __future__ import annotations

import re

import pytest
from click.testing import CliRunner

from legacy_engine.advisory.window import (
    WindowResolution,
    _adaptive_audit,
    _count_rounds,
    build_advisory_inputs,
    resolve_advisory_window,
)
from legacy_engine.analytics.eras.consume import EraHorizon
from legacy_engine.cli import main
from legacy_engine.ingestion import store
from tests.conftest import in_current_regime


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

    def test_thin_banner_states_count_and_floor(self, make_rounds_corpus):
        # HONEST-DEGRADE NFR: the banner must carry the NAMED REASON — the actual round
        # count AND the floor — not merely the word "THIN". A regression dropping either
        # {n_rounds} or {thin_floor} from the banner must fail here.
        con, _ = make_rounds_corpus(n_repeats=2)
        res = resolve_advisory_window(con, since="2026-01-01", until="2026-01-03", thin_floor=500)
        assert res.banner is not None
        assert re.search(r"\b\d+ rounds < floor 500\b", res.banner), res.banner
        con.close()

    def test_exactly_floor_rounds_does_not_degrade(self, make_rounds_corpus):
        # Degrade is strictly `n_rounds < floor`, so a window with EXACTLY floor rounds
        # must NOT degrade (boundary pin). Read the in-window count, then set floor == it.
        con, _ = make_rounds_corpus(n_repeats=2)
        n = _count_rounds(con, since="2026-01-01", until="2026-01-03", provenance=None)
        assert n > 0, "window must actually contain rounds for this boundary test"
        res = resolve_advisory_window(con, since="2026-01-01", until="2026-01-03", thin_floor=n)
        assert res.banner is None                                   # n == floor → not thin
        assert res.since == "2026-01-01" and res.until == "2026-01-03"
        con.close()

    def test_thin_floor_zero_disables_degrade(self, make_rounds_corpus):
        # Deck-based surfaces (report meta) pass thin_floor=0 → window honored, never degraded.
        con, _ = make_rounds_corpus(n_repeats=2)
        res = resolve_advisory_window(con, regime="current", thin_floor=0)
        assert res.since == in_current_regime(0) and res.until is None and res.banner is None
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

    def test_meta_wrw_under_window_now_computes(self, db_path):
        # wrw is now windowed (finding: wrw-windowed) — no longer skipped under a window.
        result = CliRunner().invoke(
            main, ["report", "meta", "--db", db_path, "--definition", "wrw",
                   "--provenance", "online", "--since", "2026-01-01", "--until", "2026-03-01"]
        )
        assert result.exit_code == 0, result.output
        # The old "skipping wrw under a window" message must no longer appear.
        assert "skipping wrw under a window" not in result.output


class TestMetashareDocRot:
    def test_stale_claim_removed(self):
        import inspect
        from legacy_engine.analytics import metashare
        src = inspect.getsource(metashare.compute_metashare)
        assert "match_results is not windowed" not in src

    def test_windowed_wrw_now_computes(self, make_rounds_corpus):
        """wrw under a window is now supported (finding: wrw-windowed); must not raise."""
        from legacy_engine.analytics.metashare import compute_metashare
        con, _ = make_rounds_corpus(n_repeats=1)
        # Must succeed and return a valid MetaShareReport.
        report = compute_metashare(con, definition="wrw", since="2026-01-01")
        assert report.definition == "wrw"
        con.close()


# ---------------------------------------------------------------------------
# epic-stable-era-windows-consumption Unit 3 — trigger-carrying adaptive audit + field era
# ---------------------------------------------------------------------------


class TestAdaptiveAudit:
    def test_no_disturbance_no_ban_only(self):
        lines = _adaptive_audit({"Control": EraHorizon(since=None, source="era", trigger=None, alarm=None)})
        assert lines == ("// adaptive: no entity disturbed — all cells use full corpus",)

    def test_named_entity_carries_trigger(self):
        horizon_meta = {
            "Doomsday": EraHorizon(
                since="2026-04-20", source="era",
                trigger="release: Flow State adoption (2026-04-20)", alarm=None,
            ),
            "Control": EraHorizon(since=None, source="era", trigger=None, alarm=None),
        }
        lines = _adaptive_audit(horizon_meta)
        assert len(lines) == 1
        assert lines[0] == (
            "// adaptive: per-entity era windows — Doomsday since 2026-04-20 "
            "(release: Flow State adoption (2026-04-20)); all others full-corpus"
        )

    def test_ban_only_entities_are_counted_not_named(self):
        horizon_meta = {
            "A": EraHorizon(since="2025-11-10", source="ban-only", trigger="ban: valid_since 2025-11-10", alarm=None),
            "B": EraHorizon(since=None, source="ban-only", trigger=None, alarm=None),
            "C": EraHorizon(since=None, source="era", trigger=None, alarm=None),
        }
        lines = _adaptive_audit(horizon_meta)
        assert lines == ("// adaptive: per-entity era windows — 2 entities ban-only; all others full-corpus",)

    def test_alarm_lines_append_never_truncate(self):
        horizon_meta = {
            "Tron": EraHorizon(since=None, source="era", trigger=None, alarm="unattributed disturbance (p_change=0.970)"),
            "Control": EraHorizon(since=None, source="era", trigger=None, alarm=None),
        }
        lines = _adaptive_audit(horizon_meta)
        assert len(lines) == 2
        assert lines[0] == "// adaptive: no entity disturbed — all cells use full corpus"
        assert lines[1] == "// ⚠ Tron: unattributed disturbance (p_change=0.970)"

    def test_audit_preamble_prepended_verbatim(self):
        lines = _adaptive_audit(
            {"X": EraHorizon(since=None, source="ban-only", trigger=None, alarm=None)},
            audit_preamble=("// eras: no era data — ban-only horizons; run `eras run`",),
        )
        assert lines[0] == "// eras: no era data — ban-only horizons; run `eras run`"
        assert lines[1] == "// adaptive: per-entity era windows — 1 entity ban-only; all others full-corpus"


class TestBuildAdvisoryInputsFieldEra:
    def test_adaptive_mode_uses_resolve_field_era(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=1)
        win = resolve_advisory_window(con)
        assert win.mode == "adaptive"
        inputs = build_advisory_inputs(con, win)
        from legacy_engine.analytics.trends import resolve_regime
        expected_since, _ = resolve_regime("current")
        assert inputs.field_since == expected_since
        assert inputs.field_until is None
        assert any(line.startswith("// field: since") for line in inputs.audit)
        con.close()

    def test_uniform_mode_field_shares_the_window(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=50)
        win = resolve_advisory_window(con, since="2026-01-01", until="2026-02-01", thin_floor=0)
        inputs = build_advisory_inputs(con, win)
        assert inputs.field_since == "2026-01-01"
        assert inputs.field_until == "2026-02-01"
        assert inputs.audit == ()
        con.close()

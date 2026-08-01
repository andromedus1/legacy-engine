"""CLI tests for the `eras` command group (Unit E: run|list|explain|confirm).

House style: file-backed hermetic DuckDB via a `_build_eras_db(tmp_path) -> str` builder,
every `runner.invoke` pinned to `--db <that path>` — never the default DB. `eras confirm` is
tested against a tmp COPY of the shipped events.json via `--events-path` — the real shipped file
is never touched by these tests. TestErasConfirm registers a SYNTHETIC event (not a real card)
because Candelabra of Tawnos's confirmation is now itself a permanent row in the shipped
events.json (dogfooding registered it 2026-06-29), so a tmp copy of the real ledger already
contains it.
"""

from __future__ import annotations

import shutil
from datetime import date, timedelta

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.config import BAN_EVENTS_PATH
from legacy_engine.ingestion import store as _store
from legacy_engine.ingestion.cache import parse_cache_item
from tests.conftest import in_current_regime

# Same implanted-cliff shape as tests/analytics/eras/test_run.py's DB corpus (kept independent —
# CLI tests can't import fixtures across the tests/analytics/eras/ package boundary, so a minimal
# replica lives here per this module's own docstring convention).
_WEEKLY = [2, 5, 12, 34, 23, 42, 37, 41, 52, 20, 28, 36, 50, 58, 59, 59, 20, 1]
_FIELD_TOTAL = 420
_CLIFF_START = date(2026, 1, 26)  # a Monday; week index 16 lands on 2026-05-18 (Undercity Informer).
assert _CLIFF_START.isoweekday() == 1
assert (_CLIFF_START + timedelta(weeks=16)).isoformat() == "2026-05-18"


def _build_eras_db(tmp_path) -> str:
    """File-backed hermetic DuckDB: Tron (100% Undercity Informer -> ban-attributed via the
    unverified date-match fallback) and Drift (15% Undercity Informer -> unattributed, alarm-
    eligible), sharing a constant 420-deck/week field with Filler."""
    db_path = str(tmp_path / "eras_cli.duckdb")
    con = _store.connect(db_path)

    for i, wk in enumerate(_WEEKLY):
        monday = _CLIFF_START + timedelta(weeks=i)
        drift_card_n = round(0.15 * wk)
        filler_n = _FIELD_TOTAL - 2 * wk

        decks: list[dict] = []
        for j in range(wk):
            decks.append({
                "Player": f"tron_{i}_{j}",
                "Mainboard": [{"Count": 1, "CardName": "Undercity Informer"}],
                "Sideboard": [],
            })
        for j in range(wk):
            mainboard = [{"Count": 1, "CardName": "Undercity Informer"}] if j < drift_card_n else []
            decks.append({"Player": f"drift_{i}_{j}", "Mainboard": mainboard, "Sideboard": []})
        for j in range(filler_n):
            decks.append({"Player": f"filler_{i}_{j}", "Mainboard": [], "Sideboard": []})

        raw = {
            "Tournament": {
                "Name": f"Week {i}", "Date": monday.isoformat(),
                "Uri": f"https://example.com/week-{i}", "Formats": "Legacy",
            },
            "Decks": decks, "Rounds": [], "Standings": [],
        }
        tid = _store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Tron' WHERE tournament_id = ? AND player LIKE ?",
            [tid, f"tron_{i}_%"],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Drift' WHERE tournament_id = ? AND player LIKE ?",
            [tid, f"drift_{i}_%"],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Filler' WHERE tournament_id = ? AND player LIKE ?",
            [tid, f"filler_{i}_%"],
        )
    con.close()
    return db_path


@pytest.fixture
def runner():
    return CliRunner()


class TestErasRun:
    def test_analyzes_all_entities_and_reports_alarm(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        result = runner.invoke(main, ["eras", "run", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "3 entities analyzed" in result.output
        assert "Tron:" in result.output
        assert "Drift:" in result.output
        assert "⚠ Drift:" in result.output

    def test_never_touches_default_db(self, tmp_path, runner, monkeypatch):
        # Point the default DUCKDB_PATH at a location that would error loudly if ever opened,
        # proving --db is honored end-to-end.
        db_path = _build_eras_db(tmp_path)
        bad_default = tmp_path / "should_never_be_touched" / "legacy.duckdb"
        monkeypatch.setattr("legacy_engine.config.DUCKDB_PATH", bad_default)
        result = runner.invoke(main, ["eras", "run", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert not bad_default.parent.exists()

    def test_respects_provenance_filter(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        result = runner.invoke(main, ["eras", "run", "--db", db_path, "--provenance", "online"])
        assert result.exit_code == 0, result.output


class TestErasList:
    def test_no_data_before_a_run(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        result = runner.invoke(main, ["eras", "list", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "no era data" in result.output

    def test_lists_entities_with_trigger_and_tier(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        runner.invoke(main, ["eras", "run", "--db", db_path])
        result = runner.invoke(main, ["eras", "list", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "Tron:" in result.output
        assert "Drift:" in result.output
        assert "trigger:" in result.output
        # Confidence tier is present (established, given ~580 post-boundary decks per entity).
        assert "established" in result.output or "evolving" in result.output


class TestErasExplain:
    def test_walks_tron_boundary_derivation_with_ban_attribution(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        runner.invoke(main, ["eras", "run", "--db", db_path])
        result = runner.invoke(main, ["eras", "explain", "Tron", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "Tron" in result.output
        assert "attribution: ban: Undercity Informer" in result.output

    def test_walks_drift_boundary_derivation_unattributed_with_alarm(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        runner.invoke(main, ["eras", "run", "--db", db_path])
        result = runner.invoke(main, ["eras", "explain", "Drift", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "unattributed disturbance" in result.output
        assert "⚠" in result.output

    def test_unknown_entity_raises_clean_click_exception(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        runner.invoke(main, ["eras", "run", "--db", db_path])
        result = runner.invoke(main, ["eras", "explain", "Nonexistent Archetype", "--db", db_path])
        assert result.exit_code != 0
        assert "unknown entity" in result.output

    def test_unknown_entity_before_any_run_also_raises(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        result = runner.invoke(main, ["eras", "explain", "Anything", "--db", db_path])
        assert result.exit_code != 0
        assert "unknown entity" in result.output


class TestErasRunRegisteredBanWording:
    """Finding A end-to-end through the CLI: Tron's own boundary is ban-attributed (Undercity
    Informer) but the alarm still fires at n=3 (no BH-FDR power) — wording must consult the real
    shipped ledger and say "registered ban", never "possible unregistered". Drift's genuinely
    unrelated 15% inclusion must stay the classic unattributed wording in the SAME run, proving
    the plausibility gate (not mere ban proximity) drives the corrected wording end-to-end."""

    def test_eras_run_shows_both_wordings_in_one_run(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        result = runner.invoke(main, ["eras", "run", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "// ⚠ Tron: registered ban" in result.output
        assert "Undercity Informer" in result.output
        assert "// ⚠ Drift: unattributed disturbance" in result.output

    def test_eras_explain_shows_corrected_wording(self, tmp_path, runner):
        db_path = _build_eras_db(tmp_path)
        runner.invoke(main, ["eras", "run", "--db", db_path])
        result = runner.invoke(main, ["eras", "explain", "Tron", "--db", db_path])
        assert result.exit_code == 0, result.output
        # The alarm line (`// ⚠ ...`, distinct from each boundary's own per-derivation
        # `attribution:` line, which legitimately stays "possible unregistered" for Tron's
        # earlier, genuinely-unrelated small boundaries) must read the corrected wording.
        alarm_line = next(line for line in result.output.splitlines() if line.startswith("// ⚠"))
        assert "registered ban" in alarm_line
        assert "Undercity Informer" in alarm_line
        assert "possible unregistered" not in alarm_line


class TestErasConfirm:
    """`eras confirm` is exercised against a SYNTHETIC event, not the real Candelabra of Tawnos
    ban — that ban is itself now a real, permanent row in the shipped `events.json` (this test
    module's own docstring notes Candelabra's registration was a later dogfooding action), so a
    tmp copy of the shipped ledger already contains it and re-confirming it would just hit the
    duplicate-event guard. The synthetic card/date are derived from the ledger's own last event
    (`in_current_regime`, tests/conftest.py) so they never collide with real entries and never
    go stale as the ledger grows further.
    """

    _CONFIRM_CARD = "Hypothetical Test-Only Ban Card"
    _CONFIRM_REASON = "synthetic reason for the eras-confirm CLI test suite"

    def _confirm_date(self) -> str:
        return in_current_regime(30)

    def _tmp_events_copy(self, tmp_path):
        dest = tmp_path / "events_copy.json"
        shutil.copy(BAN_EVENTS_PATH, dest)
        return dest

    def test_confirm_appends_and_echoes_healed_regime(self, tmp_path, runner):
        events_path = self._tmp_events_copy(tmp_path)
        confirm_date = self._confirm_date()
        result = runner.invoke(main, [
            "eras", "confirm", confirm_date, self._CONFIRM_CARD, self._CONFIRM_REASON,
            "--events-path", str(events_path),
        ])
        assert result.exit_code == 0, result.output
        assert f"registered: {self._CONFIRM_CARD} banned {confirm_date}" in result.output
        assert "regime healed" in result.output
        assert confirm_date in result.output

    def test_confirm_round_trips_through_a_fresh_load(self, tmp_path, runner):
        from legacy_engine.ingestion.banlist import load_ban_events

        events_path = self._tmp_events_copy(tmp_path)
        confirm_date = self._confirm_date()
        before = load_ban_events(events_path)
        runner.invoke(main, [
            "eras", "confirm", confirm_date, self._CONFIRM_CARD, self._CONFIRM_REASON,
            "--events-path", str(events_path),
        ])
        after = load_ban_events(events_path)
        assert len(after) == len(before) + 1
        assert (date.fromisoformat(confirm_date), self._CONFIRM_CARD, self._CONFIRM_REASON) in after

    def test_confirm_heals_regime_windows_once_ban_events_is_refreshed(self, tmp_path, runner, monkeypatch):
        # regime_windows() reads analytics.trends's OWN captured BAN_EVENTS reference (bound at
        # trends.py's import time) — a live long-running process only sees a confirmed event on
        # its NEXT import, never hot. Monkeypatching that reference simulates exactly what a
        # fresh process picks up, and proves the healing mechanism (not just the JSON write).
        from legacy_engine.analytics import trends
        from legacy_engine.ingestion.banlist import load_ban_events

        events_path = self._tmp_events_copy(tmp_path)
        confirm_date = self._confirm_date()
        runner.invoke(main, [
            "eras", "confirm", confirm_date, self._CONFIRM_CARD, self._CONFIRM_REASON,
            "--events-path", str(events_path),
        ])
        refreshed = load_ban_events(events_path)
        monkeypatch.setattr(trends, "BAN_EVENTS", refreshed)

        windows = trends.regime_windows()
        expected = date.fromisoformat(confirm_date)
        assert any(w.since == expected for w in windows), (
            f"no regime window opens at {confirm_date} after refresh: {[w.since for w in windows]}"
        )

    def test_duplicate_event_raises_clean_click_exception(self, tmp_path, runner):
        events_path = self._tmp_events_copy(tmp_path)
        confirm_date = self._confirm_date()
        runner.invoke(main, [
            "eras", "confirm", confirm_date, self._CONFIRM_CARD, self._CONFIRM_REASON,
            "--events-path", str(events_path),
        ])
        result = runner.invoke(main, [
            "eras", "confirm", confirm_date, self._CONFIRM_CARD, self._CONFIRM_REASON,
            "--events-path", str(events_path),
        ])
        assert result.exit_code != 0
        assert "already has an event" in result.output

    def test_invalid_date_raises_clean_click_exception(self, tmp_path, runner):
        events_path = self._tmp_events_copy(tmp_path)
        result = runner.invoke(main, [
            "eras", "confirm", "not-a-date", "Some Card", "some reason",
            "--events-path", str(events_path),
        ])
        assert result.exit_code != 0
        assert "invalid DATE" in result.output

    def test_never_touches_the_real_shipped_events_file(self, tmp_path, runner):
        from legacy_engine.ingestion.banlist import load_ban_events

        real_before = load_ban_events(BAN_EVENTS_PATH)
        events_path = self._tmp_events_copy(tmp_path)
        runner.invoke(main, [
            "eras", "confirm", self._confirm_date(), self._CONFIRM_CARD, self._CONFIRM_REASON,
            "--events-path", str(events_path),
        ])
        real_after = load_ban_events(BAN_EVENTS_PATH)
        assert real_before == real_after

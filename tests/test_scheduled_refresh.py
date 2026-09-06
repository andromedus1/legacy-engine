from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import signal

import pytest

from legacy_engine.ingestion.card_coverage import CardCoverageReport
from legacy_engine.ops.scheduled_refresh import (
    LockUnavailable,
    decision_refresh_lock_path,
    run_scheduled_decision_refresh,
)
from legacy_engine.ops.status import JobOutcome, JobStatus
from legacy_engine.ingestion.releases import SetRelease
from legacy_engine.workflows.decision_refresh import (
    CampApplyResult,
    EraRunResult,
    SourceRefreshResult,
)


NOW = datetime(2026, 8, 11, 18, 0, tzinfo=timezone.utc)


class RecordingPorts:
    def __init__(self, *, fail_at: str | None = None, degrade: bool = False):
        self.calls: list[str] = []
        self.fail_at = fail_at
        self.degrade = degrade

    def _record(self, name: str) -> None:
        self.calls.append(name)
        if name == self.fail_at:
            raise RuntimeError(f"{name} broke")

    def refresh_sources(self, db_path: Path):
        self._record("sources")
        return SourceRefreshResult(
            release_scan_reason="scan offline" if self.degrade else None,
            summary="sources current",
        )

    def reconcile_cards(self, db_path: Path, source_result: SourceRefreshResult):
        self._record("card_coverage")
        return CardCoverageReport(distinct_names=1, affected_decks=0)

    def label(self, db_path: Path):
        self._record("label")
        return 2

    def apply_staged_camps(self, db_path: Path):
        self._record("staged_camps")
        return CampApplyResult()

    def run_eras(self, db_path: Path):
        self._record("eras")
        return EraRunResult(entities=1, alarms=("possible unregistered change",))

    def write_ranking(self, db_path: Path, out_path: Path):
        self._record("ranking")
        out_path.write_text("ranking", encoding="utf-8")


class TickingClock:
    def __init__(self):
        self.current = NOW

    def __call__(self):
        value = self.current
        self.current += timedelta(seconds=1)
        return value


def _run(tmp_path, ports, **changes) -> JobStatus:
    values = {
        "db_path": tmp_path / "test.duckdb",
        "out_path": tmp_path / "ranking.html",
        "status_dir": tmp_path / "status",
        "lock_path": tmp_path / "locks" / "refresh.lock",
        "clock": TickingClock(),
        "attempt_id_factory": lambda: "attempt-1",
        "pid": 42,
    }
    values.update(changes)
    return run_scheduled_decision_refresh(ports, **values)


class TestScheduledDecisionRefresh:
    def test_lock_identity_depends_on_artifacts_not_status_storage(self, tmp_path):
        db = tmp_path / "db.duckdb"
        out = tmp_path / "ranking.html"
        first = decision_refresh_lock_path(db, out, lock_dir=tmp_path / "locks")
        second = decision_refresh_lock_path(db, out, lock_dir=tmp_path / "locks")
        different = decision_refresh_lock_path(db, tmp_path / "other.html", lock_dir=tmp_path / "locks")
        assert first == second
        assert first != different

    def test_success_holds_lock_through_composition_and_status(self, tmp_path):
        ports = RecordingPorts()
        events: list[str] = []

        @contextmanager
        def lock(path):
            events.append("lock-enter")
            yield
            canonical = tmp_path / "status" / "decision-refresh.json"
            assert JobStatus.model_validate_json(canonical.read_text()).outcome is JobOutcome.SUCCESS
            events.append("lock-exit")

        status = _run(tmp_path, ports, lock_factory=lock)

        assert events == ["lock-enter", "lock-exit"]
        assert ports.calls == ["sources", "card_coverage", "label", "staged_camps", "eras", "ranking"]
        assert status.outcome is JobOutcome.SUCCESS
        assert status.artifacts.ranking_written
        assert len(status.artifacts.ranking_sha256) == 64
        assert status.pending_actions == ("era alarm: possible unregistered change",)
        assert (tmp_path / "status" / "attempts" / "decision-refresh" / "attempt-1.json").exists()

    def test_degraded_refresh_is_successful_but_labeled(self, tmp_path):
        status = _run(tmp_path, RecordingPorts(degrade=True))
        assert status.outcome is JobOutcome.DEGRADED
        assert status.ok is True
        assert "sources: scan offline" in status.reason

    def test_required_failure_preserves_last_good_without_claiming_it(self, tmp_path):
        out = tmp_path / "ranking.html"
        out.write_text("last good", encoding="utf-8")
        status = _run(
            tmp_path,
            RecordingPorts(fail_at="label"),
            out_path=out,
        )
        assert status.outcome is JobOutcome.FAILED
        assert status.phase == "label"
        assert out.read_text() == "last good"
        assert not status.artifacts.ranking_written
        assert status.artifacts.ranking_sha256 is None

    def test_overlap_calls_no_ports_and_does_not_replace_canonical(self, tmp_path):
        ports = RecordingPorts()
        status_dir = tmp_path / "status"
        status_dir.mkdir()
        canonical = status_dir / "decision-refresh.json"
        canonical.write_text("owner", encoding="utf-8")

        def busy(path):
            raise LockUnavailable("busy owner")

        status = _run(tmp_path, ports, status_dir=status_dir, lock_factory=busy)
        assert status.outcome is JobOutcome.SKIPPED_OVERLAP
        assert ports.calls == []
        assert canonical.read_text() == "owner"
        assert (status_dir / "attempts" / "decision-refresh" / "attempt-1.json").exists()

    def test_missing_declared_ranking_becomes_wrapper_failure(self, tmp_path):
        ports = RecordingPorts()
        ports.write_ranking = lambda db_path, out_path: ports._record("ranking")
        status = _run(tmp_path, ports)
        assert status.outcome is JobOutcome.FAILED
        assert status.phase == "wrapper"
        assert "declared but missing" in status.reason

    def test_interrupt_records_failure_then_reraises(self, tmp_path):
        ports = RecordingPorts()
        ports.refresh_sources = lambda db_path: (_ for _ in ()).throw(KeyboardInterrupt())
        with pytest.raises(KeyboardInterrupt):
            _run(tmp_path, ports)
        canonical = JobStatus.model_validate_json(
            (tmp_path / "status" / "decision-refresh.json").read_text()
        )
        assert canonical.outcome is JobOutcome.FAILED
        assert canonical.reason == "KeyboardInterrupt"

    def test_sigterm_records_failure_then_exits(self, tmp_path):
        ports = RecordingPorts()

        def terminate_during_refresh(db_path):
            signal.raise_signal(signal.SIGTERM)

        ports.refresh_sources = terminate_during_refresh
        with pytest.raises(SystemExit) as raised:
            _run(tmp_path, ports)
        assert raised.value.code == 128 + signal.SIGTERM
        canonical = JobStatus.model_validate_json(
            (tmp_path / "status" / "decision-refresh.json").read_text()
        )
        assert canonical.outcome is JobOutcome.FAILED
        assert canonical.reason == "SystemExit"

    def test_monitor_runs_under_same_lock_and_unavailable_degrades_not_fails(self, tmp_path):
        ports = RecordingPorts()
        events = []

        class MonitorPorts:
            def oracle_rows(self):
                events.append("monitor")
                raise RuntimeError("bulk offline")

            def fetch_wotc(self, url):
                raise FileNotFoundError(url)

        @contextmanager
        def lock(path):
            events.append("lock-enter")
            yield
            events.append("lock-exit")

        state_path = tmp_path / "state" / "format-monitor.json"
        status = _run(
            tmp_path, ports, lock_factory=lock,
            format_monitor_ports=MonitorPorts(),
            format_monitor_state_path=state_path,
        )
        assert events == ["lock-enter", "monitor", "lock-exit"]
        assert status.outcome is JobOutcome.DEGRADED
        assert status.artifacts.ranking_written
        assert status.format_monitor.wotc == "unavailable"
        assert any("format monitor unavailable" in item for item in status.pending_actions)

    def test_sigterm_during_monitor_terminalizes_status_then_exits(self, tmp_path):
        ports = RecordingPorts()

        class MonitorPorts:
            def oracle_rows(self):
                signal.raise_signal(signal.SIGTERM)
            def fetch_wotc(self, url):
                raise AssertionError("unreachable")

        with pytest.raises(SystemExit):
            _run(
                tmp_path, ports, format_monitor_ports=MonitorPorts(),
                format_monitor_state_path=tmp_path / "state.json",
            )
        canonical = JobStatus.model_validate_json(
            (tmp_path / "status" / "decision-refresh.json").read_text()
        )
        assert canonical.outcome is JobOutcome.FAILED
        assert canonical.reason == "SystemExit"

    def test_monitor_candidate_projects_to_pending_action(self, tmp_path):
        ports = RecordingPorts()
        ports.refresh_sources = lambda db_path: SourceRefreshResult(
            new_card_names=frozenset({"New Card"}),
            recent_release_records=(SetRelease(
                code="eoe", name="Edge of Eternities", released_at=NOW.date(),
            ),),
            summary="sources current",
        )

        class MonitorPorts:
            def oracle_rows(self):
                return [{
                    "oracle_id": "one", "name": "Card",
                    "legalities": {"legacy": "legal"},
                }]

            def fetch_wotc(self, url):
                return (
                    "<p>Changes effective as of August 11, 2026.</p>"
                    "<h2>Legacy</h2><p>No changes.</p>"
                    "<h2>Vintage</h2><p>No changes.</p>"
                    "<p>Next announcement: October 12, 2026.</p>"
                ), url

        status = _run(
            tmp_path, ports,
            format_monitor_ports=MonitorPorts(),
            format_monitor_state_path=tmp_path / "state.json",
        )
        assert status.outcome is JobOutcome.SUCCESS
        assert status.format_monitor.candidate_count == 1
        assert any("review new release evidence" in item for item in status.pending_actions)

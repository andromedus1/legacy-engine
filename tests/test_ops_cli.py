from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.ops.status import (
    ArtifactIdentity,
    JobOutcome,
    JobStatus,
    write_job_status,
)


NOW = datetime.now(timezone.utc)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _status(tmp_path: Path, **changes) -> JobStatus:
    values = {
        "job": "decision-refresh",
        "attempt_id": "cli-attempt",
        "pid": 42,
        "started_at": NOW,
        "finished_at": NOW,
        "outcome": JobOutcome.SUCCESS,
        "ok": True,
        "phase": "complete",
        "summary": "completed",
        "artifacts": ArtifactIdentity(
            db_path=str(tmp_path / "test.duckdb"),
            ranking_path=str(tmp_path / "ranking.html"),
            ranking_written=True,
            ranking_sha256="abc123",
        ),
    }
    values.update(changes)
    return JobStatus(**values)


class TestOpsStatusCli:
    def test_ops_help_lists_status_refresh_and_scheduler(self, runner):
        result = runner.invoke(main, ["ops", "--help"])
        assert result.exit_code == 0
        assert "scheduled-refresh" in result.output
        assert "status" in result.output
        assert "scheduler" in result.output

    def test_status_uses_explicit_temp_directory(self, runner, tmp_path):
        status_dir = tmp_path / "status"
        write_job_status(status_dir / "decision-refresh.json", _status(tmp_path))
        result = runner.invoke(main, ["ops", "status", "--status-dir", str(status_dir)])
        assert result.exit_code == 0
        assert "scheduled refresh: healthy" in result.output
        assert str(tmp_path / "test.duckdb") in result.output

    def test_missing_status_is_explicit_and_safe(self, runner, tmp_path):
        result = runner.invoke(
            main, ["ops", "status", "--brief", "--status-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "scheduled refresh: missing" in result.output
        assert "no status record" in result.output

    def test_session_script_matches_cli_brief(self, runner, tmp_path):
        status_dir = tmp_path / "status"
        write_job_status(status_dir / "decision-refresh.json", _status(
            tmp_path,
            outcome=JobOutcome.FAILED,
            ok=False,
            reason="label broke",
        ))
        cli_result = runner.invoke(
            main, ["ops", "status", "--brief", "--status-dir", str(status_dir)]
        )
        script_result = subprocess.run(
            [sys.executable, "scripts/session_ops_status.py", "--status-dir", str(status_dir)],
            cwd=Path(__file__).parent.parent,
            check=True,
            text=True,
            capture_output=True,
        )
        assert script_result.stdout.strip() == cli_result.output.strip()


class TestScheduledRefreshCli:
    @pytest.mark.parametrize(
        ("outcome", "exit_code"),
        [
            (JobOutcome.SUCCESS, 0),
            (JobOutcome.DEGRADED, 0),
            (JobOutcome.FAILED, 1),
            (JobOutcome.SKIPPED_OVERLAP, 75),
        ],
    )
    def test_exit_contract_without_live_database(
        self, runner, tmp_path, monkeypatch, outcome, exit_code,
    ):
        status_dir = tmp_path / "status"
        status = _status(
            tmp_path,
            outcome=outcome,
            ok=outcome in {JobOutcome.SUCCESS, JobOutcome.DEGRADED},
            reason="busy" if outcome is JobOutcome.SKIPPED_OVERLAP else None,
        )

        def fake_run(ports, **kwargs):
            if outcome is not JobOutcome.SKIPPED_OVERLAP:
                write_job_status(status_dir / "decision-refresh.json", status)
            return status

        monkeypatch.setattr(
            "legacy_engine.ops.scheduled_refresh.run_scheduled_decision_refresh",
            fake_run,
        )
        result = runner.invoke(main, [
            "ops", "scheduled-refresh",
            "--db", str(tmp_path / "test.duckdb"),
            "--out", str(tmp_path / "ranking.html"),
            "--status-dir", str(status_dir),
        ])
        assert result.exit_code == exit_code, result.output
        assert outcome.value in result.output or "healthy" in result.output

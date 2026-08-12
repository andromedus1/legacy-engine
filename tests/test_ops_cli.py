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
from legacy_engine.ops.launchd import CommandResult


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
    def test_status_override_does_not_change_artifact_lock(self, runner, tmp_path, monkeypatch):
        captured = []
        status = _status(tmp_path)

        def fake_run(ports, **kwargs):
            captured.append(kwargs["lock_path"])
            write_job_status(kwargs["status_dir"] / "decision-refresh.json", status)
            return status

        monkeypatch.setattr(
            "legacy_engine.ops.scheduled_refresh.run_scheduled_decision_refresh", fake_run,
        )
        common = ["--db", str(tmp_path / "db.duckdb"), "--out", str(tmp_path / "ranking.html")]
        for name in ("status-a", "status-b"):
            result = runner.invoke(main, [
                "ops", "scheduled-refresh", *common, "--status-dir", str(tmp_path / name),
            ])
            assert result.exit_code == 0, result.output
        assert captured[0] == captured[1]

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


class TestSchedulerCli:
    def test_scheduler_help_lists_lifecycle(self, runner):
        result = runner.invoke(main, ["ops", "scheduler", "--help"])
        assert result.exit_code == 0
        for command in ("install", "inspect", "run-now", "uninstall"):
            assert command in result.output

    @pytest.mark.parametrize("command", ["install", "inspect", "run-now", "uninstall"])
    def test_scheduler_verbs_use_injected_launchctl_and_temp_paths(
        self, runner, tmp_path, monkeypatch, command,
    ):
        repo = tmp_path / "repo"
        python = repo / ".venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.touch()
        agents = tmp_path / "LaunchAgents"
        calls: list[tuple[str, ...]] = []

        class FakeProcess:
            def run(self, *args):
                calls.append(args)
                if args[0] == "print":
                    return CommandResult(returncode=113, stderr="Could not find service")
                return CommandResult(returncode=0)

        monkeypatch.setattr(
            "legacy_engine.ops.launchd.SubprocessLaunchctl",
            lambda: FakeProcess(),
        )
        result = runner.invoke(main, [
            "ops", "scheduler", command,
            "--repo-root", str(repo),
            "--launch-agents-dir", str(agents),
            "--uid", "501",
        ])
        assert result.exit_code == 0, result.output
        assert str(agents / "com.legacy-engine.refresh.plist") in result.output
        assert "daily 07:30 local" in result.output
        if command == "install":
            assert calls[-1][0] == "bootstrap"
        elif command == "inspect":
            assert calls == [("print", "gui/501/com.legacy-engine.refresh")]
        elif command == "run-now":
            assert calls == [("kickstart", "gui/501/com.legacy-engine.refresh")]
        else:
            assert calls == []  # already absent is idempotent; no real bootout

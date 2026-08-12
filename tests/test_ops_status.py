from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

from legacy_engine.ops.status import (
    ArtifactIdentity,
    JobHealth,
    JobOutcome,
    JobStatus,
    job_status_audit_lines,
    read_job_status,
    write_attempt_status,
    write_job_status,
)


NOW = datetime(2026, 8, 11, 18, 0, tzinfo=timezone.utc)


def _status(**changes) -> JobStatus:
    values = {
        "job": "decision-refresh",
        "attempt_id": "attempt-1",
        "pid": 42,
        "started_at": NOW - timedelta(minutes=5),
        "finished_at": NOW,
        "outcome": JobOutcome.SUCCESS,
        "ok": True,
        "phase": "complete",
        "summary": "completed",
        "artifacts": ArtifactIdentity(
            db_path="/tmp/db.duckdb",
            ranking_path="/tmp/ranking.html",
            ranking_written=True,
            ranking_sha256="abc123",
        ),
    }
    values.update(changes)
    return JobStatus(**values)


class TestStatusPersistence:
    def test_round_trip_preserves_status_contract(self, tmp_path):
        path = tmp_path / "status.json"
        original = _status(pending_actions=("confirm ban",))

        write_job_status(path, original)

        view = read_job_status(path, now=NOW)
        assert view.health is JobHealth.DEGRADED
        assert view.status == original

    def test_failed_replace_preserves_previous_record(self, tmp_path, monkeypatch):
        path = tmp_path / "status.json"
        write_job_status(path, _status(summary="old"))
        old_payload = path.read_text()

        def fail_replace(source, destination):
            raise OSError("disk refused replace")

        monkeypatch.setattr(os, "replace", fail_replace)
        with pytest.raises(OSError, match="disk refused"):
            write_job_status(path, _status(summary="new"))

        assert path.read_text() == old_payload
        assert list(tmp_path.glob("*.tmp")) == []

    def test_attempt_records_are_immutable(self, tmp_path):
        status = _status()
        path = write_attempt_status(tmp_path, status)
        assert path.name == "attempt-1.json"

        with pytest.raises(FileExistsError):
            write_attempt_status(tmp_path, status)


class TestStatusHealth:
    @pytest.mark.parametrize(
        ("status", "age", "health"),
        [
            (_status(), timedelta(hours=1), JobHealth.HEALTHY),
            (_status(outcome=JobOutcome.DEGRADED, reason="scan offline"), timedelta(hours=1), JobHealth.DEGRADED),
            (_status(outcome=JobOutcome.FAILED, ok=False, reason="label broke"), timedelta(hours=1), JobHealth.FAILED),
            (_status(outcome=JobOutcome.RUNNING, ok=None, finished_at=None), timedelta(hours=1), JobHealth.RUNNING),
            (_status(), timedelta(hours=37), JobHealth.STALE),
            (_status(outcome=JobOutcome.RUNNING, ok=None, finished_at=None), timedelta(hours=37), JobHealth.STALE),
        ],
    )
    def test_classifies_terminal_running_and_stale(self, tmp_path, status, age, health):
        reference = NOW - age
        status = status.model_copy(update={
            "started_at": reference,
            "finished_at": None if status.outcome is JobOutcome.RUNNING else reference,
        })
        path = tmp_path / "status.json"
        write_job_status(path, status)

        assert read_job_status(path, now=NOW).health is health

    def test_missing_and_malformed_are_not_healthy(self, tmp_path):
        path = tmp_path / "status.json"
        assert read_job_status(path, now=NOW).health is JobHealth.MISSING
        path.write_text("{bad json")
        assert read_job_status(path, now=NOW).health is JobHealth.INVALID

    def test_terminal_without_finished_at_is_invalid(self, tmp_path):
        path = tmp_path / "status.json"
        write_job_status(path, _status(finished_at=None))
        view = read_job_status(path, now=NOW)
        assert view.health is JobHealth.INVALID
        assert "no finished_at" in view.reason

    def test_naive_timestamp_is_rejected(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            _status(started_at=NOW.replace(tzinfo=None))


class TestStatusAuditLines:
    def test_healthy_full_output_carries_artifact_identity(self, tmp_path):
        path = tmp_path / "status.json"
        write_job_status(path, _status())
        lines = job_status_audit_lines(read_job_status(path, now=NOW))
        assert lines[0].startswith("// scheduled refresh: healthy")
        assert "attempt-1" in lines[1]
        assert "sha256=abc123" in lines[3]

    def test_unhealthy_brief_output_names_reason(self, tmp_path):
        path = tmp_path / "status.json"
        write_job_status(path, _status(
            outcome=JobOutcome.FAILED,
            ok=False,
            reason="label broke",
        ))
        lines = job_status_audit_lines(read_job_status(path, now=NOW), brief=True)
        assert len(lines) == 1
        assert lines[0].startswith("// ⚠ scheduled refresh: failed")
        assert "label broke" in lines[0]

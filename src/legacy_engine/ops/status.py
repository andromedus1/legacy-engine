"""Typed, atomic status records for local maintenance jobs."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator

from legacy_engine.models.base import LegacyEngineModel


class JobOutcome(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    DEGRADED = "degraded"
    FAILED = "failed"
    SKIPPED_OVERLAP = "skipped_overlap"


class ArtifactIdentity(LegacyEngineModel):
    db_path: str
    ranking_path: str
    ranking_written: bool
    ranking_sha256: str | None = None


class FormatMonitorSummary(LegacyEngineModel):
    legality: str
    wotc: str
    releases: str
    candidate_count: int = Field(ge=0)
    unavailable_reasons: tuple[str, ...] = ()


class JobStatus(LegacyEngineModel):
    schema_version: Literal[1] = 1
    job: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    attempt_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    pid: int = Field(ge=0)
    started_at: datetime
    finished_at: datetime | None = None
    outcome: JobOutcome
    ok: bool | None
    phase: str
    summary: str
    reason: str | None = None
    artifacts: ArtifactIdentity
    pending_actions: tuple[str, ...] = ()
    format_monitor: FormatMonitorSummary | None = None

    @field_validator("started_at", "finished_at")
    @classmethod
    def _timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("job status timestamps must be timezone-aware")
        return value


class JobHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    STALE = "stale"
    RUNNING = "running"
    MISSING = "missing"
    INVALID = "invalid"


class JobStatusView(LegacyEngineModel):
    health: JobHealth
    status: JobStatus | None = None
    reason: str


def write_job_status(path: Path, status: JobStatus) -> None:
    """Atomically replace one status record without exposing partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = status.model_dump_json(indent=2) + "\n"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def write_attempt_status(status_dir: Path, status: JobStatus) -> Path:
    """Write the immutable evidence record for one completed attempt."""
    path = status_dir / "attempts" / status.job / f"{status.attempt_id}.json"
    if path.exists():
        raise FileExistsError(f"attempt status already exists: {path}")
    write_job_status(path, status)
    return path


def read_job_status(
    path: Path,
    *,
    now: datetime,
    stale_after: timedelta = timedelta(hours=36),
) -> JobStatusView:
    """Read canonical status and classify its operator-visible health."""
    if not path.exists():
        return JobStatusView(
            health=JobHealth.MISSING,
            reason=f"no status record at {path}",
        )
    try:
        status = JobStatus.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        return JobStatusView(
            health=JobHealth.INVALID,
            reason=f"invalid status record at {path}: {exc}",
        )

    if now.utcoffset() is None:
        raise ValueError("status comparison clock must be timezone-aware")

    reference = status.finished_at or status.started_at
    age = now - reference
    if age < timedelta(minutes=-5):
        return JobStatusView(
            health=JobHealth.INVALID,
            status=status,
            reason=f"status timestamp is in the future: {reference.isoformat()}",
        )
    if age > stale_after:
        detail = "running record appears stuck" if status.outcome is JobOutcome.RUNNING else "last terminal run is stale"
        return JobStatusView(
            health=JobHealth.STALE,
            status=status,
            reason=f"{detail}; last evidence {reference.isoformat()}",
        )
    if status.outcome is JobOutcome.RUNNING:
        return JobStatusView(
            health=JobHealth.RUNNING,
            status=status,
            reason=f"run active since {status.started_at.isoformat()}",
        )
    if status.finished_at is None:
        return JobStatusView(
            health=JobHealth.INVALID,
            status=status,
            reason=f"terminal outcome {status.outcome.value} has no finished_at",
        )
    if status.outcome in {JobOutcome.FAILED, JobOutcome.SKIPPED_OVERLAP}:
        return JobStatusView(
            health=JobHealth.FAILED,
            status=status,
            reason=status.reason or status.summary,
        )
    if status.outcome is JobOutcome.DEGRADED or status.pending_actions:
        reason = status.reason or (
            f"{len(status.pending_actions)} pending operator action(s)"
        )
        return JobStatusView(health=JobHealth.DEGRADED, status=status, reason=reason)
    return JobStatusView(
        health=JobHealth.HEALTHY,
        status=status,
        reason=status.summary,
    )


def job_status_audit_lines(
    view: JobStatusView,
    *,
    brief: bool = False,
) -> tuple[str, ...]:
    """Render status as machine-scannable audit comment lines."""
    warning = view.health not in {JobHealth.HEALTHY, JobHealth.RUNNING}
    prefix = "// ⚠" if warning else "//"
    status = view.status
    when = ""
    if status is not None:
        stamp = status.finished_at or status.started_at
        when = f" at {stamp.isoformat()}"
    head = f"{prefix} scheduled refresh: {view.health.value}{when} — {view.reason}"
    if status is not None and status.format_monitor is not None:
        monitor = status.format_monitor
        head += (
            f"; format monitor legality={monitor.legality}, wotc={monitor.wotc}, "
            f"releases={monitor.releases}, candidates={monitor.candidate_count}"
        )
    if brief or status is None:
        return (head,)

    lines = [
        head,
        f"// attempt: {status.attempt_id} (pid={status.pid}, phase={status.phase})",
        f"// database: {status.artifacts.db_path}",
    ]
    ranking = status.artifacts
    if ranking.ranking_written:
        lines.append(
            f"// ranking: {ranking.ranking_path} (sha256={ranking.ranking_sha256})"
        )
    else:
        lines.append(f"// ranking: not written ({ranking.ranking_path})")
    if status.format_monitor is not None:
        monitor = status.format_monitor
        lines.append(
            f"// format monitor: legality={monitor.legality}, wotc={monitor.wotc}, "
            f"releases={monitor.releases}, candidates={monitor.candidate_count}"
        )
        lines.extend(
            f"// ⚠ format monitor unavailable: {reason}"
            for reason in monitor.unavailable_reasons
        )
    lines.extend(f"// ⚠ pending action: {action}" for action in status.pending_actions)
    return tuple(lines)

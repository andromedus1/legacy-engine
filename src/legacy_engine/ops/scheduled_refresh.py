"""Exclusive local runner for the existing decision-data refresh workflow."""

from __future__ import annotations

import fcntl
import hashlib
from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Protocol

from legacy_engine.ops.status import (
    ArtifactIdentity,
    JobOutcome,
    JobStatus,
    write_attempt_status,
    write_job_status,
)
from legacy_engine.workflows.decision_refresh import (
    DecisionRefreshPorts,
    RefreshStepStatus,
    run_decision_refresh,
)


JOB_NAME = "decision-refresh"


class LockUnavailable(RuntimeError):
    """Raised when another decision refresh owns the execution lock."""


class Clock(Protocol):
    def __call__(self) -> datetime: ...


@contextmanager
def exclusive_file_lock(path: Path):
    """Acquire a process-scoped non-blocking kernel lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LockUnavailable(f"refresh already running; lock busy: {path}") from exc
        yield
    finally:
        handle.close()


def _artifacts(db_path: Path, out_path: Path, *, ranking_written: bool) -> ArtifactIdentity:
    digest = None
    if ranking_written:
        if not out_path.is_file():
            raise FileNotFoundError(f"ranking output declared but missing: {out_path}")
        hasher = hashlib.sha256()
        with out_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
    return ArtifactIdentity(
        db_path=str(db_path.resolve()),
        ranking_path=str(out_path.resolve()),
        ranking_written=ranking_written,
        ranking_sha256=digest,
    )


def _base_status(
    *,
    attempt_id: str,
    pid: int,
    started_at: datetime,
    outcome: JobOutcome,
    ok: bool | None,
    phase: str,
    summary: str,
    artifacts: ArtifactIdentity,
    finished_at: datetime | None = None,
    reason: str | None = None,
    pending_actions: tuple[str, ...] = (),
) -> JobStatus:
    return JobStatus(
        job=JOB_NAME,
        attempt_id=attempt_id,
        pid=pid,
        started_at=started_at,
        finished_at=finished_at,
        outcome=outcome,
        ok=ok,
        phase=phase,
        summary=summary,
        reason=reason,
        artifacts=artifacts,
        pending_actions=pending_actions,
    )


def run_scheduled_decision_refresh(
    ports: DecisionRefreshPorts,
    *,
    db_path: Path,
    out_path: Path,
    status_dir: Path,
    lock_path: Path,
    clock: Clock,
    attempt_id_factory: Callable[[], str],
    pid: int,
    lock_factory: Callable[[Path], AbstractContextManager[None]] = exclusive_file_lock,
) -> JobStatus:
    """Run the production composition once and persist attributable status."""
    started_at = clock()
    attempt_id = attempt_id_factory()
    canonical_path = status_dir / f"{JOB_NAME}.json"
    empty_artifacts = _artifacts(db_path, out_path, ranking_written=False)

    try:
        lock_context = lock_factory(lock_path)
        with lock_context:
            running = _base_status(
                attempt_id=attempt_id,
                pid=pid,
                started_at=started_at,
                outcome=JobOutcome.RUNNING,
                ok=None,
                phase="starting",
                summary="decision-data refresh in progress",
                artifacts=empty_artifacts,
            )
            write_job_status(canonical_path, running)
            try:
                result = run_decision_refresh(ports, db_path=db_path, out_path=out_path)
                failed = next(
                    (step for step in result.steps if step.status is RefreshStepStatus.FAILED),
                    None,
                )
                degraded = tuple(
                    step for step in result.steps
                    if step.status is RefreshStepStatus.DEGRADED
                )
                if failed is not None:
                    outcome = JobOutcome.FAILED
                    ok = False
                    phase = failed.name
                    reason = failed.reason or failed.summary
                    summary = f"decision-data refresh failed at {failed.name}"
                elif degraded:
                    outcome = JobOutcome.DEGRADED
                    ok = True
                    phase = "complete"
                    reason = "; ".join(
                        f"{step.name}: {step.reason or step.summary}" for step in degraded
                    )
                    summary = f"decision-data refresh completed with {len(degraded)} degraded step(s)"
                else:
                    outcome = JobOutcome.SUCCESS
                    ok = True
                    phase = "complete"
                    reason = None
                    summary = "decision-data refresh completed"
                artifacts = _artifacts(
                    db_path,
                    out_path,
                    ranking_written=result.ranking_output is not None,
                )
                pending = tuple(
                    f"era alarm: {alarm}" for alarm in result.format_awareness.era_alarms
                )
                terminal = _base_status(
                    attempt_id=attempt_id,
                    pid=pid,
                    started_at=started_at,
                    finished_at=clock(),
                    outcome=outcome,
                    ok=ok,
                    phase=phase,
                    summary=summary,
                    reason=reason,
                    artifacts=artifacts,
                    pending_actions=pending,
                )
            except (KeyboardInterrupt, SystemExit) as exc:
                terminal = _base_status(
                    attempt_id=attempt_id,
                    pid=pid,
                    started_at=started_at,
                    finished_at=clock(),
                    outcome=JobOutcome.FAILED,
                    ok=False,
                    phase="wrapper",
                    summary="decision-data refresh interrupted",
                    reason=type(exc).__name__,
                    artifacts=empty_artifacts,
                )
                write_job_status(canonical_path, terminal)
                write_attempt_status(status_dir, terminal)
                raise
            except Exception as exc:
                terminal = _base_status(
                    attempt_id=attempt_id,
                    pid=pid,
                    started_at=started_at,
                    finished_at=clock(),
                    outcome=JobOutcome.FAILED,
                    ok=False,
                    phase="wrapper",
                    summary="decision-data refresh wrapper failed",
                    reason=str(exc),
                    artifacts=empty_artifacts,
                )
            write_job_status(canonical_path, terminal)
            write_attempt_status(status_dir, terminal)
            return terminal
    except LockUnavailable as exc:
        overlap = _base_status(
            attempt_id=attempt_id,
            pid=pid,
            started_at=started_at,
            finished_at=clock(),
            outcome=JobOutcome.SKIPPED_OVERLAP,
            ok=False,
            phase="lock",
            summary="scheduled refresh skipped because another run owns the lock",
            reason=str(exc),
            artifacts=empty_artifacts,
        )
        write_attempt_status(status_dir, overlap)
        return overlap

"""Exclusive local runner for the existing decision-data refresh workflow."""

from __future__ import annotations

import fcntl
import hashlib
import signal
from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Protocol

from legacy_engine.ops.status import (
    ArtifactIdentity,
    FormatCandidateSummary,
    FormatMonitorSummary,
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


def decision_refresh_lock_path(db_path: Path, out_path: Path, *, lock_dir: Path) -> Path:
    """Return the shared lock identity for one protected artifact pair."""
    identity = f"{db_path.resolve()}\0{out_path.resolve()}".encode()
    digest = hashlib.sha256(identity).hexdigest()[:16]
    return lock_dir / f"{JOB_NAME}-{digest}.lock"


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


@contextmanager
def _terminal_signal_as_exit():
    """Turn launchd's SIGTERM into a catchable exit while this run owns the lock."""
    previous = signal.getsignal(signal.SIGTERM)

    def terminate(signum, frame):
        raise SystemExit(128 + signum)

    try:
        signal.signal(signal.SIGTERM, terminate)
    except ValueError:  # Signal handlers are available only in the main interpreter thread.
        yield
        return
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def _artifacts(
    db_path: Path,
    out_path: Path,
    *,
    ranking_written: bool,
    ranking_utility: dict[str, object] | None = None,
) -> ArtifactIdentity:
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
        ranking_utility=ranking_utility,
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
    format_monitor: FormatMonitorSummary | None = None,
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
        format_monitor=format_monitor,
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
    format_monitor_ports=None,
    format_monitor_state_path: Path | None = None,
) -> JobStatus:
    """Run the production composition once and persist attributable status."""
    started_at = clock()
    attempt_id = attempt_id_factory()
    canonical_path = status_dir / f"{JOB_NAME}.json"
    empty_artifacts = _artifacts(db_path, out_path, ranking_written=False)

    try:
        lock_context = lock_factory(lock_path)
        with lock_context, _terminal_signal_as_exit():
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
                    ranking_utility=(
                        result.ranking_utility.model_dump(mode="json")
                        if result.ranking_utility is not None else None
                    ),
                )
                pending = tuple(
                    f"era alarm: {alarm}" for alarm in result.format_awareness.era_alarms
                )
                monitor_summary = None
                if (format_monitor_ports is None) != (format_monitor_state_path is None):
                    raise ValueError(
                        "format_monitor_ports and format_monitor_state_path must be supplied together"
                    )
                if format_monitor_ports is not None and format_monitor_state_path is not None:
                    try:
                        from legacy_engine.ingestion.banlist import BAN_EVENTS
                        from legacy_engine.ingestion.releases import ReleaseScan
                        from legacy_engine.ops.format_monitor import run_format_monitor

                        source = result.source_observation
                        if source is None:
                            raise ValueError("decision refresh produced no source observation")
                        monitor = run_format_monitor(
                            format_monitor_ports,
                            state_path=format_monitor_state_path,
                            observed_at=clock(),
                            release_scan=(
                                None if source.release_scan_reason is not None else ReleaseScan(
                                    upcoming=list(source.upcoming_release_records),
                                    recently_released=list(source.recent_release_records),
                                    scanned_at=started_at.date(),
                                )
                            ),
                            release_scan_reason=source.release_scan_reason,
                            new_card_names=tuple(sorted(source.new_card_names)),
                            registered_events=BAN_EVENTS,
                        )
                        monitor_summary = FormatMonitorSummary(
                            legality=monitor.legality_state.value,
                            wotc=monitor.wotc_state.value,
                            releases=monitor.release_state.value,
                            candidate_count=len(monitor.candidates),
                            candidates=tuple(
                                FormatCandidateSummary(
                                    candidate_id=item.candidate_id,
                                    kind=item.kind,
                                    disposition=item.disposition.value,
                                    subject_name=item.subject_name,
                                )
                                for item in monitor.candidates
                            ),
                            unavailable_reasons=monitor.unavailable_reasons,
                        )
                        pending = tuple(dict.fromkeys((*pending, *monitor.pending_actions)))
                        if monitor.unavailable_reasons and outcome is JobOutcome.SUCCESS:
                            outcome = JobOutcome.DEGRADED
                            reason = "; ".join(monitor.unavailable_reasons)
                            summary = "decision-data refresh completed; format monitor unavailable"
                    except Exception as exc:
                        monitor_summary = FormatMonitorSummary(
                            legality="unavailable", wotc="unavailable", releases="unavailable",
                            candidate_count=0, unavailable_reasons=(str(exc),),
                        )
                        pending = tuple(dict.fromkeys((
                            *pending, f"format monitor unavailable: {exc}",
                        )))
                        if outcome is JobOutcome.SUCCESS:
                            outcome = JobOutcome.DEGRADED
                            reason = f"format monitor unavailable: {exc}"
                            summary = "decision-data refresh completed; format monitor unavailable"
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
                    format_monitor=monitor_summary,
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

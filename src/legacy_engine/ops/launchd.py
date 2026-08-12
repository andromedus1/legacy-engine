"""Hermetic rendering and reversible control of the local refresh LaunchAgent."""

from __future__ import annotations

import os
import plistlib
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from pydantic import Field

from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.ops.scheduled_refresh import (
    LockUnavailable,
    decision_refresh_lock_path,
    exclusive_file_lock,
)


REFRESH_AGENT_LABEL = "com.legacy-engine.refresh"


class CommandResult(LegacyEngineModel):
    returncode: int
    stdout: str = ""
    stderr: str = ""


class LaunchctlPort(Protocol):
    def run(self, *args: str) -> CommandResult: ...


class SubprocessLaunchctl:
    def run(self, *args: str) -> CommandResult:
        completed = subprocess.run(
            ("launchctl", *args),
            check=False,
            text=True,
            capture_output=True,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


class LaunchAgentSpec(LegacyEngineModel):
    label: str
    domain_target: str
    plist_path: Path
    python_path: Path
    repo_root: Path
    stdout_path: Path
    stderr_path: Path
    lock_path: Path
    hour: int = Field(default=7, ge=0, le=23)
    minute: int = Field(default=30, ge=0, le=59)


class LaunchAgentState(LegacyEngineModel):
    ok: bool
    installed: bool
    loaded: bool
    plist_path: Path
    detail: str


def build_refresh_launch_agent_spec(
    *,
    repo_root: Path,
    launch_agents_dir: Path,
    uid: int,
) -> LaunchAgentSpec:
    root = repo_root.resolve()
    return LaunchAgentSpec(
        label=REFRESH_AGENT_LABEL,
        domain_target=f"gui/{uid}",
        plist_path=launch_agents_dir.resolve() / f"{REFRESH_AGENT_LABEL}.plist",
        python_path=root / ".venv" / "bin" / "python",
        repo_root=root,
        stdout_path=root / "data" / "ops" / "logs" / "refresh.out.log",
        stderr_path=root / "data" / "ops" / "logs" / "refresh.err.log",
        lock_path=decision_refresh_lock_path(
            root / "data" / "legacy.duckdb",
            root / "decks" / "best-deck-best-call-ranking.html",
            lock_dir=root / "data" / "ops" / "locks",
        ),
    )


def _validate_spec(spec: LaunchAgentSpec) -> None:
    paths = (
        spec.plist_path,
        spec.python_path,
        spec.repo_root,
        spec.stdout_path,
        spec.stderr_path,
        spec.lock_path,
    )
    if any(not path.is_absolute() for path in paths):
        raise ValueError("LaunchAgent paths must be absolute")
    if spec.label != REFRESH_AGENT_LABEL:
        raise ValueError(f"unexpected LaunchAgent label: {spec.label}")
    if not spec.domain_target.startswith("gui/"):
        raise ValueError(f"LaunchAgent must target a gui domain: {spec.domain_target}")
    if not spec.repo_root.is_dir():
        raise ValueError(f"repository root does not exist: {spec.repo_root}")
    if not spec.python_path.is_file():
        raise ValueError(f"virtualenv Python does not exist: {spec.python_path}")


def render_launch_agent_plist(spec: LaunchAgentSpec) -> bytes:
    _validate_spec(spec)
    payload = {
        "Label": spec.label,
        "ProgramArguments": [
            str(spec.python_path),
            "-m",
            "legacy_engine.cli",
            "ops",
            "scheduled-refresh",
        ],
        "WorkingDirectory": str(spec.repo_root),
        "StartCalendarInterval": {"Hour": spec.hour, "Minute": spec.minute},
        "StandardOutPath": str(spec.stdout_path),
        "StandardErrorPath": str(spec.stderr_path),
    }
    return plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)


def _target(spec: LaunchAgentSpec) -> str:
    return f"{spec.domain_target}/{spec.label}"


def _detail(result: CommandResult) -> str:
    return (result.stderr or result.stdout).strip() or f"launchctl exited {result.returncode}"


def _not_loaded(result: CommandResult) -> bool:
    detail = f"{result.stderr}\n{result.stdout}".lower()
    return "could not find service" in detail or "no such process" in detail


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def inspect_launch_agent(
    spec: LaunchAgentSpec,
    launchctl: LaunchctlPort,
) -> LaunchAgentState:
    result = launchctl.run("print", _target(spec))
    loaded = result.returncode == 0
    detail = "loaded" if loaded else _detail(result)
    return LaunchAgentState(
        ok=loaded or _not_loaded(result),
        installed=spec.plist_path.is_file(),
        loaded=loaded,
        plist_path=spec.plist_path,
        detail=detail,
    )


def install_launch_agent(
    spec: LaunchAgentSpec,
    launchctl: LaunchctlPort,
) -> LaunchAgentState:
    candidate = render_launch_agent_plist(spec)
    try:
        with exclusive_file_lock(spec.lock_path):
            previous = spec.plist_path.read_bytes() if spec.plist_path.is_file() else None
            prior = inspect_launch_agent(spec, launchctl)
            if not prior.ok:
                return prior.model_copy(update={"detail": f"cannot establish current state: {prior.detail}"})
            if previous == candidate and prior.loaded:
                return prior.model_copy(update={"ok": True, "detail": "already installed and loaded"})

            if prior.loaded:
                bootout = launchctl.run("bootout", spec.domain_target, str(spec.plist_path))
                if bootout.returncode != 0:
                    return LaunchAgentState(
                        ok=False, installed=previous is not None, loaded=True,
                        plist_path=spec.plist_path,
                        detail=f"bootout failed; existing agent preserved: {_detail(bootout)}",
                    )

            try:
                _atomic_write(spec.plist_path, candidate)
                spec.stdout_path.parent.mkdir(parents=True, exist_ok=True)
                bootstrap = launchctl.run("bootstrap", spec.domain_target, str(spec.plist_path))
                if bootstrap.returncode == 0:
                    return LaunchAgentState(
                        ok=True, installed=True, loaded=True, plist_path=spec.plist_path,
                        detail="installed and loaded",
                    )
                failure = f"bootstrap failed: {_detail(bootstrap)}"
            except Exception as exc:
                failure = f"install failed after bootout: {type(exc).__name__}: {exc}"

            rollback_details: list[str] = []
            if previous is None:
                spec.plist_path.unlink(missing_ok=True)
                rollback_details.append("removed failed candidate")
            else:
                try:
                    _atomic_write(spec.plist_path, previous)
                    rollback_details.append("restored previous plist")
                    if prior.loaded:
                        restored = launchctl.run("bootstrap", spec.domain_target, str(spec.plist_path))
                        if restored.returncode == 0:
                            rollback_details.append("reloaded previous agent")
                        else:
                            rollback_details.append(f"previous-agent reload failed: {_detail(restored)}")
                except Exception as exc:
                    rollback_details.append(f"rollback failed: {type(exc).__name__}: {exc}")
            return LaunchAgentState(
                ok=False,
                installed=spec.plist_path.is_file(),
                loaded=prior.loaded and "reloaded previous agent" in rollback_details,
                plist_path=spec.plist_path,
                detail=f"{failure}; {'; '.join(rollback_details)}",
            )
    except LockUnavailable as exc:
        return LaunchAgentState(
            ok=False, installed=spec.plist_path.is_file(), loaded=True,
            plist_path=spec.plist_path,
            detail=f"refresh is active; scheduler configuration preserved: {exc}",
        )


def run_launch_agent_now(
    spec: LaunchAgentSpec,
    launchctl: LaunchctlPort,
) -> LaunchAgentState:
    result = launchctl.run("kickstart", _target(spec))
    return LaunchAgentState(
        ok=result.returncode == 0,
        installed=spec.plist_path.is_file(),
        loaded=result.returncode == 0,
        plist_path=spec.plist_path,
        detail="kickstarted" if result.returncode == 0 else f"kickstart failed: {_detail(result)}",
    )


def uninstall_launch_agent(
    spec: LaunchAgentSpec,
    launchctl: LaunchctlPort,
) -> LaunchAgentState:
    if not spec.plist_path.exists():
        return LaunchAgentState(
            ok=True, installed=False, loaded=False, plist_path=spec.plist_path,
            detail="already uninstalled",
        )
    try:
        with exclusive_file_lock(spec.lock_path):
            bootout = launchctl.run("bootout", spec.domain_target, str(spec.plist_path))
            if bootout.returncode != 0 and not _not_loaded(bootout):
                return LaunchAgentState(
                    ok=False, installed=True, loaded=True, plist_path=spec.plist_path,
                    detail=f"bootout failed; plist preserved: {_detail(bootout)}",
                )
            spec.plist_path.unlink()
            return LaunchAgentState(
                ok=True, installed=False, loaded=False, plist_path=spec.plist_path,
                detail="unloaded and removed",
            )
    except LockUnavailable as exc:
        return LaunchAgentState(
            ok=False, installed=True, loaded=True, plist_path=spec.plist_path,
            detail=f"refresh is active; plist preserved: {exc}",
        )

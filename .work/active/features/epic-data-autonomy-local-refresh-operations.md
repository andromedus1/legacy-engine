---
id: epic-data-autonomy-local-refresh-operations
kind: feature
stage: done
tags: [ingestion, infra]
parent: epic-data-autonomy
depends_on: [feature-decision-data-currency]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Local scheduled decision-data refresh and operator status

## Brief

Turn the existing composed decision-data refresh into a reliable local operation on the
maintainer's Mac. Use launchd at the already-decided daily 07:30 local schedule, with no
`RunAtLoad`, and execute against the repository's local data and DuckDB through absolute paths.

The feature must preserve the composed refresh's fail-closed/degraded contracts, prevent
overlapping runs, and atomically write a typed status record on both success and failure. Provide
repeatable install, inspect, run-now, and uninstall controls plus concise log and session/CLI
visibility. Do not add cloud state, a second database, or a second-format deployment.

## Acceptance boundary

- The scheduler invokes the existing production composition instead of duplicating refresh logic.
- Concurrent invocations cannot corrupt or race decision artifacts.
- Every attempted run leaves attributable timestamps, outcome, phase/reason, and artifact identity.
- Installation and removal are explicit and reversible; tests use hermetic temporary paths rather
  than touching the operator's live LaunchAgent.

## Design decisions

- **Composition boundary**: the scheduled runner calls
  `workflows.decision_refresh.run_decision_refresh(DefaultDecisionRefreshPorts(), ...)` directly.
  It does not compose Click commands, shell strings, or a second refresh implementation. The
  existing `scripts/refresh_decision_data.py` remains a thin manual adapter over the same workflow.
- **Overlap behavior**: acquire one non-blocking `fcntl.flock` before any refresh mutation. A second
  invocation records an immutable `skipped_overlap` attempt, leaves the canonical status owned by
  the running invocation untouched, and exits with temporary-failure status. There is no stale-lock
  recovery protocol because the kernel releases `flock` when the process exits.
- **Status durability**: the lock-owning invocation atomically publishes a canonical
  `data/ops/status/decision-refresh.json` first as `running`, then as a terminal typed record. Every
  invocation also writes an immutable per-attempt record under
  `data/ops/status/attempts/decision-refresh/`. Writes use a same-directory temporary file,
  `fsync`, and `os.replace`; readers never observe partial JSON.
- **Outcome semantics**: `success` and `degraded` are successful process outcomes; `failed` and
  `skipped_overlap` are non-zero. Degradation preserves the composed workflow's existing meaning:
  advisory source gaps are named while the ranking may still refresh. A required failed step names
  its phase/reason and retains the last-good ranking.
- **Artifact identity**: each terminal record carries the resolved DuckDB path, ranking path,
  whether this attempt wrote the ranking, and the ranking SHA-256 when written. A preserved
  last-good file is never mislabeled as this attempt's output.
- **Freshness contract**: a daily job is stale after 36 hours without a terminal successful or
  degraded record. Missing, invalid, running-too-long, failed, and stale are distinct status views;
  none is rendered as a false clear.
- **Scheduler contract**: one user LaunchAgent named `com.legacy-engine.refresh` runs daily at 07:30
  local with `StartCalendarInterval`, absolute `.venv/bin/python` and repository paths,
  `WorkingDirectory`, and explicit stdout/stderr logs. `RunAtLoad`, `KeepAlive`, and
  `StartInterval` are omitted. Install/inspect/run-now/uninstall use the `gui/<uid>` domain.
- **Install safety**: an identical installed-and-loaded plist is a no-op. Reconfiguration validates
  the candidate before bootout, writes atomically, and restores/reloads the previous plist on a
  bootstrap failure when possible. Uninstall never deletes the plist if bootout fails.
- **Session visibility**: `legacy-engine ops status --brief` is the stable, no-network status
  surface. A tiny repository script plus the project session-orientation instruction invokes that
  same formatter when status exists; no harness-specific settings file becomes source of truth.
- **Scope guard**: this feature does not implement the B&R/release monitor, hot spare, vendor
  prices, cloud state, Modern, git commits/pushes, or generic multi-job scheduling. The sibling
  monitoring feature extends `pending_actions` additively.

## UI decision

No mockups. This adds operational `// ` audit lines to the existing Click CLI and a session-start
summary, not a new visual screen or flow.

## Architectural choice

Three shapes were considered. A shell wrapper plus a hand-authored plist is smallest, but it makes
exception-safe status, typed testing, and path validation depend on shell conventions. A generic
job registry/daemon could host future monitors, but it introduces a scheduler framework and durable
job abstraction before a second job exists. Choose a small typed `legacy_engine.ops` package: a
status/runner core, a launchd adapter, and thin Click/script consumers. This keeps the existing
decision-refresh workflow authoritative while isolating the real infrastructure boundaries
(filesystem locking, atomic persistence, clock, process id, and `launchctl`).

The trickiest unit is the lock/status transaction. The canonical record belongs only to the process
holding the execution lock; overlap attempts use immutable side records so they cannot overwrite an
in-progress or terminal owner record. The lock-owning process writes `running` after acquisition and
a terminal record in all expected success/degrade/failure paths. If the status filesystem itself is
unwritable, the command fails loudly to stderr and non-zero—there is no honest way to claim durable
observability in that condition.

## Implementation Units

### Unit 1: Typed status contract and atomic status repository

**Files**: `src/legacy_engine/config.py`, `src/legacy_engine/ops/__init__.py`,
`src/legacy_engine/ops/status.py`, `tests/test_ops_status.py`

**Story**: `epic-data-autonomy-local-refresh-operations-runner-status`

```python
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Literal

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

class JobStatus(LegacyEngineModel):
    schema_version: Literal[1] = 1
    job: str
    attempt_id: str
    pid: int
    started_at: datetime
    finished_at: datetime | None = None
    outcome: JobOutcome
    ok: bool | None
    phase: str
    summary: str
    reason: str | None = None
    artifacts: ArtifactIdentity
    pending_actions: tuple[str, ...] = ()

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

def write_job_status(path: Path, status: JobStatus) -> None: ...
def write_attempt_status(status_dir: Path, status: JobStatus) -> Path: ...
def read_job_status(
    path: Path, *, now: datetime, stale_after: timedelta = timedelta(hours=36),
) -> JobStatusView: ...
def job_status_audit_lines(view: JobStatusView, *, brief: bool = False) -> tuple[str, ...]: ...
```

**Implementation Notes**:

- Add constants only—no directory creation—to `config.py`: `OPS_DIR`, `OPS_STATUS_DIR`,
  `OPS_LOG_DIR`, and `OPS_LOCK_DIR` under `DATA_DIR`.
- Shared records subclass `LegacyEngineModel`; timestamps are timezone-aware UTC and JSON is a
  stable UTF-8 Pydantic dump with a trailing newline.
- Atomic writing creates parent directories at the I/O boundary, flushes and `fsync`s a temporary
  file in the destination directory, then `os.replace`s it. Best-effort cleanup removes only the
  exact temporary file created by that call.
- Parsing errors become `JobHealth.INVALID` with a named reason; they are never swallowed into
  `MISSING` or `HEALTHY`. A `running` record older than 36 hours is `STALE` with a stuck-run reason.
- All audit/status output follows the `// ` / `// ⚠` project pattern. Brief output is one line and
  never performs network or DuckDB work.

**Acceptance Criteria**:

- [ ] A reader never observes partial JSON during replacement, and a failed replacement preserves
      the previous canonical record.
- [ ] Round-trip parsing preserves attempt, outcome, phase/reason, pending actions, and artifact
      identity.
- [ ] Missing, malformed, failed, degraded, active, stuck-running, and stale-success records map to
      distinct, deterministic views using an injected clock.
- [ ] Every non-healthy view renders a named reason; no absent record renders as a successful run.

### Unit 2: Exclusive scheduled runner over the existing composition

**Files**: `src/legacy_engine/ops/scheduled_refresh.py`, `tests/test_scheduled_refresh.py`

**Story**: `epic-data-autonomy-local-refresh-operations-runner-status`

```python
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from typing import Protocol

from legacy_engine.workflows.decision_refresh import DecisionRefreshPorts

class LockUnavailable(RuntimeError): ...

class Clock(Protocol):
    def __call__(self) -> datetime: ...

def exclusive_file_lock(path: Path) -> AbstractContextManager[None]: ...

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
) -> JobStatus: ...
```

**Implementation Notes**:

- `exclusive_file_lock` opens one explicit lock file and calls
  `fcntl.flock(fd, LOCK_EX | LOCK_NB)` before any workflow call. It raises `LockUnavailable` on
  contention and always closes its own descriptor.
- The runner writes canonical `running` only after it owns the lock. It calls
  `run_decision_refresh(ports, db_path=..., out_path=...)` once, maps its typed step statuses to the
  terminal job outcome/phase/reason, hashes the ranking only when that result says it was written,
  publishes canonical terminal state, then writes the immutable terminal attempt record.
- Lock contention writes only an immutable `skipped_overlap` attempt. Unexpected exceptions around
  composition are converted to `failed` at phase `wrapper`; `KeyboardInterrupt`/`SystemExit` are not
  disguised as ordinary failures, but a `finally` best-effort terminal write records interruption
  before re-raising.
- Era alarms become `pending_actions`; release counts remain in the summary. The later format
  monitor may append attributable pending-action records without changing this runner contract.

**Acceptance Criteria**:

- [ ] The execution lock is acquired before the first fake-port call and held through final ranking
      write and terminal canonical status publication.
- [ ] A concurrent invocation makes zero decision-refresh port calls, preserves the owner's
      canonical status, and leaves a `skipped_overlap` attempt record.
- [ ] Success, degraded source, required-step failure, unexpected wrapper failure, and interruption
      each produce the specified outcome, phase/reason, process result, and immutable attempt.
- [ ] A failed refresh does not hash or claim the retained last-good ranking as newly written.

### Unit 3: Operator CLI and session-start projection

**Files**: `src/legacy_engine/cli.py`, `scripts/refresh_decision_data.py`,
`scripts/session_ops_status.py`, `AGENTS.md`, `tests/test_ops_cli.py`

**Story**: `epic-data-autonomy-local-refresh-operations-operator-cli`

```python
@main.group()
def ops() -> None: ...

@ops.command("scheduled-refresh")
def ops_scheduled_refresh(
    db: str | None, out: str | None, status_dir: str | None, verbose: bool,
) -> None: ...

@ops.command("status")
def ops_status(status_dir: str | None, brief: bool, verbose: bool) -> None: ...
```

**Implementation Notes**:

- Follow the nested-Click pattern: `_setup_logging(verbose)` first, lazy imports inside leaves, and
  explicit `--db`, `--out`, and `--status-dir` overrides for hermetic execution. Production defaults
  resolve from constants.
- `ops scheduled-refresh` constructs `DefaultDecisionRefreshPorts`, supplies real UTC clock/UUID/pid,
  echoes the final audit lines, exits zero for success/degraded, and exits non-zero for failed or
  overlap. It never catches or edits individual refresh-step semantics in the CLI.
- Keep the manual `scripts/refresh_decision_data.py` as an unscheduled direct composition, but make
  it acquire the same artifact-derived operations lock as the scheduled adapter before mutation.
- `scripts/session_ops_status.py` calls the same read/brief formatter, has no network/DB imports, and
  exits zero even for missing/unhealthy state so it cannot break session startup. `AGENTS.md` session
  orientation invokes it when `data/ops/status/decision-refresh.json` exists and asks the agent to
  surface warnings/pending actions.

**Acceptance Criteria**:

- [ ] `legacy-engine ops --help` lists `scheduled-refresh`, `status`, and `scheduler`; both leaves
      call `_setup_logging` before work.
- [ ] Hermetic CLI tests use temporary status/DB/output paths and fake workflow adapters; they never
      read or write the operator's default database or status directory.
- [ ] `ops status` and the session script render identical brief health for a fixed record, including
      failed/stale/pending-action warnings.
- [ ] Running the session script with no status is safe, quick, local-only, and explicitly reports
      that no scheduled run is recorded.

### Unit 4: Generated launchd configuration and reversible controls

**Files**: `src/legacy_engine/ops/launchd.py`, `src/legacy_engine/cli.py`,
`tests/test_launchd.py`, `tests/test_ops_cli.py`

**Story**: `epic-data-autonomy-local-refresh-operations-launchd-controls`

```python
from pathlib import Path
from typing import Protocol

from legacy_engine.models.base import LegacyEngineModel

class CommandResult(LegacyEngineModel):
    returncode: int
    stdout: str = ""
    stderr: str = ""

class LaunchctlPort(Protocol):
    def run(self, *args: str) -> CommandResult: ...

class LaunchAgentSpec(LegacyEngineModel):
    label: str
    domain_target: str
    plist_path: Path
    python_path: Path
    repo_root: Path
    stdout_path: Path
    stderr_path: Path
    hour: int = 7
    minute: int = 30

class LaunchAgentState(LegacyEngineModel):
    installed: bool
    loaded: bool
    plist_path: Path
    detail: str

def build_refresh_launch_agent_spec(
    *, repo_root: Path, launch_agents_dir: Path, uid: int,
) -> LaunchAgentSpec: ...
def render_launch_agent_plist(spec: LaunchAgentSpec) -> bytes: ...
def install_launch_agent(spec: LaunchAgentSpec, launchctl: LaunchctlPort) -> LaunchAgentState: ...
def inspect_launch_agent(spec: LaunchAgentSpec, launchctl: LaunchctlPort) -> LaunchAgentState: ...
def run_launch_agent_now(spec: LaunchAgentSpec, launchctl: LaunchctlPort) -> LaunchAgentState: ...
def uninstall_launch_agent(spec: LaunchAgentSpec, launchctl: LaunchctlPort) -> LaunchAgentState: ...
```

```python
@ops.group("scheduler")
def ops_scheduler() -> None: ...

# leaves: install, inspect, run-now, uninstall
```

**Implementation Notes**:

- Render with `plistlib`, not string interpolation. `ProgramArguments` are the absolute venv Python,
  `-m legacy_engine.cli ops scheduled-refresh`; `WorkingDirectory`, `StartCalendarInterval`, and
  log paths are absolute. Validate `.venv/bin/python`, repository root, hour/minute, and plist
  structure before mutating LaunchAgents.
- The subprocess adapter uses argument tuples with no shell. Tests inject `LaunchctlPort` and a
  temporary LaunchAgents directory; no test invokes the real `launchctl` or writes under `~/Library`.
- Install/reconfigure follows the rollback rule in Design decisions. `inspect` maps `launchctl print`
  return code/output without treating “not loaded” as a crash. `run-now` uses `kickstart` without
  `-k`, so it never kills a currently running refresh. Uninstall is idempotent when absent.
- CLI scheduler leaves echo the resolved label, plist, schedule, log paths, loaded state, and
  actionable launchctl failure reason as `// ` audit lines.

**Acceptance Criteria**:

- [ ] Decoded plist has exactly the pinned label, absolute arguments/working/log paths, and daily
      07:30 `StartCalendarInterval`; it has no `RunAtLoad`, `KeepAlive`, or `StartInterval` keys.
- [ ] Identical reinstall is a no-op; changed reinstall reloads; bootstrap failure restores the
      prior file and attempts to restore the prior loaded state with the failure named.
- [ ] Inspect and run-now target `gui/<uid>/com.legacy-engine.refresh`; run-now does not pass `-k`.
- [ ] Uninstall removes only the exact resolved plist after successful/not-loaded bootout and reports
      whether recovery is possible on failure.

### Unit 5: Current operations documentation

**Files**: `README.md`, `docs/ARCHITECTURE.md`

**Story**: `epic-data-autonomy-local-refresh-operations-launchd-controls`

**Implementation Notes**:

- Add the `ops` package and CLI surface to the current architecture map after implementation.
- Document install, inspect, run-now, status, log paths, uninstall, the 07:30/wake-coalescing
  semantics, and how to diagnose missing/stale/failed status. Keep Modern/hot-spare/monitoring out.
- Run the documentation alignment and knowledge-index regeneration workflows after the code lands;
  do not hand-edit generated index files.

**Acceptance Criteria**:

- [ ] A maintainer can install, verify, manually trigger, inspect status/logs, and fully uninstall
      the local job using only documented commands.
- [ ] Documentation says the scheduler automates existing decision-data composition and does not
      claim the separate B&R monitor or deferred supply-chain arcs are built.

## Implementation Order

1. **Typed status contract/repository** — first because every other unit consumes its durable error
   and freshness semantics.
2. **Exclusive scheduled runner** — proves the highest-risk lock/status transaction with fake ports.
3. **Operator CLI/session projection** — adds consumers only after the core is deterministic.
4. **Launchd rendering/control** — depends on the settled scheduled-refresh command path.
5. **Current documentation/index** — records the verified command/path behavior after implementation.

## Testing

### Unit tests

- `tests/test_ops_status.py`: atomic replacement, prior-record preservation on replace failure,
  Pydantic round trip, timezone/staleness boundaries at 36 hours, invalid/missing/running/terminal
  health, and exact brief/full audit lines using an injected `now`.
- `tests/test_scheduled_refresh.py`: recording refresh ports plus injected clock/id/pid/lock cover
  call ordering, lock-before-mutation, terminal mapping, overlap isolation, last-good ranking
  attribution, pending era alarms, exceptions, and interrupt best-effort status.
- `tests/test_launchd.py`: decode rendered bytes with `plistlib.loads`; fake `LaunchctlPort` asserts
  exact command tuples, idempotence, reload, rollback, run-now no-kill behavior, and safe uninstall.

### Integration tests

- `tests/test_ops_cli.py`: Click runner with temp paths and monkeypatched production adapters proves
  exit codes/audit output for success, degraded, failed, overlap, missing/stale status, and every
  scheduler verb without touching live paths.
- Existing `tests/test_decision_refresh.py` remains the composition contract; add only a focused seam
  assertion if implementation reveals an untested result field needed by the scheduled runner.
- Run the focused ops/decision-refresh tests, then the full suite. Any real production bug follows
  the project's park-then-fix test-integrity rule.

## Risks

- **Status storage fails**: disk-full/permissions can prevent the promised final record. The runner
  emits a loud stderr error and non-zero exit; launchctl logs are the fallback. Do not fabricate a
  successful status. **Fallback**: `launchctl print` plus stderr log remains attributable.
- **Process dies uncatchably**: SIGKILL/power loss can leave canonical `running`. The kernel releases
  the lock; after 36 hours the view becomes stuck/stale rather than healthy. **Fallback**: the next
  run replaces canonical state and immutable attempt history retains prior evidence.
- **Refresh duration exceeds a day**: launchd or manual starts may contend. Non-blocking overlap
  preserves the owner and records the skipped attempt; it does not run two DuckDB writers.
  **Fallback**: operator inspects logs/status before `run-now`; no forced kill is automated.
- **Reconfiguration bootstrap fails**: the agent may be temporarily unloaded. Install restores the
  prior plist and attempts to reload it, reporting both primary and rollback errors.
  **Fallback**: documented `inspect` and `install` are safe to retry.
- **Session integration varies by harness**: a committed settings hook would be Claude/Codex-specific.
  **Fallback**: the source-of-truth is the portable `ops status --brief` formatter, invoked through
  the repository session-orientation instruction and usable by any later hook.
- **Least certain**: interruption finalization cannot cover SIGKILL or a machine crash. The design
  deliberately detects the stale `running` evidence instead of claiming exactly-once completion.

## Other agent review

A cross-model advisory pass was requested because lock/status semantics affect data integrity. The
local peer wrapper returned no usable result, so no peer suggestions were incorporated; this is a
non-blocking advisory failure. The design's pre-mortem therefore records the uncatchable-process,
status-filesystem, long-run overlap, and launchd rollback cases explicitly.

## Implementation summary

- `epic-data-autonomy-local-refresh-operations-runner-status` — done in `cec33b6`: typed atomic
  canonical/per-attempt status, health classification, artifact identity, and exclusive kernel-lock
  wrapper around the existing decision-refresh composition.
- `epic-data-autonomy-local-refresh-operations-operator-cli` — done in `7437d26`: `ops
  scheduled-refresh`, `ops status [--brief]`, shared no-network session projection, and session
  orientation integration.
- `epic-data-autonomy-local-refresh-operations-launchd-controls` — done in `82c4aa6`: generated
  07:30 LaunchAgent, reversible install/inspect/run-now/uninstall controls behind an injected
  process boundary, hermetic lifecycle coverage, runbook/architecture alignment, and canonical
  knowledge-index regeneration.
- No live LaunchAgent was installed, inspected, triggered, or removed during implementation. The
  external-state lifecycle remains an explicit operator action after review.

## Integrated verification

- `.venv/bin/pytest -q tests/test_launchd.py tests/test_ops_cli.py tests/test_ops_status.py tests/test_scheduled_refresh.py tests/test_decision_refresh.py tests/test_cli.py`
  — 125 passed.
- `PYTHONPATH=. .venv/bin/pytest -q` — 3,757 passed, 1 skipped in 159.39 seconds. The explicit
  `PYTHONPATH` preserves this repository's established mixed `tests.*` and sibling-module imports;
  no unrelated ranking tests were changed to alter collection behavior.
- `.venv/bin/python -m compileall -q src/legacy_engine/ops src/legacy_engine/cli.py scripts/session_ops_status.py`
  — passed.
- Canonical knowledge-index regeneration — 48 docs, 0 errors, 11 pre-existing warnings.
- Ruff was unavailable in `.venv`; pytest, compileall, diff checks, and the standard independent
  feature review are the verification path.

## Run notes

- **Ownership**: one cohesive feature owner followed the three-story dependency chain; shared CLI,
  status, and launchd context made splitting across workers more costly than sequential ownership.
- **Capability**: host implementation used the active frontier coding model at high reasoning; no
  routine implementation delegation was needed because all three layers share one interface chain.
- **Review weight**: `standard`, explicitly requested by the autopilot caller — one independent
  fresh-context feature pass, followed by recipient adjudication and any confirmed fixes without a
  second review pass.

## Review (2026-08-11)

**Verdict**: Approve

**Blockers**: none. The shared-lock and active-run lifecycle findings were fixed by
`epic-data-autonomy-local-refresh-operations-review-safety` in `3305dcf`.
**Important**: none. The post-bootout rollback-boundary finding was fixed in the same scoped story.
**Nits**: none.
**Rejected**: none.

**Notes**: Standard-weight deep feature review used one same-harness fresh-context Sol pass after
the different-class Claude endpoint returned no report, Gemini was unavailable, and Z.AI lacked
credentials. The pass covered correctness, tests, design alignment, command/path safety,
CLI/config contracts, foundation assertions, durability, concurrency, lifecycle, and operational
rollback. Recipient adjudication confirmed all three findings; the fix story added the shared
artifact-derived lock across scheduled/manual production entrypoints, active-lock-safe lifecycle
controls, best-effort SIGTERM terminalization, and a complete post-bootout rollback boundary.
Focused verification passed 134 tests; the corrected full suite passed 3,769 tests with 1 skip.
Standard closure requires no second independent pass. Live LaunchAgent installation, inspection,
triggering, and removal were intentionally excluded and remain explicit operator actions.

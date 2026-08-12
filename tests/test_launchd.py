from __future__ import annotations

import plistlib

import pytest

from legacy_engine.ops.launchd import (
    CommandResult,
    REFRESH_AGENT_LABEL,
    build_refresh_launch_agent_spec,
    inspect_launch_agent,
    install_launch_agent,
    render_launch_agent_plist,
    run_launch_agent_now,
    uninstall_launch_agent,
)


class FakeLaunchctl:
    def __init__(self, results=()):
        self.results = list(results)
        self.calls: list[tuple[str, ...]] = []

    def run(self, *args: str) -> CommandResult:
        self.calls.append(args)
        if self.results:
            return self.results.pop(0)
        return CommandResult(returncode=0)


@pytest.fixture
def spec(tmp_path):
    repo = tmp_path / "repo"
    python = repo / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()
    return build_refresh_launch_agent_spec(
        repo_root=repo,
        launch_agents_dir=tmp_path / "LaunchAgents",
        uid=501,
    )


class TestLaunchAgentRendering:
    def test_pinned_calendar_and_absolute_paths_without_respawn_keys(self, spec):
        payload = plistlib.loads(render_launch_agent_plist(spec))
        assert payload["Label"] == REFRESH_AGENT_LABEL
        assert payload["ProgramArguments"] == [
            str(spec.python_path), "-m", "legacy_engine.cli", "ops", "scheduled-refresh",
        ]
        assert payload["WorkingDirectory"] == str(spec.repo_root)
        assert payload["StartCalendarInterval"] == {"Hour": 7, "Minute": 30}
        assert payload["StandardOutPath"] == str(spec.stdout_path)
        assert payload["StandardErrorPath"] == str(spec.stderr_path)
        for forbidden in ("RunAtLoad", "KeepAlive", "StartInterval"):
            assert forbidden not in payload

    def test_missing_venv_python_fails_before_mutation(self, spec):
        spec.python_path.unlink()
        launchctl = FakeLaunchctl()
        with pytest.raises(ValueError, match="virtualenv Python"):
            install_launch_agent(spec, launchctl)
        assert launchctl.calls == []


class TestLaunchAgentLifecycle:
    def test_install_bootstraps_candidate(self, spec):
        launchctl = FakeLaunchctl([
            CommandResult(returncode=113, stderr="Could not find service"),
            CommandResult(returncode=0),
        ])
        state = install_launch_agent(spec, launchctl)
        assert state.ok and state.installed and state.loaded
        assert launchctl.calls == [
            ("print", "gui/501/com.legacy-engine.refresh"),
            ("bootstrap", "gui/501", str(spec.plist_path)),
        ]
        assert plistlib.loads(spec.plist_path.read_bytes())["Label"] == REFRESH_AGENT_LABEL

    def test_identical_loaded_install_is_noop(self, spec):
        spec.plist_path.parent.mkdir(parents=True)
        spec.plist_path.write_bytes(render_launch_agent_plist(spec))
        launchctl = FakeLaunchctl([CommandResult(returncode=0)])
        state = install_launch_agent(spec, launchctl)
        assert state.detail == "already installed and loaded"
        assert launchctl.calls == [("print", "gui/501/com.legacy-engine.refresh")]

    def test_changed_install_boots_out_then_reloads(self, spec):
        spec.plist_path.parent.mkdir(parents=True)
        spec.plist_path.write_text("old plist")
        launchctl = FakeLaunchctl([
            CommandResult(returncode=0),
            CommandResult(returncode=0),
            CommandResult(returncode=0),
        ])
        state = install_launch_agent(spec, launchctl)
        assert state.ok
        assert launchctl.calls[1] == ("bootout", "gui/501", str(spec.plist_path))
        assert launchctl.calls[2] == ("bootstrap", "gui/501", str(spec.plist_path))

    def test_bootstrap_failure_restores_and_reloads_previous(self, spec):
        old = b"old plist"
        spec.plist_path.parent.mkdir(parents=True)
        spec.plist_path.write_bytes(old)
        launchctl = FakeLaunchctl([
            CommandResult(returncode=0),
            CommandResult(returncode=0),
            CommandResult(returncode=5, stderr="bad candidate"),
            CommandResult(returncode=0),
        ])
        state = install_launch_agent(spec, launchctl)
        assert not state.ok
        assert state.loaded
        assert spec.plist_path.read_bytes() == old
        assert "reloaded previous agent" in state.detail

    def test_inspect_and_run_now_use_exact_target_without_kill(self, spec):
        spec.plist_path.parent.mkdir(parents=True)
        spec.plist_path.touch()
        inspect_ctl = FakeLaunchctl([CommandResult(returncode=0)])
        assert inspect_launch_agent(spec, inspect_ctl).loaded
        run_ctl = FakeLaunchctl([CommandResult(returncode=0)])
        assert run_launch_agent_now(spec, run_ctl).ok
        assert run_ctl.calls == [("kickstart", "gui/501/com.legacy-engine.refresh")]
        assert "-k" not in run_ctl.calls[0]

    def test_uninstall_preserves_plist_on_bootout_failure(self, spec):
        spec.plist_path.parent.mkdir(parents=True)
        spec.plist_path.write_text("installed")
        ctl = FakeLaunchctl([CommandResult(returncode=5, stderr="permission denied")])
        state = uninstall_launch_agent(spec, ctl)
        assert not state.ok
        assert spec.plist_path.exists()

    def test_uninstall_accepts_not_loaded_and_is_idempotent(self, spec):
        spec.plist_path.parent.mkdir(parents=True)
        spec.plist_path.write_text("installed")
        ctl = FakeLaunchctl([
            CommandResult(returncode=113, stderr="Could not find service"),
        ])
        state = uninstall_launch_agent(spec, ctl)
        assert state.ok and not spec.plist_path.exists()
        second = uninstall_launch_agent(spec, FakeLaunchctl())
        assert second.ok and second.detail == "already uninstalled"

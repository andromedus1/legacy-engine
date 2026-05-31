"""Rules vendoring — clone/fetch/checkout sequence + manifest, with injected runner (no real git)."""

from __future__ import annotations

import pytest

from legacy_engine.config import MTGOFORMATDATA_SHA
from legacy_engine.ingestion import rules_vendor

_PINNED_SHA = "e056bc7d63c0138091986ce1696c705bc7dee296"


class _FakeResult:
    def __init__(self, stdout: str):
        self.stdout = stdout


def _runner_factory(head_sha: str):
    """Return a (runner, calls) pair.  runner returns head_sha for every call so
    rev-parse HEAD reports the expected resolved SHA."""
    calls: list[list[str]] = []

    def runner(cmd, **kwargs):
        calls.append(list(cmd))
        return _FakeResult(head_sha + "\n")

    return runner, calls


# ── Existing coverage (updated for new fetch/checkout sequence) ───────────────

def test_clones_when_absent_and_pins_sha(tmp_path):
    dest = tmp_path / "rules"
    runner, calls = _runner_factory(_PINNED_SHA)
    sha = rules_vendor.refresh_rules(repo="REPO", dest=dest, sha=_PINNED_SHA, runner=runner)

    # First call must be git clone
    assert calls[0][:2] == ["git", "clone"]
    assert sha == _PINNED_SHA
    assert rules_vendor.pinned_sha(dest) == _PINNED_SHA


def test_skips_clone_when_git_dir_present(tmp_path):
    """When .git already exists, no clone; goes straight to fetch."""
    dest = tmp_path / "rules"
    (dest / ".git").mkdir(parents=True)
    runner, calls = _runner_factory(_PINNED_SHA)
    rules_vendor.refresh_rules(dest=dest, sha=_PINNED_SHA, runner=runner)

    git_cmds = [c for c in calls if c[:1] == ["git"]]
    # Must NOT contain a clone command
    assert not any("clone" in c for c in git_cmds)
    # Must contain a fetch
    assert any("fetch" in c for c in git_cmds)
    assert rules_vendor.pinned_sha(dest) == _PINNED_SHA


def test_pinned_sha_absent_when_not_vendored(tmp_path):
    assert rules_vendor.pinned_sha(tmp_path) == ""


# ── New: SHA pinning call sequence (finding #5) ───────────────────────────────

def test_fetch_checkout_sequence_on_fresh_clone(tmp_path):
    """After cloning, refresh_rules does fetch --depth 1 origin <sha> then checkout FETCH_HEAD."""
    dest = tmp_path / "rules"
    runner, calls = _runner_factory(_PINNED_SHA)
    rules_vendor.refresh_rules(repo="REPO", dest=dest, sha=_PINNED_SHA, runner=runner)

    git_cmds = [c for c in calls if c[:1] == ["git"]]

    # clone is first
    assert git_cmds[0][:2] == ["git", "clone"]

    # fetch --depth 1 origin <sha> is somewhere after clone
    fetch_cmds = [c for c in git_cmds if "fetch" in c]
    assert fetch_cmds, "expected a git fetch call"
    fetch = fetch_cmds[0]
    assert "--depth" in fetch and "1" in fetch
    assert "origin" in fetch
    assert _PINNED_SHA in fetch

    # checkout FETCH_HEAD follows the fetch
    checkout_cmds = [c for c in git_cmds if "checkout" in c]
    assert checkout_cmds, "expected a git checkout call"
    assert "FETCH_HEAD" in checkout_cmds[0]


def test_fetch_checkout_sequence_on_existing_repo(tmp_path):
    """On an existing repo, fetch --depth 1 origin <sha> then checkout FETCH_HEAD (no clone)."""
    dest = tmp_path / "rules"
    (dest / ".git").mkdir(parents=True)
    runner, calls = _runner_factory(_PINNED_SHA)
    rules_vendor.refresh_rules(dest=dest, sha=_PINNED_SHA, runner=runner)

    git_cmds = [c for c in calls if c[:1] == ["git"]]

    fetch_cmds = [c for c in git_cmds if "fetch" in c]
    assert fetch_cmds
    fetch = fetch_cmds[0]
    assert "--depth" in fetch and "1" in fetch
    assert _PINNED_SHA in fetch

    checkout_cmds = [c for c in git_cmds if "checkout" in c]
    assert checkout_cmds
    assert "FETCH_HEAD" in checkout_cmds[0]


def test_sha_mismatch_raises(tmp_path):
    """If post-checkout HEAD doesn't match the requested SHA, a RuntimeError is raised."""
    dest = tmp_path / "rules"
    # runner returns a *different* SHA from the one requested
    wrong_sha = "deadbeef" * 5
    runner, _calls = _runner_factory(wrong_sha)

    with pytest.raises(RuntimeError, match="rules pin mismatch"):
        rules_vendor.refresh_rules(repo="REPO", dest=dest, sha=_PINNED_SHA, runner=runner)


def test_manifest_records_input_sha(tmp_path):
    """Manifest always records the *requested* SHA, not whatever rev-parse returns."""
    dest = tmp_path / "rules"
    runner, _ = _runner_factory(_PINNED_SHA)
    rules_vendor.refresh_rules(repo="REPO", dest=dest, sha=_PINNED_SHA, runner=runner)

    assert rules_vendor.pinned_sha(dest) == _PINNED_SHA


def test_config_sha_constant():
    """MTGOFORMATDATA_SHA in config matches the expected pinned value."""
    assert MTGOFORMATDATA_SHA == _PINNED_SHA

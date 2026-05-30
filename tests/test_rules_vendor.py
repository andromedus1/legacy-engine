"""Rules vendoring — clone/pull branch + manifest, with an injected runner (no real git)."""

from __future__ import annotations

from legacy_engine.ingestion import rules_vendor


class _FakeResult:
    def __init__(self, stdout):
        self.stdout = stdout


def _runner_factory(sha):
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return _FakeResult(sha + "\n")  # used for the rev-parse call

    return runner, calls


def test_clones_when_absent_and_pins_sha(tmp_path):
    dest = tmp_path / "rules"
    runner, calls = _runner_factory("abc123")
    sha = rules_vendor.refresh_rules(repo="REPO", dest=dest, runner=runner)
    assert calls[0][:2] == ["git", "clone"]
    assert sha == "abc123"
    assert rules_vendor.pinned_sha(dest) == "abc123"


def test_pulls_when_present(tmp_path):
    dest = tmp_path / "rules"
    (dest / ".git").mkdir(parents=True)
    runner, calls = _runner_factory("def456")
    rules_vendor.refresh_rules(dest=dest, runner=runner)
    assert any("pull" in c for c in calls)
    assert rules_vendor.pinned_sha(dest) == "def456"


def test_pinned_sha_absent_when_not_vendored(tmp_path):
    assert rules_vendor.pinned_sha(tmp_path) == ""

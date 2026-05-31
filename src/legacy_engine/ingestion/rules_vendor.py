"""Vendor the MTGOFormatData archetype rules as a pinned, versioned data dependency.

``refresh_rules`` clones/fetches the upstream repo into RULES_DIR, checks out a
specific commit SHA, and records it in a manifest so the classifier always runs
against a known rules version.  The git runner is injected so tests can assert
the call sequence without hitting the network.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path

from legacy_engine.config import MTGOFORMATDATA_REPO, MTGOFORMATDATA_SHA, RULES_DIR

logger = logging.getLogger(__name__)

MANIFEST_NAME = "RULES_MANIFEST.json"


def refresh_rules(
    repo: str = MTGOFORMATDATA_REPO,
    dest: Path = RULES_DIR,
    sha: str = MTGOFORMATDATA_SHA,
    runner: Callable = subprocess.run,
) -> str:
    """Clone/fetch the rules repo, check out ``sha``, and pin it in the manifest.

    Strategy: stay shallow throughout.  For a fresh destination we clone first
    (to establish the remote), then fetch and checkout the pinned SHA via
    FETCH_HEAD.  For an existing repo we skip the clone and go straight to the
    fetch.  After checkout we resolve HEAD and raise if it doesn't match ``sha``
    — any drift (network error, wrong remote, ref rewrite) is surfaced immediately
    rather than silently recorded.

    Returns the verified SHA.
    """
    dest = Path(dest)

    if not (dest / ".git").exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Cloning rules %s -> %s", repo, dest)
        # Shallow clone to establish the remote; we'll fetch the exact sha next.
        runner(["git", "clone", "--depth", "1", repo, str(dest)], check=True)
    else:
        logger.info("Rules repo already present at %s; fetching sha %s", dest, sha)

    # Fetch the pinned SHA into FETCH_HEAD (stays shallow) then check it out.
    runner(
        ["git", "-C", str(dest), "fetch", "--depth", "1", "origin", sha],
        check=True,
    )
    runner(["git", "-C", str(dest), "checkout", "FETCH_HEAD"], check=True)

    resolved = _resolve_sha(dest, runner)
    if resolved != sha:
        raise RuntimeError(
            f"rules pin mismatch: wanted {sha!r}, got {resolved!r}"
        )

    dest.mkdir(parents=True, exist_ok=True)  # robust: clone normally creates it
    (dest / MANIFEST_NAME).write_text(json.dumps({"repo": repo, "sha": sha}, indent=2))
    logger.info("Rules pinned at %s", sha)
    return sha


def _resolve_sha(dest: Path, runner: Callable) -> str:
    """Return the current HEAD SHA, or '' if it can't be resolved (e.g. fake runner in tests)."""
    try:
        result = runner(
            ["git", "-C", str(dest), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        )
        return (getattr(result, "stdout", "") or "").strip()
    except Exception:  # noqa: BLE001 — SHA resolution is best-effort
        return ""


def pinned_sha(dest: Path = RULES_DIR) -> str:
    """Read the pinned SHA from the manifest, or '' if not yet vendored."""
    manifest = Path(dest) / MANIFEST_NAME
    if not manifest.exists():
        return ""
    return json.loads(manifest.read_text()).get("sha", "")

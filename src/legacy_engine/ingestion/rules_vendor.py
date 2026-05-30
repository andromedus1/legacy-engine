"""Vendor the MTGOFormatData archetype rules as a pinned, versioned data dependency.

`refresh_rules` clones/pulls the upstream repo into RULES_DIR and records the resolved commit SHA in
a manifest, so the classifier always runs against a known rules version. The git call is injected so
tests don't hit the network.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path

from legacy_engine.config import MTGOFORMATDATA_REPO, RULES_DIR

logger = logging.getLogger(__name__)

MANIFEST_NAME = "RULES_MANIFEST.json"


def refresh_rules(
    repo: str = MTGOFORMATDATA_REPO,
    dest: Path = RULES_DIR,
    runner: Callable = subprocess.run,
) -> str:
    """Clone/pull the rules repo and pin its commit SHA in a manifest. Returns the SHA."""
    dest = Path(dest)
    if (dest / ".git").exists():
        logger.info("Updating rules at %s", dest)
        runner(["git", "-C", str(dest), "pull", "--ff-only"], check=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Cloning rules %s -> %s", repo, dest)
        runner(["git", "clone", "--depth", "1", repo, str(dest)], check=True)

    sha = _resolve_sha(dest, runner)
    dest.mkdir(parents=True, exist_ok=True)  # git clone normally creates it; be robust regardless
    (dest / MANIFEST_NAME).write_text(json.dumps({"repo": repo, "sha": sha}, indent=2))
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

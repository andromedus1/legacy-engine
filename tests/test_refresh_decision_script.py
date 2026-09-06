from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

from legacy_engine.ops.scheduled_refresh import (
    LockUnavailable,
    decision_refresh_lock_path,
    exclusive_file_lock,
)


def _script_module():
    path = Path(__file__).parent.parent / "scripts" / "refresh_decision_data.py"
    spec = importlib.util.spec_from_file_location("refresh_decision_data", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manual_refresh_contends_with_scheduled_artifact_lock(tmp_path):
    module = _script_module()
    db = tmp_path / "legacy.duckdb"
    out = tmp_path / "ranking.html"
    lock_dir = tmp_path / "locks"
    shared = decision_refresh_lock_path(db, out, lock_dir=lock_dir)

    class Ports:
        def refresh_sources(self, db_path):
            raise AssertionError("manual refresh must not start while scheduled lock is held")

    with exclusive_file_lock(shared):
        with pytest.raises(LockUnavailable):
            module.run_manual_refresh(
                db_path=db, out_path=out, lock_dir=lock_dir, ports=Ports(),
            )


def test_direct_script_establishes_repository_import_root(tmp_path):
    project_root = Path(__file__).parent.parent.resolve()
    script = project_root / "scripts" / "refresh_decision_data.py"
    probe = f"""
import importlib.util
import sys
from pathlib import Path

project_root = Path({str(project_root)!r})
script = Path({str(script)!r})
sys.path = [p for p in sys.path if Path(p or '.').resolve() != project_root]
spec = importlib.util.spec_from_file_location('refresh_decision_data_direct', script)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert str(project_root) in sys.path
import scripts.refresh_best_call_ranking
"""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

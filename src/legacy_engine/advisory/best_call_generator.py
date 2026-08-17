"""Package-owned access to the repository's mature Best Call ranking generator."""

from __future__ import annotations

from functools import lru_cache
import importlib.util
from pathlib import Path
from types import ModuleType

from legacy_engine.config import PROJECT_ROOT


RANKING_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "refresh_best_call_ranking.py"


@lru_cache(maxsize=None)
def _load_generator(script_path: Path) -> ModuleType:
    """Load one generator module by absolute path without relying on ``sys.path``."""
    if not script_path.is_file():
        raise RuntimeError(f"ranking generator not found at {script_path}")
    spec = importlib.util.spec_from_file_location(
        "legacy_engine_refresh_best_call_ranking", script_path,
    )
    if spec is None or spec.loader is None:  # pragma: no cover - importlib fixed-path guard
        raise RuntimeError(f"cannot load ranking generator at {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current_report_target(*args, **kwargs):
    """Resolve the current report target through the package-owned loader."""
    return _load_generator(RANKING_SCRIPT_PATH).current_report_target(*args, **kwargs)


def generate_ranking(**kwargs):
    """Generate one ranking through the package-owned loader."""
    return _load_generator(RANKING_SCRIPT_PATH).generate_ranking(**kwargs)

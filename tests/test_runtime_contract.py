from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).parent.parent


def test_python_pin_package_range_and_ci_matrix_stay_aligned():
    package = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    pin = (ROOT / ".python-version").read_text().strip()
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    assert pin == "3.13"
    assert package["requires-python"] == ">=3.11,<3.14"
    matrix_match = re.search(r"python-version: \[([^]]+)]", workflow)
    assert matrix_match is not None
    versions = tuple(re.findall(r"['\"](3\.\d+)['\"]", matrix_match.group(1)))
    assert versions == ("3.11", pin)
    assert "python-version: ${{ matrix.python-version }}" in workflow


def test_contributor_runtime_and_optional_discovery_contract_are_explicit():
    contributing = (ROOT / "CONTRIBUTING.md").read_text()

    assert "Python 3.11–3.13" in contributing
    assert "Python **3.13** via `.python-version`" in contributing
    assert "Python 3.14 is not supported" in contributing
    assert "skips honestly" in contributing

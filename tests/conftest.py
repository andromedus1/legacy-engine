"""Shared test fixtures and factory helpers.

Establishes the project test idiom: factory fixtures returning `_make_X(**kwargs)`
builders with sensible defaults, overridable per test (per
.claude/rules/patterns.md test-factory-patterns).
"""

from __future__ import annotations

import pytest

from legacy_engine.confidence import ConfidenceMetadata


@pytest.fixture
def make_confidence():
    """Return a builder for ConfidenceMetadata with overridable defaults."""

    def _make(**kwargs) -> ConfidenceMetadata:
        defaults: dict = {
            "level": "established",
            "production": "hand-written",
            "source": "user",
        }
        defaults.update(kwargs)
        return ConfidenceMetadata(**defaults)

    return _make

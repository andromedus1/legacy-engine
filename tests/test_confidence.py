"""ConfidenceMetadata validation + tier_for_sample boundary behavior."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from legacy_engine.confidence import ConfidenceMetadata, tier_for_sample


class TestTierForSample:
    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, "speculative"),
            (29, "speculative"),
            (30, "evolving"),
            (99, "evolving"),
            (100, "established"),
            (5000, "established"),
        ],
    )
    def test_boundaries(self, n, expected):
        assert tier_for_sample(n) == expected

    def test_custom_thresholds(self):
        assert tier_for_sample(50, evolving_min=60, established_min=200) == "speculative"
        assert tier_for_sample(60, evolving_min=60, established_min=200) == "evolving"


class TestConfidenceMetadata:
    def test_defaults(self):
        meta = ConfidenceMetadata()
        assert meta.level == "speculative"
        assert meta.production == "template-generated"
        assert meta.source == "heuristic"
        assert meta.updated is None

    def test_explicit_construction(self):
        meta = ConfidenceMetadata(
            level="established",
            production="hand-written",
            source="user",
            updated=date(2026, 5, 29),
        )
        assert meta.level == "established"
        assert meta.updated == date(2026, 5, 29)

    def test_factory_fixture(self, make_confidence):
        assert make_confidence().level == "established"
        assert make_confidence(level="evolving").level == "evolving"

    def test_invalid_level_rejected(self):
        with pytest.raises(ValidationError):
            ConfidenceMetadata(level="totally-sure")

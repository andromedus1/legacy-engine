"""Per-entity stable-era detection — series building + change-point detection.

Story 1 (series):
    from legacy_engine.analytics.eras.series import (
        Bucket, EntitySeries, build_entity_series,
    )
"""

from __future__ import annotations

from legacy_engine.analytics.eras.series import Bucket, EntitySeries, build_entity_series

__all__ = [
    "Bucket",
    "EntitySeries",
    "build_entity_series",
]

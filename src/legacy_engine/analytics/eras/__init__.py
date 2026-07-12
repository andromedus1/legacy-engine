"""Per-entity stable-era detection — series building + change-point detection.

Story 1 (series):
    from legacy_engine.analytics.eras.series import (
        Bucket, EntitySeries, build_entity_series,
    )

Story 2 (bocpd):
    from legacy_engine.analytics.eras.bocpd import (
        BocpdResult, beta_binomial_bocpd,
    )
"""

from __future__ import annotations

from legacy_engine.analytics.eras.bocpd import BocpdResult, beta_binomial_bocpd
from legacy_engine.analytics.eras.series import Bucket, EntitySeries, build_entity_series

__all__ = [
    "Bucket",
    "EntitySeries",
    "build_entity_series",
    "BocpdResult",
    "beta_binomial_bocpd",
]

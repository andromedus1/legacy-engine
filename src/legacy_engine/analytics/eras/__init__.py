"""Per-entity stable-era detection — series building, change-point detection, ensemble.

Pipeline seam (epic-stable-era-windows-detection):

    series.py    build_entity_series(con)          -> dict[str, EntitySeries]   (the only DB pass)
    detect.py    detect_presence / detect_composition / detect_share
                 + corroborate_winrate             -> list[CandidateBoundary]   (pure numpy)
    ensemble.py  derive_eras(series, candidates)   -> dict[str, EntityEras]     (merge + BH-FDR
                                                       + deck floor + camp inheritance)
    bocpd.py     beta_binomial_bocpd               -> BocpdResult               (online drift
                                                       alarm; consumed by the era-ledger feature)
"""

from __future__ import annotations

from legacy_engine.analytics.eras.bocpd import BocpdResult, beta_binomial_bocpd
from legacy_engine.analytics.eras.detect import (
    SIGNAL_TYPES,
    CandidateBoundary,
    corroborate_winrate,
    detect_composition,
    detect_presence,
    detect_share,
)
from legacy_engine.analytics.eras.ensemble import EntityEras, EraBoundary, derive_eras
from legacy_engine.analytics.eras.series import Bucket, EntitySeries, build_entity_series

__all__ = [
    "Bucket",
    "EntitySeries",
    "build_entity_series",
    "BocpdResult",
    "beta_binomial_bocpd",
    "SIGNAL_TYPES",
    "CandidateBoundary",
    "detect_presence",
    "detect_composition",
    "detect_share",
    "corroborate_winrate",
    "EraBoundary",
    "EntityEras",
    "derive_eras",
]

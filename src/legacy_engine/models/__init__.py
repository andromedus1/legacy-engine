"""Shared data models for legacy-engine."""

from __future__ import annotations

from legacy_engine.confidence import ConfidenceMetadata, tier_for_sample
from legacy_engine.models.base import LegacyEngineModel

__all__ = ["LegacyEngineModel", "ConfidenceMetadata", "tier_for_sample"]
